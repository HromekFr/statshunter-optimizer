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
route_service = None

def initialize_services():
    """Initialize external service clients."""
    global statshunters_client, route_service
    
    # Initialize Statshunters client
    share_link = os.getenv("STATSHUNTERS_SHARE_LINK")
    api_key = os.getenv("STATSHUNTERS_API_KEY")
    
    if share_link or api_key:
        statshunters_client = StatshuntersClient(share_link=share_link, api_key=api_key)
    
    # Initialize routing service
    ors_key = os.getenv("ORS_API_KEY")
    if ors_key:
        route_service = RouteService(ors_key)
    else:
        logger.warning("ORS_API_KEY not found. Route generation will be disabled.")

# Initialize on startup
initialize_services()

# Request/Response models
class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    target_distance: float  # kilometers
    bike_type: str = "gravel"  # road, gravel, mountain, ebike
    max_tiles: int = 30
    prefer_unvisited: bool = True
    share_link: Optional[str] = None
    api_key: Optional[str] = None

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
    """Generate an optimized route for tile hunting."""
    try:
        if not route_service:
            raise HTTPException(status_code=400, detail="OpenRouteService API key not configured")
        
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
        
        # Generate route through waypoints
        route_data = route_service.generate_route(
            waypoints=waypoints,
            bike_type=request.bike_type,
            optimize=True
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
        
        # Generate GPX
        gpx_content = route_service.create_gpx(route_data, name=f"Statshunters_{request.bike_type}_route")
        
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

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "statshunters": statshunters_client is not None,
            "routing": route_service is not None
        }
    }

# Mount static files for CSS, JS, and other assets
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)