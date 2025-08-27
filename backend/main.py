from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Tuple
import os
from dotenv import load_dotenv
import logging

from statshunters import StatshuntersClient
from routing import RouteService
from mapy_routing import MapyRouteService
from routing_factory import RoutingServiceFactory
from optimizer import TileOptimizer

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Statshunters Route Optimizer")

# Enable CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
statshunters_client = None
routing_factory = None

def initialize_services():
    """Initialize external service clients."""
    global statshunters_client, routing_factory
    
    # Initialize Statshunters client
    share_link = os.getenv("STATSHUNTERS_SHARE_LINK")
    api_key = os.getenv("STATSHUNTERS_API_KEY")
    
    if share_link or api_key:
        statshunters_client = StatshuntersClient(share_link=share_link, api_key=api_key)
    
    # Initialize routing factory (handles both OpenRouteService and Mapy.cz)
    routing_factory = RoutingServiceFactory()
    
    available_services = routing_factory.get_available_services()
    if available_services:
        logger.info(f"Initialized routing services: {[s['name'] for s in available_services]}")
    else:
        logger.warning("No routing services available. Please configure ORS_API_KEY or MAPY_API_KEY.")

# Initialize on startup
initialize_services()

# Request/Response models
class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    target_distance: float  # kilometers
    bike_type: str = "mountain"  # road, gravel, mountain, ebike
    max_tiles: int = 30
    prefer_unvisited: bool = True
    share_link: Optional[str] = None
    api_key: Optional[str] = None
    routing_service: Optional[str] = None  # 'openroute', 'mapy', or None to use factory default

class TileDataRequest(BaseModel):
    west: float
    south: float
    east: float
    north: float
    share_link: Optional[str] = None
    api_key: Optional[str] = None

class RouteResponse(BaseModel):
    route_geojson: dict
    distance: float  # kilometers
    duration: float  # hours
    elevation_gain: float  # meters
    tiles_covered: int
    new_tiles: int
    gpx_download_url: str

# API Endpoints
@app.get("/")
async def read_root():
    """Serve the main HTML page."""
    return FileResponse("../frontend/index.html")

