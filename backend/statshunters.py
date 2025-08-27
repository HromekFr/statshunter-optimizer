import re
import requests
from typing import List, Tuple, Optional, Dict, Set
import mercantile
from shapely.geometry import shape, box
import logging

logger = logging.getLogger(__name__)

class StatshuntersClient:
    """Client for interacting with Statshunters API."""
    
    TILE_ZOOM = 14  # Statshunters uses zoom level 14 tiles
    
    def __init__(self, share_link: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Statshunters client.
        
        Args:
            share_link: Full share link (e.g., https://www.statshunters.com/share/abc123)
            api_key: Direct API key if available
        """
        self.share_code = None
        self.api_key = api_key
        
        if share_link:
            match = re.match(r"https://www\.statshunters\.com/share/(\w+)", share_link)
            if match:
                self.share_code = match.group(1)
            else:
                raise ValueError(f"Invalid share link format: {share_link}")
    
    def fetch_visited_tiles(self) -> Set[Tuple[int, int]]:
        """
        Fetch visited tiles from Statshunters.
        
        Returns:
            Set of (x, y) tile coordinates at zoom level 14
        """
        if not self.share_code and not self.api_key:
            raise ValueError("Either share_link or api_key must be provided")
        
        visited_tiles = set()
        
        if self.share_code:
            # Use share API endpoint with pagination
            base_url = f"https://www.statshunters.com/share/{self.share_code}/api/activities"
            page = 1
            
            try:
                while True:
                    url = f"{base_url}?page={page}" if page > 1 else base_url
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    activities = data.get('activities', [])
                    if not activities:  # No more pages
                        break
                    
                    # Extract tiles from activities
                    for activity in activities:
                        if 'tiles' in activity:
                            for tile in activity['tiles']:
                                if isinstance(tile, list) and len(tile) >= 2:
                                    visited_tiles.add((tile[0], tile[1]))
                                elif isinstance(tile, dict) and 'x' in tile and 'y' in tile:
                                    visited_tiles.add((tile['x'], tile['y']))
                    
                    page += 1
                    # Safety limit to prevent infinite loops
                    if page > 100:
                        logger.warning("Reached pagination limit of 100 pages")
                        break
                
                logger.info(f"Fetched {len(visited_tiles)} visited tiles from {page-1} pages")
                
            except requests.RequestException as e:
                logger.error(f"Error fetching tiles: {e}")
                raise
        
        elif self.api_key:
            # Try using API key as if it's a share code
            # Some users might paste just the share code instead of full URL
            logger.info("Trying to use provided API key as share code")
            
            # If API key looks like a share code, use it directly
            if len(self.api_key) > 10 and self.api_key.isalnum():
                base_url = f"https://www.statshunters.com/share/{self.api_key}/api/activities"
                page = 1
                
                try:
                    while True:
                        url = f"{base_url}?page={page}" if page > 1 else base_url
                        response = requests.get(url, timeout=30)
                        response.raise_for_status()
                        data = response.json()
                        
                        activities = data.get('activities', [])
                        if not activities:  # No more pages
                            break
                        
                        # Extract tiles from activities
                        for activity in activities:
                            if 'tiles' in activity:
                                for tile in activity['tiles']:
                                    if isinstance(tile, list) and len(tile) >= 2:
                                        visited_tiles.add((tile[0], tile[1]))
                                    elif isinstance(tile, dict) and 'x' in tile and 'y' in tile:
                                        visited_tiles.add((tile['x'], tile['y']))
                        
                        page += 1
                        # Safety limit to prevent infinite loops
                        if page > 100:
                            logger.warning("Reached pagination limit of 100 pages")
                            break
                    
                    logger.info(f"Fetched {len(visited_tiles)} visited tiles using API key as share code from {page-1} pages")
                    
                except requests.RequestException as e:
                    logger.error(f"Error using API key as share code: {e}")
                    raise ValueError(
                        "Could not access data with provided API key. "
                        "Please ensure you're using a valid Statshunters share link "
                        "(format: https://www.statshunters.com/share/abc123) "
                        "or the share code portion (abc123). "
                        "Get your share link from your Statshunters profile settings."
                    )
            else:
                raise ValueError(
                    "Invalid API key format. Statshunters primarily uses share links for API access. "
                    "Please use a share link from your profile: https://www.statshunters.com/share/YOUR_CODE"
                )
        
        return visited_tiles
    
    def get_tiles_in_bounds(self, west: float, south: float, east: float, north: float) -> Set[Tuple[int, int]]:
        """
        Get all tiles within geographic bounds.
        
        Args:
            west: Western longitude
            south: Southern latitude
            east: Eastern longitude
            north: Northern latitude
            
        Returns:
            Set of (x, y) tile coordinates at zoom level 14
        """
        tiles = set()
        
        # Get tile bounds at zoom level 14
        west_tile = mercantile.tile(west, north, self.TILE_ZOOM)
        east_tile = mercantile.tile(east, south, self.TILE_ZOOM)
        
        for x in range(west_tile.x, east_tile.x + 1):
            for y in range(west_tile.y, east_tile.y + 1):
                tiles.add((x, y))
        
        return tiles
    
    def get_unvisited_tiles(self, bounds: Tuple[float, float, float, float], 
                           visited_tiles: Optional[Set[Tuple[int, int]]] = None) -> Set[Tuple[int, int]]:
        """
        Get unvisited tiles within bounds.
        
        Args:
            bounds: (west, south, east, north) geographic bounds
            visited_tiles: Optional set of already visited tiles
            
        Returns:
            Set of unvisited (x, y) tile coordinates
        """
        if visited_tiles is None:
            visited_tiles = self.fetch_visited_tiles()
        
        all_tiles = self.get_tiles_in_bounds(*bounds)
        unvisited_tiles = all_tiles - visited_tiles
        
        logger.info(f"Found {len(unvisited_tiles)} unvisited tiles in bounds")
        return unvisited_tiles
    
    def tile_to_bounds(self, x: int, y: int) -> Tuple[float, float, float, float]:
        """
        Convert tile coordinates to geographic bounds.
        
        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            
        Returns:
            (west, south, east, north) bounds in degrees
        """
        tile = mercantile.Tile(x, y, self.TILE_ZOOM)
        bounds = mercantile.bounds(tile)
        return (bounds.west, bounds.south, bounds.east, bounds.north)
    
    def tiles_to_geojson(self, tiles: Set[Tuple[int, int]], properties: Optional[Dict] = None) -> Dict:
        """
        Convert tiles to GeoJSON format.
        
        Args:
            tiles: Set of (x, y) tile coordinates
            properties: Optional properties for each tile
            
        Returns:
            GeoJSON FeatureCollection
        """
        features = []
        
        for x, y in tiles:
            bounds = self.tile_to_bounds(x, y)
            geometry = box(bounds[0], bounds[1], bounds[2], bounds[3])
            
            feature = {
                "type": "Feature",
                "geometry": geometry.__geo_interface__,
                "properties": properties or {"tile": f"{x},{y},{self.TILE_ZOOM}"}
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }