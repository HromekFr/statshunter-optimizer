import openrouteservice
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class RouteService:
    """Service for generating cycling routes using OpenRouteService."""
    
    # OpenRouteService cycling profiles
    PROFILES = {
        'road': 'cycling-road',
        'gravel': 'cycling-regular',
        'mountain': 'cycling-mountain',
        'ebike': 'cycling-electric'
    }
    
    def __init__(self, api_key: str):
        """
        Initialize route service with OpenRouteService API key.
        
        Args:
            api_key: OpenRouteService API key
        """
        self.client = openrouteservice.Client(key=api_key)
    
    def generate_route(self, 
                      waypoints: List[Tuple[float, float]], 
                      bike_type: str = 'gravel',
                      optimize: bool = True,
                      return_geometry: bool = True) -> Dict:
        """
        Generate a cycling route through waypoints.
        
        Args:
            waypoints: List of (lon, lat) coordinates
            bike_type: Type of bike ('road', 'gravel', 'mountain', 'ebike')
            optimize: Whether to optimize waypoint order
            return_geometry: Whether to return route geometry
            
        Returns:
            Route data including geometry, distance, and duration
        """
        if bike_type not in self.PROFILES:
            raise ValueError(f"Invalid bike type. Choose from: {list(self.PROFILES.keys())}")
        
        if len(waypoints) < 2:
            raise ValueError("At least 2 waypoints required")
        
        if len(waypoints) > 50:
            logger.warning(f"Too many waypoints ({len(waypoints)}). Using first 50.")
            waypoints = waypoints[:50]
        
        profile = self.PROFILES[bike_type]
        
        try:
            # Generate route
            route = self.client.directions(
                coordinates=waypoints,
                profile=profile,
                format='geojson',
                optimize_waypoints=optimize,
                geometry=return_geometry,
                instructions=False,  # We don't need turn-by-turn instructions
                elevation=True  # Include elevation data
            )
            
            # Extract key metrics
            if route and 'features' in route and len(route['features']) > 0:
                feature = route['features'][0]
                properties = feature.get('properties', {})
                
                result = {
                    'geometry': feature.get('geometry', {}),
                    'distance': properties.get('summary', {}).get('distance', 0),  # meters
                    'duration': properties.get('summary', {}).get('duration', 0),  # seconds
                    'ascent': properties.get('ascent', 0),
                    'descent': properties.get('descent', 0),
                    'waypoint_order': properties.get('way_points', [])
                }
                
                logger.info(f"Generated route: {result['distance']/1000:.1f}km, "
                          f"{result['duration']/3600:.1f}h, "
                          f"ascent: {result['ascent']:.0f}m")
                
                return result
            
        except openrouteservice.exceptions.ApiError as e:
            logger.error(f"ORS API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Route generation error: {e}")
            raise
    
    def generate_round_trip(self,
                           start_point: Tuple[float, float],
                           target_distance: float,
                           bike_type: str = 'gravel',
                           seed: Optional[int] = None) -> Dict:
        """
        Generate a round trip route of approximately target distance.
        
        Args:
            start_point: (lon, lat) starting coordinate
            target_distance: Target distance in kilometers
            bike_type: Type of bike
            seed: Random seed for route variation
            
        Returns:
            Round trip route data
        """
        profile = self.PROFILES.get(bike_type, 'cycling-regular')
        
        try:
            # Use ORS round trip API
            route = self.client.directions(
                coordinates=[start_point, start_point],  # Start and end at same point
                profile=profile,
                format='geojson',
                options={
                    'round_trip': {
                        'length': target_distance * 1000,  # Convert to meters
                        'points': 3,  # Number of waypoints to generate
                        'seed': seed or 0
                    }
                }
            )
            
            return route
            
        except Exception as e:
            logger.error(f"Round trip generation error: {e}")
            # Fallback to manual waypoint generation
            # This is simplified - you'd want more sophisticated logic here
            import math
            waypoints = [start_point]
            
            # Generate waypoints in a rough circle
            radius = target_distance / (2 * math.pi)  # km
            for angle in [90, 180, 270]:
                lat_offset = radius * math.cos(math.radians(angle)) / 111  # degrees
                lon_offset = radius * math.sin(math.radians(angle)) / (111 * math.cos(math.radians(start_point[1])))
                waypoint = (start_point[0] + lon_offset, start_point[1] + lat_offset)
                waypoints.append(waypoint)
            
            waypoints.append(start_point)  # Return to start
            
            return self.generate_route(waypoints, bike_type, optimize=False)
    
    def create_gpx(self, route_data: Dict, name: str = "Statshunters Route") -> str:
        """
        Convert route data to GPX format.
        
        Args:
            route_data: Route data with geometry
            name: Name for the GPX track
            
        Returns:
            GPX XML string
        """
        import gpxpy
        import gpxpy.gpx
        
        gpx = gpxpy.gpx.GPX()
        
        # Create track
        track = gpxpy.gpx.GPXTrack()
        track.name = name
        gpx.tracks.append(track)
        
        # Create segment
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)
        
        # Add points from geometry
        if 'geometry' in route_data and 'coordinates' in route_data['geometry']:
            for coord in route_data['geometry']['coordinates']:
                # GeoJSON is [lon, lat, elevation?], GPX needs lat, lon
                if len(coord) >= 2:
                    point = gpxpy.gpx.GPXTrackPoint(
                        latitude=coord[1],
                        longitude=coord[0],
                        elevation=coord[2] if len(coord) > 2 else None
                    )
                    segment.points.append(point)
        
        return gpx.to_xml()