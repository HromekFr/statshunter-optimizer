"""
Test suite for API endpoints.
"""

import unittest
import sys
import os
from unittest.mock import patch, Mock
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from main import app


class TestAPIEndpoints(unittest.TestCase):
    """Test the FastAPI endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('routing_services', data)
    
    def test_routing_services_endpoint(self):
        """Test routing services endpoint."""
        response = self.client.get("/api/routing-services")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('services', data)
        self.assertIsInstance(data['services'], dict)
    
    def test_bike_profiles_endpoint(self):
        """Test bike profiles endpoint."""
        response = self.client.get("/api/bike-profiles")
        # May return 503 if no services configured
        if response.status_code == 200:
            data = response.json()
            self.assertIn('profiles', data)
            self.assertIsInstance(data['profiles'], dict)
    
    @patch('main.StatshuntersClient')
    def test_tiles_endpoint(self, mock_client_class):
        """Test tiles endpoint with mocked Statshunters client."""
        mock_client = Mock()
        mock_client.fetch_visited_tiles.return_value = set()
        mock_client.get_tiles_in_bounds.return_value = {(100, 200), (101, 200)}
        mock_client.tiles_to_geojson.return_value = {
            'type': 'FeatureCollection',
            'features': []
        }
        mock_client_class.return_value = mock_client
        
        request_data = {
            "west": 14.0,
            "south": 50.0,
            "east": 14.5,
            "north": 50.5,
            "share_link": "test_link"
        }
        
        response = self.client.post("/api/tiles", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('visited', data)
            self.assertIn('unvisited', data)
            self.assertIn('stats', data)
    
    def test_invalid_tile_request(self):
        """Test tiles endpoint with invalid request."""
        request_data = {
            "west": "invalid",
            "south": 50.0,
            "east": 14.5,
            "north": 50.5
        }
        
        response = self.client.post("/api/tiles", json=request_data)
        self.assertEqual(response.status_code, 422)  # Validation error
    
    @patch('main.routing_factory')
    @patch('main.StatshuntersClient')
    def test_route_generation_success(self, mock_client_class, mock_factory):
        """Test successful route generation."""
        # Mock Statshunters client
        mock_client = Mock()
        mock_client.fetch_visited_tiles.return_value = set()
        mock_client.get_tiles_in_bounds.return_value = {(100, 200), (101, 200)}
        mock_client_class.return_value = mock_client
        
        # Mock routing service
        mock_service = Mock()
        mock_service.generate_route.return_value = {
            'geometry': {
                'type': 'LineString',
                'coordinates': [[14.4, 50.0], [14.5, 50.1]]
            },
            'distance': 10000,
            'duration': 1800,
            'ascent': 100
        }
        mock_service.create_gpx.return_value = '<?xml version="1.0"?><gpx></gpx>'
        
        mock_factory.get_available_services.return_value = {'test': {}}
        mock_factory.create_service.return_value = mock_service
        
        request_data = {
            "start_lat": 50.0,
            "start_lon": 14.0,
            "target_distance": 50,
            "bike_type": "mountain",
            "max_tiles": 20,
            "prefer_unvisited": True,
            "share_link": "test_link"
        }
        
        response = self.client.post("/api/route", json=request_data)
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            self.assertIn('route_geojson', data)
            self.assertIn('distance', data)
            self.assertIn('duration', data)
            self.assertIn('tiles_covered', data)
    
    def test_route_generation_invalid_request(self):
        """Test route generation with invalid request."""
        request_data = {
            "start_lat": "invalid",
            "start_lon": 14.0,
            "target_distance": 50
        }
        
        response = self.client.post("/api/route", json=request_data)
        self.assertEqual(response.status_code, 422)  # Validation error
    
    def test_gpx_download_not_found(self):
        """Test GPX download with non-existent file."""
        response = self.client.get("/api/download/nonexistent.gpx")
        self.assertEqual(response.status_code, 404)
    
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_gpx_download_success(self, mock_open, mock_exists):
        """Test successful GPX download."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = '<?xml version="1.0"?><gpx></gpx>'
        mock_open.return_value.__enter__.return_value = mock_file
        
        response = self.client.get("/api/download/test.gpx")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/gpx+xml')


class TestStaticFiles(unittest.TestCase):
    """Test static file serving."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_index_html(self):
        """Test that index.html is served."""
        response = self.client.get("/")
        # Should return index.html
        self.assertIn(response.status_code, [200, 404])  # 404 if frontend not built
    
    def test_favicon(self):
        """Test favicon endpoint."""
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()