@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404s."""
    return Response(content="", media_type="image/x-icon")

@app.get("/api/routing-services")
async def get_routing_services():
    """Get available routing services and their capabilities."""
    if not routing_factory:
        raise HTTPException(status_code=503, detail="Routing services not initialized")
    
    services = routing_factory.get_available_services()
    return {"services": services}

@app.post("/api/tiles")
async def get_tiles(request: TileDataRequest):
    """Get visited and unvisited tiles in the specified bounds."""
    try:
        # Use provided credentials or fall back to environment
        client = statshunters_client
        if request.share_link or request.api_key:
            client = StatshuntersClient(share_link=request.share_link, api_key=request.api_key)
        
        if not client:
            raise HTTPException(status_code=400, detail="Statshunters credentials not configured")
        
        # Fetch visited tiles
        visited_tiles = client.fetch_visited_tiles()
        
        # Get all tiles in bounds
        all_tiles = client.get_tiles_in_bounds(request.west, request.south, request.east, request.north)
        
        # Calculate unvisited tiles
        unvisited_tiles = all_tiles - visited_tiles
        
        # Convert to GeoJSON
        visited_geojson = client.tiles_to_geojson(
            visited_tiles & all_tiles,  # Only show visited tiles in bounds
            {"status": "visited"}
        )
        unvisited_geojson = client.tiles_to_geojson(
            unvisited_tiles,
            {"status": "unvisited"}
        )
        
        return {
            "visited": visited_geojson,
            "unvisited": unvisited_geojson,
            "stats": {
                "total_tiles": len(all_tiles),
                "visited_tiles": len(visited_tiles & all_tiles),
                "unvisited_tiles": len(unvisited_tiles)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching tiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/route", response_model=RouteResponse)
async def generate_route(request: RouteRequest):
    """Generate an optimized route for tile hunting using available routing services."""
    try:
        # Use the global routing factory (configured via environment variables)
        factory = routing_factory
        
        if not factory:
            raise HTTPException(status_code=503, detail="Routing services not available")
        
        # Check if any routing services are available
        available_services = factory.get_available_services()
        if not available_services:
            raise HTTPException(
                status_code=400, 
                detail="No routing services configured. Please configure API keys in your .env file: "
                       "ORS_API_KEY (OpenRouteService) or MAPY_API_KEY (Mapy.cz)"
            )
        
        # Use provided credentials or fall back to environment
        client = statshunters_client
        if request.share_link or request.api_key:
            client = StatshuntersClient(share_link=request.share_link, api_key=request.api_key)
        
        if not client:
            raise HTTPException(status_code=400, detail="Statshunters credentials not configured")
        
        # Define search bounds (roughly based on target distance)
        # This is simplified - you might want more sophisticated bounds calculation
        km_to_deg = 1 / 111  # Rough conversion
        search_radius = request.target_distance / 2 * km_to_deg
        
        bounds = (
            request.start_lon - search_radius,
            request.start_lat - search_radius,
            request.start_lon + search_radius,
            request.start_lat + search_radius
        )
        
        # Fetch tiles
        visited_tiles = client.fetch_visited_tiles()
        all_tiles = client.get_tiles_in_bounds(*bounds)
        
        # Initialize optimizer
        optimizer = TileOptimizer(visited_tiles, all_tiles)
        
        # Generate optimized waypoints
        waypoints = optimizer.optimize_tile_coverage(
            start_point=(request.start_lon, request.start_lat),
            target_distance=request.target_distance,
            max_tiles=request.max_tiles,
            prefer_unvisited=request.prefer_unvisited
        )
        
        # Create routing service using factory
        try:
            # Create routing service instance using factory
            routing_service = factory.create_service(
                service_type=request.routing_service,
                bike_type=request.bike_type
            )
            
            # Validate bike type for selected service
            if request.routing_service and not factory.validate_service_bike_combination(request.routing_service, request.bike_type):
                available_bikes = factory.get_bike_types_for_service(request.routing_service)
                raise HTTPException(
                    status_code=400,
                    detail=f"Bike type '{request.bike_type}' is not supported by {request.routing_service}. "
                           f"Available types: {list(available_bikes.keys())}"
                )
            
            # Get service info for logging
            service_name = "auto-selected"
            if hasattr(routing_service, '__class__'):
                service_name = "Mapy.cz" if "MapyRouteService" in str(type(routing_service)) else "OpenRouteService"
            
            logger.info(f"Using {service_name} for {request.bike_type} bike routing")
            
            # Generate route through waypoints
            route_data = routing_service.generate_route(
                waypoints=waypoints,
                bike_type=request.bike_type,
                optimize=True,
                validate_waypoints=False  # Disabled to avoid rate limiting
            )
            
        except ValueError as routing_error:
            # Check for rate limiting first
            error_msg = str(routing_error)
            if "rate limit" in error_msg.lower() or "429" in error_msg:
                service_display = service_name if 'service_name' in locals() else "routing service"
                raise HTTPException(
                    status_code=429,
                    detail=f"{service_display} rate limit exceeded. Please wait a few minutes before trying again. "
                           "To reduce API usage, try: reducing target distance, using fewer max tiles, "
                           "or selecting an area closer to roads."
                )
            
            # If routing fails, try with fewer waypoints or different strategy
            logger.warning(f"Initial routing failed with {service_name if 'service_name' in locals() else 'routing service'}: {routing_error}")
            
            if len(waypoints) > 2:
                # Try with just start and end points
                logger.info("Retrying with simplified route (start and end only)")
                simplified_waypoints = [waypoints[0], waypoints[-1]]
                
                try:
                    route_data = routing_service.generate_route(
                        waypoints=simplified_waypoints,
                        bike_type=request.bike_type,
                        optimize=False,
                        validate_waypoints=False  # Disabled to avoid rate limiting
                    )
                    logger.info("Simplified route generated successfully")
                except Exception as simple_error:
                    simple_error_msg = str(simple_error)
                    logger.error(f"Simplified routing also failed: {simple_error}")
                    
                    # Check for rate limiting in simplified route
                    if "rate limit" in simple_error_msg.lower() or "429" in simple_error_msg:
                        raise HTTPException(
                            status_code=429,
                            detail="OpenRouteService rate limit exceeded. Please wait a few minutes before trying again."
                        )
                    
                    # Provide specific error message based on the error type
                    if "2012" in simple_error_msg and "weightings" in simple_error_msg:
                        raise HTTPException(
                            status_code=400,
                            detail="Route generation failed due to API configuration issues. "
                                   "This is a known issue and has been reported to the developers. "
                                   "Try again in a few minutes or contact support."
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Could not generate route in this area. The selected coordinates may be in "
                                   f"areas without suitable roads for {request.bike_type} cycling. "
                                   f"Try selecting a different start point or reducing the distance. "
                                   f"Error: {simple_error_msg}"
                        )
            else:
                # Handle single route failure
                if "2012" in error_msg and "weightings" in error_msg:
                    raise HTTPException(
                        status_code=400,
                        detail="Route generation failed due to API configuration issues. "
                               "This is a known issue. Try again in a few minutes."
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not generate route between the selected points. "
                               f"The coordinates may be in areas without suitable roads for {request.bike_type} cycling. "
                               f"Try selecting a different start point. Error: {error_msg}"
                    )
        
        # Calculate tiles covered by route
        # This is simplified - you'd want to check actual route geometry
        tiles_covered = set()
        new_tiles = set()
        
        for waypoint in waypoints:
            # Find which tile this waypoint is in
            import mercantile
            tile = mercantile.tile(waypoint[0], waypoint[1], 14)
            tile_coord = (tile.x, tile.y)
            tiles_covered.add(tile_coord)
            if tile_coord not in visited_tiles:
                new_tiles.add(tile_coord)
        
        # Generate GPX using the routing service that was used for route generation
        service_prefix = service_name.replace(".", "_") if 'service_name' in locals() else "Route"
        gpx_content = routing_service.create_gpx(route_data, name=f"{service_prefix}_{request.bike_type}_route")
        
        # Store GPX temporarily (in production, use proper storage)
        gpx_filename = f"route_{hash(gpx_content) % 1000000}.gpx"
        gpx_path = f"temp/{gpx_filename}"
        os.makedirs("temp", exist_ok=True)
        with open(gpx_path, "w") as f:
            f.write(gpx_content)
        
        return RouteResponse(
            route_geojson=route_data.get("geometry", {}),
            distance=route_data.get("distance", 0) / 1000,  # Convert to km
            duration=route_data.get("duration", 0) / 3600,  # Convert to hours
            elevation_gain=route_data.get("ascent", 0),
            tiles_covered=len(tiles_covered),
            new_tiles=len(new_tiles),
            gpx_download_url=f"/api/download/{gpx_filename}"
        )
    
    except Exception as e:
        logger.error(f"Error generating route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{filename}")
async def download_gpx(filename: str):
    """Download generated GPX file."""
    try:
        file_path = f"temp/{filename}"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
            return Response(
                content=content,
                media_type="application/gpx+xml",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error downloading GPX: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bike-profiles")
async def get_bike_profiles():
    """Get information about available bike profiles and their routing preferences."""
    if not routing_factory:
        raise HTTPException(status_code=503, detail="Routing services not available")
    
    available_services = routing_factory.get_available_services()
    if not available_services:
        raise HTTPException(status_code=400, detail="No routing services configured")
    
    # Return bike profiles organized by service
    service_profiles = {}
    for service_info in available_services:
        service_id = service_info['id']
        try:
            # Create service instance to get profiles
            routing_service = routing_factory.create_service(service_type=service_id)
            
            # Get profiles for this service
            profiles = {}
            service_bike_types = service_info.get('bike_types', {})
            for bike_type in service_bike_types.keys():
                try:
                    profiles[bike_type] = routing_service.get_route_preferences(bike_type)
                except Exception as e:
                    # Skip bike types that don't work with this service
                    logger.warning(f"Could not get preferences for {bike_type} on {service_id}: {e}")
                    continue
            
            service_profiles[service_id] = {
                'service_name': service_info['name'],
                'profiles': profiles
            }
            
        except Exception as e:
            logger.warning(f"Could not load profiles for service {service_id}: {e}")
            continue
    
    return {"service_profiles": service_profiles}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    available_services = routing_factory.get_available_services() if routing_factory else []
    return {
        "status": "healthy",
        "services": {
            "statshunters": statshunters_client is not None,
            "routing_factory": routing_factory is not None,
            "available_routing_services": [s['id'] for s in available_services]
        }
    }

# Mount static files for CSS, JS, and other assets
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)