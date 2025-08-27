import math
import random
from typing import List, Tuple, Set, Dict, Optional
import numpy as np
from scipy.spatial.distance import cdist
import networkx as nx
import logging

logger = logging.getLogger(__name__)

class TileOptimizer:
    """Optimizer for finding routes that cover maximum unvisited tiles."""
    
    def __init__(self, visited_tiles: Set[Tuple[int, int]], all_tiles: Set[Tuple[int, int]]):
        """
        Initialize optimizer with tile data.
        
        Args:
            visited_tiles: Set of already visited tile coordinates
            all_tiles: Set of all tiles in the area
        """
        self.visited_tiles = visited_tiles
        self.unvisited_tiles = all_tiles - visited_tiles
        self.all_tiles = all_tiles
    
    def tile_to_center_with_offset(self, tile_x: int, tile_y: int, zoom: int = 14, road_bias: bool = True) -> Tuple[float, float]:
        """
        Get the center coordinate of a tile, optionally with small random offset to increase road hit probability.
        
        Args:
            tile_x: Tile X coordinate
            tile_y: Tile Y coordinate
            zoom: Zoom level
            road_bias: Whether to add small random offset to increase chance of hitting roads
            
        Returns:
            (lon, lat) center coordinate, possibly with offset
        """
        import mercantile
        import random
        
        tile = mercantile.Tile(tile_x, tile_y, zoom)
        bounds = mercantile.bounds(tile)
        
        lon = (bounds.west + bounds.east) / 2
        lat = (bounds.south + bounds.north) / 2
        
        if road_bias:
            # Add small random offset to increase probability of hitting a road
            # Tiles are roughly 300-600m at zoom 14, so offset by up to 25% of tile size
            tile_width = bounds.east - bounds.west
            tile_height = bounds.north - bounds.south
            
            lon_offset = (random.random() - 0.5) * tile_width * 0.5  # ±25% of tile width
            lat_offset = (random.random() - 0.5) * tile_height * 0.5  # ±25% of tile height
            
            lon += lon_offset
            lat += lat_offset
        
        return (lon, lat)

    def tile_to_center(self, tile_x: int, tile_y: int, zoom: int = 14) -> Tuple[float, float]:
        """
        Get the center coordinate of a tile.
        
        Args:
            tile_x: Tile X coordinate
            tile_y: Tile Y coordinate
            zoom: Zoom level
            
        Returns:
            (lon, lat) center coordinate
        """
        import mercantile
        tile = mercantile.Tile(tile_x, tile_y, zoom)
        bounds = mercantile.bounds(tile)
        
        lon = (bounds.west + bounds.east) / 2
        lat = (bounds.south + bounds.north) / 2
        return (lon, lat)
    
    def optimize_tile_coverage(self,
                              start_point: Tuple[float, float],
                              target_distance: float,
                              max_tiles: int = 30,
                              prefer_unvisited: bool = True) -> List[Tuple[float, float]]:
        """
        Find optimal waypoints to cover maximum tiles within distance constraint.
        
        Args:
            start_point: (lon, lat) starting coordinate
            target_distance: Target distance in kilometers
            max_tiles: Maximum number of tiles to include
            prefer_unvisited: Whether to prioritize unvisited tiles
            
        Returns:
            List of waypoint coordinates
        """
        # Convert tiles to coordinates
        tile_coords = []
        tile_weights = []
        
        tiles_to_consider = self.unvisited_tiles if prefer_unvisited else self.all_tiles
        
        for tile_x, tile_y in tiles_to_consider:
            coord = self.tile_to_center_with_offset(tile_x, tile_y, road_bias=True)
            tile_coords.append(coord)
            # Weight unvisited tiles higher
            weight = 2.0 if (tile_x, tile_y) in self.unvisited_tiles else 1.0
            tile_weights.append(weight)
        
        if not tile_coords:
            logger.warning("No tiles to optimize")
            return [start_point]
        
        # Find tiles within reasonable distance from start
        distances_from_start = [
            self.haversine_distance(start_point, coord) 
            for coord in tile_coords
        ]
        
        # Filter tiles within max_distance (half of target to allow return)
        max_radius = target_distance / 2
        nearby_indices = [
            i for i, d in enumerate(distances_from_start) 
            if d <= max_radius
        ]
        
        if not nearby_indices:
            logger.warning("No tiles within target distance")
            return [start_point]
        
        # Select subset of tiles using clustering or greedy approach
        selected_coords = self._greedy_tile_selection(
            start_point,
            [tile_coords[i] for i in nearby_indices],
            [tile_weights[i] for i in nearby_indices],
            target_distance,
            max_tiles
        )
        
        # Optimize order using TSP approximation
        optimized_path = self._optimize_path(start_point, selected_coords)
        
        return optimized_path
    
    def _greedy_tile_selection(self,
                               start: Tuple[float, float],
                               candidates: List[Tuple[float, float]],
                               weights: List[float],
                               max_distance: float,
                               max_tiles: int) -> List[Tuple[float, float]]:
        """
        Greedy selection of tiles to maximize coverage within distance.
        
        Args:
            start: Starting coordinate
            candidates: List of candidate tile coordinates
            weights: Weight for each candidate
            max_distance: Maximum total distance
            max_tiles: Maximum number of tiles
            
        Returns:
            Selected tile coordinates
        """
        selected = []
        remaining_distance = max_distance
        current_pos = start
        
        # Create list of (coord, weight, index) tuples
        weighted_candidates = list(zip(candidates, weights, range(len(candidates))))
        used_indices = set()
        
        while len(selected) < max_tiles and weighted_candidates:
            # Calculate distance-weighted scores for remaining candidates
            scores = []
            for coord, weight, idx in weighted_candidates:
                if idx not in used_indices:
                    dist = self.haversine_distance(current_pos, coord)
                    return_dist = self.haversine_distance(coord, start)
                    
                    # Check if we can visit this tile and return
                    if dist + return_dist <= remaining_distance:
                        # Score based on weight/distance ratio
                        score = weight / (dist + 0.1)  # Add small value to avoid division by zero
                        scores.append((score, coord, dist, idx))
            
            if not scores:
                break
            
            # Select best scoring tile
            scores.sort(reverse=True)
            best_score, best_coord, best_dist, best_idx = scores[0]
            
            selected.append(best_coord)
            used_indices.add(best_idx)
            remaining_distance -= best_dist
            current_pos = best_coord
            
            # Remove selected from candidates
            weighted_candidates = [
                (c, w, i) for c, w, i in weighted_candidates 
                if i != best_idx
            ]
        
        return selected
    
    def _optimize_path(self, start: Tuple[float, float], 
                      waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Optimize waypoint order using TSP approximation.
        
        Args:
            start: Starting coordinate
            waypoints: List of waypoints to visit
            
        Returns:
            Optimized path including start and end
        """
        if len(waypoints) <= 1:
            return [start] + waypoints + [start]
        
        # Start with original start point
        unvisited = waypoints.copy()
        current = start
        optimized = [start]
        
        # Greedy nearest neighbor
        while unvisited:
            distances = [self.haversine_distance(current, point) for point in unvisited]
            nearest_idx = distances.index(min(distances))
            nearest_point = unvisited.pop(nearest_idx)
            optimized.append(nearest_point)
            current = nearest_point
        
        # Return to start
        optimized.append(start)
        
        return optimized
    
    def haversine_distance(self, coord1: Tuple[float, float], 
                          coord2: Tuple[float, float]) -> float:
        """
        Calculate distance between two coordinates in kilometers.
        
        Args:
            coord1: (lon, lat) coordinate
            coord2: (lon, lat) coordinate
            
        Returns:
            Distance in kilometers
        """
        lon1, lat1 = coord1
        lon2, lat2 = coord2
        
        # Convert to radians
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        
        return c * r
    
    def cluster_tiles(self, tiles: Set[Tuple[int, int]], n_clusters: int = 5) -> List[Set[Tuple[int, int]]]:
        """
        Cluster tiles into groups for multi-day planning.
        
        Args:
            tiles: Set of tile coordinates
            n_clusters: Number of clusters to create
            
        Returns:
            List of tile clusters
        """
        if len(tiles) <= n_clusters:
            return [tiles]
        
        # Convert tiles to coordinates
        coords = np.array([self.tile_to_center(x, y) for x, y in tiles])
        
        # Simple distance-based clustering (fallback without sklearn)
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(coords)
        except ImportError:
            # Fallback: random assignment
            import random
            random.seed(42)
            labels = [random.randint(0, n_clusters-1) for _ in range(len(coords))]
        
        # Group tiles by cluster
        clusters = []
        for i in range(n_clusters):
            cluster_tiles = {
                tile for tile, label in zip(tiles, labels) 
                if label == i
            }
            if cluster_tiles:
                clusters.append(cluster_tiles)
        
        return clusters