import math
import logging
from typing import List, Tuple, Optional, Dict
import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist

logger = logging.getLogger(__name__)

class MapyWaypointReducer:
    """
    Intelligent waypoint reducer for Mapy.cz API that respects the 15 waypoint limit
    while maintaining optimal route coverage and tile hunting effectiveness.
    """
    
    MAPY_MAX_WAYPOINTS = 15
    
    def __init__(self):
        """Initialize the waypoint reducer."""
        pass
    
    def reduce_waypoints(self, 
                        waypoints: List[Tuple[float, float]], 
                        target_distance: float,
                        strategy: str = 'auto') -> List[Tuple[float, float]]:
        """
        Reduce waypoints to fit Mapy.cz limitations while maintaining route quality.
        
        Args:
            waypoints: List of (lon, lat) waypoint coordinates
            target_distance: Target route distance in kilometers
            strategy: Reduction strategy ('auto', 'clustering', 'sampling', 'corridor')
            
        Returns:
            Optimized list of waypoints (max 15)
        """
        if len(waypoints) <= self.MAPY_MAX_WAYPOINTS:
            logger.info(f"Waypoints ({len(waypoints)}) already within Mapy.cz limit")
            return waypoints
        
        logger.info(f"Reducing {len(waypoints)} waypoints to {self.MAPY_MAX_WAYPOINTS} for Mapy.cz")
        
        # Auto-select strategy based on distance
        if strategy == 'auto':
            strategy = self._select_strategy(target_distance, len(waypoints))
        
        if strategy == 'clustering':
            return self._cluster_waypoints(waypoints)
        elif strategy == 'sampling':
            return self._sample_waypoints(waypoints, target_distance)
        elif strategy == 'corridor':
            return self._corridor_waypoints(waypoints)
        else:
            logger.warning(f"Unknown strategy '{strategy}', falling back to sampling")
            return self._sample_waypoints(waypoints, target_distance)
    
    def _select_strategy(self, distance: float, waypoint_count: int) -> str:
        """
        Automatically select the best reduction strategy based on route characteristics.
        
        Args:
            distance: Target distance in km
            waypoint_count: Number of original waypoints
            
        Returns:
            Strategy name
        """
        if distance < 30:
            # Short routes: Use clustering to maintain local coverage
            return 'clustering'
        elif distance < 75:
            # Medium routes: Use smart sampling
            return 'sampling'
        else:
            # Long routes: Use corridor approach
            return 'corridor'
    
    def _cluster_waypoints(self, waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Use k-means clustering to group waypoints and select cluster centers.
        Best for short routes where waypoints are densely packed.
        
        Args:
            waypoints: Original waypoints
            
        Returns:
            Reduced waypoints using clustering
        """
        if len(waypoints) <= self.MAPY_MAX_WAYPOINTS:
            return waypoints
        
        # Always preserve start and end points
        start_point = waypoints[0]
        end_point = waypoints[-1]
        middle_points = waypoints[1:-1]
        
        if len(middle_points) <= self.MAPY_MAX_WAYPOINTS - 2:
            return waypoints
        
        # Convert to numpy array for sklearn
        points_array = np.array(middle_points)
        
        # Number of clusters for middle points (reserve 2 spots for start/end)
        n_clusters = min(self.MAPY_MAX_WAYPOINTS - 2, len(middle_points))
        
        try:
            # Perform k-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit(points_array)
            
            # Use cluster centers as waypoints
            cluster_centers = clusters.cluster_centers_.tolist()
            
            # Convert back to tuples
            reduced_middle = [(lon, lat) for lon, lat in cluster_centers]
            
            # Combine with preserved start/end
            result = [start_point] + reduced_middle + [end_point]
            
            logger.info(f"Clustering reduced {len(waypoints)} waypoints to {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}, falling back to sampling")
            return self._sample_waypoints(waypoints, distance=50)  # fallback distance
    
    def _sample_waypoints(self, waypoints: List[Tuple[float, float]], target_distance: float) -> List[Tuple[float, float]]:
        """
        Use strategic sampling to select waypoints based on importance and spacing.
        
        Args:
            waypoints: Original waypoints
            target_distance: Target distance for route
            
        Returns:
            Strategically sampled waypoints
        """
        if len(waypoints) <= self.MAPY_MAX_WAYPOINTS:
            return waypoints
        
        # Always preserve start and end
        start_point = waypoints[0]
        end_point = waypoints[-1]
        middle_points = waypoints[1:-1]
        
        if len(middle_points) <= self.MAPY_MAX_WAYPOINTS - 2:
            return waypoints
        
        # Calculate distances between consecutive waypoints
        distances = []
        for i in range(len(waypoints) - 1):
            dist = self._haversine_distance(waypoints[i], waypoints[i + 1])
            distances.append(dist)
        
        # Calculate cumulative distances to use for sampling
        cumulative_distances = [0]
        for dist in distances:
            cumulative_distances.append(cumulative_distances[-1] + dist)
        
        total_distance = cumulative_distances[-1]
        
        # Number of middle waypoints to select
        n_middle = self.MAPY_MAX_WAYPOINTS - 2
        
        # Sample waypoints at even intervals along the route
        selected_indices = []
        for i in range(1, n_middle + 1):
            target_distance_point = (i / (n_middle + 1)) * total_distance
            
            # Find closest waypoint to this distance
            closest_idx = 0
            min_diff = float('inf')
            for j, cum_dist in enumerate(cumulative_distances):
                diff = abs(cum_dist - target_distance_point)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = j
            
            if closest_idx not in selected_indices and 0 < closest_idx < len(waypoints) - 1:
                selected_indices.append(closest_idx)
        
        # Sort indices and get corresponding waypoints
        selected_indices.sort()
        selected_middle = [waypoints[i] for i in selected_indices]
        
        result = [start_point] + selected_middle + [end_point]
        
        logger.info(f"Sampling reduced {len(waypoints)} waypoints to {len(result)}")
        return result
    
    def _corridor_waypoints(self, waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        For long routes, select waypoints that maintain the route corridor.
        Focuses on key directional changes and important waypoints.
        
        Args:
            waypoints: Original waypoints
            
        Returns:
            Corridor-optimized waypoints
        """
        if len(waypoints) <= self.MAPY_MAX_WAYPOINTS:
            return waypoints
        
        # Always preserve start and end
        start_point = waypoints[0]
        end_point = waypoints[-1]
        
        if len(waypoints) <= 3:
            return waypoints
        
        # Calculate bearing changes to identify important turning points
        important_indices = [0]  # Always include start
        
        for i in range(1, len(waypoints) - 1):
            # Calculate bearings
            bearing1 = self._calculate_bearing(waypoints[i-1], waypoints[i])
            bearing2 = self._calculate_bearing(waypoints[i], waypoints[i+1])
            
            # Calculate bearing change
            bearing_change = abs(bearing2 - bearing1)
            if bearing_change > 180:
                bearing_change = 360 - bearing_change
            
            # Include waypoints with significant direction changes
            if bearing_change > 30:  # 30 degree threshold
                important_indices.append(i)
        
        important_indices.append(len(waypoints) - 1)  # Always include end
        
        # If we have too many important waypoints, sample them
        if len(important_indices) > self.MAPY_MAX_WAYPOINTS:
            # Keep start/end and sample the rest
            middle_important = important_indices[1:-1]
            n_middle = self.MAPY_MAX_WAYPOINTS - 2
            
            step = len(middle_important) // n_middle
            sampled_middle = middle_important[::max(1, step)][:n_middle]
            
            important_indices = [0] + sampled_middle + [len(waypoints) - 1]
        
        # If we still don't have enough waypoints, add evenly spaced ones
        while len(important_indices) < self.MAPY_MAX_WAYPOINTS and len(important_indices) < len(waypoints):
            # Find largest gap and add a waypoint there
            largest_gap = 0
            gap_middle = 0
            
            for i in range(len(important_indices) - 1):
                gap_size = important_indices[i + 1] - important_indices[i]
                if gap_size > largest_gap:
                    largest_gap = gap_size
                    gap_middle = (important_indices[i] + important_indices[i + 1]) // 2
            
            if largest_gap > 1 and gap_middle not in important_indices:
                important_indices.append(gap_middle)
                important_indices.sort()
        
        result = [waypoints[i] for i in important_indices]
        
        logger.info(f"Corridor method reduced {len(waypoints)} waypoints to {len(result)}")
        return result
    
    def _haversine_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            point1: (lon, lat) of first point
            point2: (lon, lat) of second point
            
        Returns:
            Distance in kilometers
        """
        lon1, lat1 = point1
        lon2, lat2 = point2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def _calculate_bearing(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        Calculate the bearing from point1 to point2.
        
        Args:
            point1: (lon, lat) of first point
            point2: (lon, lat) of second point
            
        Returns:
            Bearing in degrees (0-360)
        """
        lon1, lat1 = point1
        lon2, lat2 = point2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def estimate_route_quality(self, 
                             original_waypoints: List[Tuple[float, float]], 
                             reduced_waypoints: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        Estimate the quality loss from waypoint reduction.
        
        Args:
            original_waypoints: Original waypoint list
            reduced_waypoints: Reduced waypoint list
            
        Returns:
            Quality metrics dictionary
        """
        # Calculate coverage efficiency
        original_distance = sum(
            self._haversine_distance(original_waypoints[i], original_waypoints[i+1])
            for i in range(len(original_waypoints) - 1)
        )
        
        reduced_distance = sum(
            self._haversine_distance(reduced_waypoints[i], reduced_waypoints[i+1])
            for i in range(len(reduced_waypoints) - 1)
        )
        
        # Calculate waypoint density
        original_density = len(original_waypoints) / original_distance if original_distance > 0 else 0
        reduced_density = len(reduced_waypoints) / reduced_distance if reduced_distance > 0 else 0
        
        return {
            'waypoint_reduction': len(reduced_waypoints) / len(original_waypoints),
            'distance_ratio': reduced_distance / original_distance if original_distance > 0 else 1.0,
            'density_ratio': reduced_density / original_density if original_density > 0 else 1.0,
            'original_waypoints': len(original_waypoints),
            'reduced_waypoints': len(reduced_waypoints),
            'original_distance': original_distance,
            'reduced_distance': reduced_distance
        }