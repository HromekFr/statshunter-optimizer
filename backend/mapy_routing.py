import requests
from typing import List, Tuple, Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)

class MapyRouteService:
    """Service for generating cycling routes using Mapy.cz API."""
    
    # Mapy.cz cycling profiles
    PROFILES = {
        'road': 'bike_road',
        'mountain': 'bike_mountain'
    }
    
    # Routing options for each bike type
    PROFILE_OPTIONS = {
        'road': {
            'description': 'Road cycling: prefers asphalt surfaces and cycle paths, optimized for road bikes',
            'description_extra': 'fast routes on paved surfaces'
        },
        'mountain': {
            'description': 'Mountain/touring cycling: prefers cycle paths regardless of surface, excellent for bike touring and mountain biking',
            'description_extra': 'touring routes on varied terrain including unpaved paths'
        }
    }
    
    def __init__(self, api_key: str):
        """
        Initialize route service with Mapy.cz API key.
        
        Args:
            api_key: Mapy.cz API key
        """
        self.api_key = api_key
        self.base_url = "https://api.mapy.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def get_route_preferences(self, bike_type: str) -> Dict:
        """
        Get routing preferences description for a bike type.
        
        Args:
            bike_type: Type of bike
            
        Returns:
            Dictionary describing routing preferences
        """
        profile_options = self.PROFILE_OPTIONS.get(bike_type, {})
        
        return {
            'profile': self.PROFILES.get(bike_type, 'bike_mountain'),
            'description': profile_options.get('description', 'Standard cycling route'),
            'avoids': [],  # Mapy.cz has fewer avoid options than OpenRouteService
            'prefers_green_routes': bike_type == 'mountain',
            'difficulty_level': 'touring optimized'
        }
    
    def validate_and_snap_waypoints(self, waypoints: List[Tuple[float, float]], bike_type: str = 'mountain') -> List[Tuple[float, float]]:
        """
        Validate waypoints and snap them to nearest routable points.
        For Mapy.cz, we use a lightweight approach to avoid unnecessary API calls.
        
        Args:
            waypoints: List of (lon, lat) coordinates
            bike_type: Type of bike for routing profile
            
        Returns:
            List of validated waypoints
        """
        if not waypoints:
            return waypoints
            
        # Limit waypoints to reduce API usage (Mapy.cz allows up to 15)
        if len(waypoints) > 15:
            logger.info(f"Limiting waypoints from {len(waypoints)} to 15 (Mapy.cz limit)")
            waypoints = waypoints[:15]
        
        # For Mapy.cz, we'll use a simple validation approach without expensive API calls
        # Similar to our OpenRouteService optimization
        validated_waypoints = []
        
        for i, (lon, lat) in enumerate(waypoints):
            # Basic coordinate validation
            if self._is_valid_coordinate(lon, lat):
                validated_waypoints.append((lon, lat))
                logger.debug(f"Waypoint {i} at ({lon:.6f}, {lat:.6f}) accepted")
            else:
                # Apply simple coordinate adjustment for invalid points
                adjusted_coord = self._adjust_coordinate(lon, lat)
                if adjusted_coord:
                    validated_waypoints.append(adjusted_coord)
                    logger.info(f"Adjusted waypoint {i} from ({lon:.6f}, {lat:.6f}) to ({adjusted_coord[0]:.6f}, {adjusted_coord[1]:.6f})")
        
        logger.info(f"Validated {len(validated_waypoints)} out of {len(waypoints)} waypoints for Mapy.cz")
        return validated_waypoints
    
    def _is_valid_coordinate(self, lon: float, lat: float) -> bool:
        """
        Quick validation for coordinates without API calls.
        
        Args:
            lon: Longitude
            lat: Latitude
            
        Returns:
            True if coordinate appears valid
        """
        # Basic bounds checking
        if abs(lat) > 85 or abs(lon) > 180:
            return False
        
        # Mapy.cz works best in Central/Eastern Europe, but accept global coordinates
        # Most coordinates should be valid for routing
        return True
    
    def _adjust_coordinate(self, lon: float, lat: float) -> Optional[Tuple[float, float]]:
        """
        Apply small adjustment to potentially problematic coordinates.
        
        Args:
            lon: Original longitude
            lat: Original latitude
            
        Returns:
            Adjusted coordinate or None
        """
        # Apply small offset similar to OpenRouteService approach
        adjusted_lon = lon + 0.0008  # ~80m east
        adjusted_lat = lat + 0.0006  # ~70m north
        
        if self._is_valid_coordinate(adjusted_lon, adjusted_lat):
            return (adjusted_lon, adjusted_lat)
        
        return None

    def generate_route(self, 
                      waypoints: List[Tuple[float, float]], 
                      bike_type: str = 'mountain',
                      optimize: bool = True,
                      return_geometry: bool = True,
                      validate_waypoints: bool = False) -> Dict:
        """
        Generate a cycling route through waypoints using Mapy.cz API.
        
        Args:
            waypoints: List of (lon, lat) coordinates
            bike_type: Type of bike ('road', 'mountain')
            optimize: Whether to optimize waypoint order (not directly supported by Mapy.cz)
            return_geometry: Whether to return route geometry
            validate_waypoints: Whether to validate and snap waypoints
            
        Returns:
            Route data including geometry, distance, and duration
        """
        if bike_type not in self.PROFILES:
            raise ValueError(f"Invalid bike type for Mapy.cz. Choose from: {list(self.PROFILES.keys())}")
        
        if len(waypoints) < 2:
            raise ValueError("At least 2 waypoints required")
        
        if len(waypoints) > 15:
            logger.warning(f"Too many waypoints ({len(waypoints)}). Using first 15 (Mapy.cz limit).")
            waypoints = waypoints[:15]
        
        # Validate waypoints if requested
        if validate_waypoints:
            logger.info("Validating waypoints for Mapy.cz...")
            original_count = len(waypoints)
            waypoints = self.validate_and_snap_waypoints(waypoints, bike_type)
            
            if len(waypoints) < 2:
                raise ValueError(
                    f"After validation, only {len(waypoints)} routable waypoints remain. "
                    f"Need at least 2. Try choosing a different area or reducing the distance."
                )
            
            if len(waypoints) < original_count:
                logger.warning(f"Reduced waypoints from {original_count} to {len(waypoints)} after validation")
        
        profile = self.PROFILES[bike_type]
        
        try:
            # Prepare request for Mapy.cz routing API
            start_coord = waypoints[0]
            end_coord = waypoints[-1]
            intermediate_waypoints = waypoints[1:-1] if len(waypoints) > 2 else []
            
            # Build API request
            params = {
                'start': f"{start_coord[0]},{start_coord[1]}",
                'end': f"{end_coord[0]},{end_coord[1]}",
                'routeType': profile,
                'lang': 'en'
            }
            
            # Add intermediate waypoints if any
            if intermediate_waypoints:
                waypoint_strings = [f"{wp[0]},{wp[1]}" for wp in intermediate_waypoints]
                params['waypoints'] = '|'.join(waypoint_strings)
            
            # Request route from Mapy.cz
            url = f"{self.base_url}/routing/route"
            logger.info(f"Requesting {bike_type} route from Mapy.cz with {len(waypoints)} waypoints")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            route_data = response.json()
            
            # Extract route information from Mapy.cz response
            if 'geometry' in route_data:
                # Convert Mapy.cz response to standard format
                result = {
                    'geometry': route_data.get('geometry', {}),
                    'distance': route_data.get('length', 0),  # meters
                    'duration': route_data.get('duration', 0),  # seconds
                    'ascent': route_data.get('ascent', 0),
                    'descent': route_data.get('descent', 0),
                    'waypoint_order': list(range(len(waypoints)))  # Mapy.cz doesn't optimize order
                }
                
                logger.info(f"Generated Mapy.cz route: {result['distance']/1000:.1f}km, "
                          f"{result['duration']/3600:.1f}h, "
                          f"ascent: {result['ascent']:.0f}m")
                
                return result
            else:
                raise ValueError("Invalid response from Mapy.cz API - no geometry data")
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Mapy.cz API error: {e}"
            logger.error(error_msg)
            
            if e.response.status_code == 429:
                raise ValueError("Mapy.cz rate limit exceeded. Please wait a moment before trying again.")
            elif e.response.status_code == 401:
                raise ValueError("Invalid Mapy.cz API key. Please check your API key configuration.")
            elif e.response.status_code == 400:
                raise ValueError("Invalid request parameters for Mapy.cz. Try different coordinates or reduce waypoints.")
            else:
                raise ValueError(f"Mapy.cz API error: {error_msg}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Mapy.cz request error: {e}")
            raise ValueError("Unable to connect to Mapy.cz routing service. Please try again later.")
        except Exception as e:
            logger.error(f"Mapy.cz route generation error: {e}")
            raise

    def create_gpx(self, route_data: Dict, name: str = "Mapy.cz Route") -> str:
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
                # Handle both [lon, lat] and [lon, lat, elevation] formats
                if len(coord) >= 2:
                    point = gpxpy.gpx.GPXTrackPoint(
                        latitude=coord[1],
                        longitude=coord[0],
                        elevation=coord[2] if len(coord) > 2 else None
                    )
                    segment.points.append(point)
        
        return gpx.to_xml()