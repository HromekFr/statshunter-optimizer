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
    
    # Routing options for each bike type to prefer cycling infrastructure
    PROFILE_OPTIONS = {
        'road': {
            'avoid_features': ['highways'],
            'prefer_greenness': False,  # Road bikes prefer faster routes
            'profile_params': {
                'weightings': {
                    'steepness_difficulty': 1,  # Moderate difficulty
                    'green': 0.2,
                    'quiet': 0.1
                }
            }
        },
        'gravel': {
            'avoid_features': ['highways'],
            'prefer_greenness': True,  # Gravel bikes can use green routes
            'profile_params': {
                'weightings': {
                    'steepness_difficulty': 2,  # Amateur level - can handle more terrain
                    'green': 0.8,  # Prefer green/quiet routes
                    'quiet': 0.8
                }
            }
        },
        'mountain': {
            'avoid_features': [],  # Mountain bikes can handle most terrain
            'prefer_greenness': True,
            'profile_params': {
                'weightings': {
                    'steepness_difficulty': 3,  # Pro level - can handle steep terrain
                    'green': 0.9,  # Strong preference for trails/paths
                    'quiet': 0.9
                }
            }
        },
        'ebike': {
            'avoid_features': ['highways'],
            'prefer_greenness': True,  # E-bikes good for leisure routes
            'profile_params': {
                'weightings': {
                    'steepness_difficulty': 0,  # Novice level - e-bike assists with hills
                    'green': 0.6,
                    'quiet': 0.6
                }
            }
        }
    }
    
    def __init__(self, api_key: str):
        """
        Initialize route service with OpenRouteService API key.
        
        Args:
            api_key: OpenRouteService API key
        """
        self.client = openrouteservice.Client(key=api_key)
    
    def get_route_preferences(self, bike_type: str) -> Dict:
        """
        Get routing preferences description for a bike type.
        
        Args:
            bike_type: Type of bike
            
        Returns:
            Dictionary describing routing preferences
        """
        profile_options = self.PROFILE_OPTIONS.get(bike_type, {})
        
        descriptions = {
            'road': 'Optimized for road cycling: avoids highways, moderate difficulty, prioritizes speed over scenery',
            'gravel': 'Optimized for gravel/adventure cycling: avoids highways, prefers quiet green routes and cycling paths, handles varied terrain',
            'mountain': 'Optimized for mountain biking: allows all terrain including trails, strongly prefers green routes and paths, handles steep terrain',
            'ebike': 'Optimized for e-bike touring: avoids highways, prefers quiet scenic routes, gentle gradients (e-motor assists with hills)'
        }
        
        return {
            'profile': self.PROFILES.get(bike_type, 'cycling-regular'),
            'description': descriptions.get(bike_type, 'Standard cycling route'),
            'avoids': profile_options.get('avoid_features', []),
            'prefers_green_routes': profile_options.get('prefer_greenness', False),
            'difficulty_level': profile_options.get('profile_params', {}).get('weightings', {}).get('steepness_difficulty', 1)
        }
    
    def validate_and_snap_waypoints(self, waypoints: List[Tuple[float, float]], bike_type: str = 'gravel') -> List[Tuple[float, float]]:
        """
        Validate waypoints and snap them to nearest routable points.
        
        Args:
            waypoints: List of (lon, lat) coordinates
            bike_type: Type of bike for routing profile
            
        Returns:
            List of validated and snapped waypoints
        """
        if not waypoints:
            return waypoints
            
        profile = self.PROFILES.get(bike_type, 'cycling-regular')
        validated_waypoints = []
        
        for i, (lon, lat) in enumerate(waypoints):
            try:
                # Try to find a routable point near this coordinate using isochrones
                # This is a lightweight way to test if a point is routable
                test_result = self.client.isochrones(
                    locations=[[lon, lat]],
                    profile=profile,
                    range=[500],  # 500 meter range
                    range_type='distance'
                )
                
                # If isochrones works, the point is routable
                validated_waypoints.append((lon, lat))
                logger.info(f"Waypoint {i} at ({lon:.6f}, {lat:.6f}) is routable")
                
            except Exception as e:
                logger.warning(f"Waypoint {i} at ({lon:.6f}, {lat:.6f}) is not routable: {e}")
                
                # Try to find a nearby routable point by searching in expanding circles
                snapped_point = self._find_nearest_routable_point(lon, lat, profile)
                if snapped_point:
                    validated_waypoints.append(snapped_point)
                    logger.info(f"Snapped waypoint {i} to ({snapped_point[0]:.6f}, {snapped_point[1]:.6f})")
                else:
                    logger.warning(f"Could not find routable alternative for waypoint {i}, skipping")
        
        return validated_waypoints
    
    def _find_nearest_routable_point(self, lon: float, lat: float, profile: str, max_radius: float = 2000) -> Optional[Tuple[float, float]]:
        """
        Find the nearest routable point within max_radius meters.
        
        Args:
            lon: Longitude of original point
            lat: Latitude of original point  
            profile: Routing profile to use
            max_radius: Maximum search radius in meters
            
        Returns:
            (lon, lat) of nearest routable point or None if not found
        """
        import math
        
        # Convert meters to approximate degrees (rough approximation)
        lat_deg_per_meter = 1 / 111000
        lon_deg_per_meter = 1 / (111000 * math.cos(math.radians(lat)))
        
        # Try points in expanding squares around the original point
        for radius_m in [200, 500, 1000, 2000]:
            if radius_m > max_radius:
                break
                
            lat_offset = radius_m * lat_deg_per_meter
            lon_offset = radius_m * lon_deg_per_meter
            
            # Test points in cardinal directions
            test_points = [
                (lon, lat + lat_offset),      # North
                (lon, lat - lat_offset),      # South
                (lon + lon_offset, lat),      # East
                (lon - lon_offset, lat),      # West
                (lon + lon_offset/2, lat + lat_offset/2),  # Northeast
                (lon - lon_offset/2, lat + lat_offset/2),  # Northwest  
                (lon + lon_offset/2, lat - lat_offset/2),  # Southeast
                (lon - lon_offset/2, lat - lat_offset/2),  # Southwest
            ]
            
            for test_lon, test_lat in test_points:
                try:
                    # Test if this point is routable
                    self.client.isochrones(
                        locations=[[test_lon, test_lat]],
                        profile=profile,
                        range=[100],
                        range_type='distance'
                    )
                    return (test_lon, test_lat)
                except:
                    continue
        
        return None

    def generate_route(self, 
                      waypoints: List[Tuple[float, float]], 
                      bike_type: str = 'gravel',
                      optimize: bool = True,
                      return_geometry: bool = True,
                      validate_waypoints: bool = True) -> Dict:
        """
        Generate a cycling route through waypoints.
        
        Args:
            waypoints: List of (lon, lat) coordinates
            bike_type: Type of bike ('road', 'gravel', 'mountain', 'ebike')
            optimize: Whether to optimize waypoint order
            return_geometry: Whether to return route geometry
            validate_waypoints: Whether to validate and snap waypoints to roads
            
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
        
        # Validate and snap waypoints to routable points
        if validate_waypoints:
            logger.info("Validating and snapping waypoints to roads...")
            original_count = len(waypoints)
            waypoints = self.validate_and_snap_waypoints(waypoints, bike_type)
            
            if len(waypoints) < 2:
                raise ValueError(
                    f"After validation, only {len(waypoints)} routable waypoints remain. "
                    f"Need at least 2. Try choosing a different area with more roads, "
                    f"or reduce the target distance."
                )
            
            if len(waypoints) < original_count:
                logger.warning(f"Reduced waypoints from {original_count} to {len(waypoints)} after validation")
        
        profile = self.PROFILES[bike_type]
        profile_options = self.PROFILE_OPTIONS.get(bike_type, {})
        
        # Build routing options
        routing_options = {}
        
        # Add avoidance preferences
        if profile_options.get('avoid_features'):
            routing_options['avoid_features'] = profile_options['avoid_features']
        
        # Add profile-specific parameters
        if profile_options.get('profile_params'):
            routing_options.update(profile_options['profile_params'])
        
        try:
            # Generate route with cycling-optimized options
            request_params = {
                'coordinates': waypoints,
                'profile': profile,
                'format': 'geojson',
                'optimize_waypoints': optimize,
                'geometry': return_geometry,
                'instructions': False,  # We don't need turn-by-turn instructions
                'elevation': True,  # Include elevation data
                'radiuses': [-1] * len(waypoints)  # Allow snapping to roads
            }
            
            # Add cycling-specific options
            if routing_options:
                request_params['options'] = routing_options
            
            route = self.client.directions(**request_params)
            
            logger.info(f"Generated {bike_type} route with cycling preferences: "
                       f"avoid={profile_options.get('avoid_features', [])}, "
                       f"green preference={profile_options.get('prefer_greenness', False)}")
            
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