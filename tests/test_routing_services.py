"""
Test suite for routing services (OpenRouteService and Mapy.cz).
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from routing_factory import RoutingServiceFactory
from mapy_routing import MapyRouteService
from mapy_waypoint_reducer import MapyWaypointReducer


class TestRoutingFactory(unittest.TestCase):
    """Test the routing service factory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RoutingServiceFactory()
    
    def test_factory_initialization(self):
        """Test factory initializes correctly."""
        self.assertIsNotNone(self.factory)
        services = self.factory.get_available_services()
        self.assertIsInstance(services, dict)
    
    def test_service_detection(self):
        """Test service availability detection."""
        # At least one service should be available if API keys are set
        services = self.factory.get_available_services()
        if os.getenv('ORS_API_KEY') or os.getenv('MAPY_API_KEY'):
            self.assertGreater(len(services), 0)
    
    def test_bike_type_validation(self):
        """Test bike type validation for services."""
        if 'openroute' in self.factory.get_available_services():
            self.assertTrue(self.factory.validate_service_bike_combination('openroute', 'road'))
            self.assertTrue(self.factory.validate_service_bike_combination('openroute', 'mountain'))
        
        if 'mapy' in self.factory.get_available_services():
            self.assertTrue(self.factory.validate_service_bike_combination('mapy', 'road'))
            self.assertTrue(self.factory.validate_service_bike_combination('mapy', 'mountain'))
            self.assertFalse(self.factory.validate_service_bike_combination('mapy', 'gravel'))


class TestMapyWaypointReducer(unittest.TestCase):
    """Test the Mapy.cz waypoint reducer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reducer = MapyWaypointReducer()
        # Create test waypoints (Prague area)
        self.waypoints = []
        for i in range(20):
            lon = 14.4378 + (i * 0.01)
            lat = 50.0755 + (i * 0.01)
            self.waypoints.append((lon, lat))
    
    def test_waypoint_limit(self):
        """Test waypoints are reduced to Mapy.cz limit."""
        reduced = self.reducer.reduce_waypoints(self.waypoints, target_distance=50)
        self.assertLessEqual(len(reduced), self.reducer.MAPY_MAX_WAYPOINTS)
        self.assertGreaterEqual(len(reduced), 2)  # At least start and end
    
    def test_preserves_start_end(self):
        """Test that start and end points are preserved."""
        reduced = self.reducer.reduce_waypoints(self.waypoints, target_distance=50)
        self.assertEqual(reduced[0], self.waypoints[0])
        self.assertEqual(reduced[-1], self.waypoints[-1])
    
    def test_strategy_selection(self):
        """Test correct strategy selection based on distance."""
        # Short distance - should use clustering
        strategy = self.reducer._select_strategy(distance=25, waypoint_count=20)
        self.assertEqual(strategy, 'clustering')
        
        # Medium distance - should use sampling
        strategy = self.reducer._select_strategy(distance=60, waypoint_count=20)
        self.assertEqual(strategy, 'sampling')
        
        # Long distance - should use corridor
        strategy = self.reducer._select_strategy(distance=150, waypoint_count=20)
        self.assertEqual(strategy, 'corridor')
    
    def test_no_reduction_needed(self):
        """Test that waypoints under limit are not reduced."""
        few_waypoints = self.waypoints[:10]
        reduced = self.reducer.reduce_waypoints(few_waypoints, target_distance=50)
        self.assertEqual(len(reduced), len(few_waypoints))


class TestMapyRouteService(unittest.TestCase):
    """Test the Mapy.cz route service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = os.getenv('MAPY_API_KEY', 'test_key')
        self.service = MapyRouteService(self.api_key)
    
    def test_service_initialization(self):
        """Test service initializes correctly."""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.api_key, self.api_key)
        self.assertIsNotNone(self.service.waypoint_reducer)
    
    def test_profile_mapping(self):
        """Test bike type to profile mapping."""
        self.assertEqual(self.service.PROFILES['road'], 'bike_road')
        self.assertEqual(self.service.PROFILES['mountain'], 'bike_mountain')
    
    @patch('requests.Session.get')
    def test_route_generation(self, mock_get):
        """Test route generation with mocked API response."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'geometry': {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[14.4378, 50.0755], [14.4400, 50.0800]]
                }
            },
            'length': 5000,
            'duration': 900,
            'ascent': 50,
            'descent': 30
        }
        mock_get.return_value = mock_response
        
        waypoints = [(14.4378, 50.0755), (14.4400, 50.0800)]
        result = self.service.generate_route(waypoints, bike_type='mountain')
        
        self.assertIn('geometry', result)
        self.assertIn('distance', result)
        self.assertIn('duration', result)
        self.assertEqual(result['distance'], 5000)
    
    @patch('requests.Session.get')
    def test_authentication_method(self, mock_get):
        """Test that API key is passed as URL parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'geometry': {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': []}}
        }
        mock_get.return_value = mock_response
        
        waypoints = [(14.4378, 50.0755), (14.4400, 50.0800)]
        self.service.generate_route(waypoints, bike_type='mountain')
        
        # Check that apikey was passed in params
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertIn('apikey', params)
        self.assertEqual(params['apikey'], self.api_key)
    
    def test_gpx_creation(self):
        """Test GPX file creation."""
        route_data = {
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    [14.4378, 50.0755],
                    [14.4400, 50.0800],
                    [14.4450, 50.0850]
                ]
            },
            'distance': 5000,
            'duration': 900
        }
        
        gpx = self.service.create_gpx(route_data, name="Test Route")
        
        self.assertIsNotNone(gpx)
        self.assertIn('<?xml', gpx)
        self.assertIn('<gpx', gpx)
        self.assertIn('<trk>', gpx)
        self.assertIn('<trkpt', gpx)
        self.assertIn('lat="50.0755"', gpx)
        self.assertIn('lon="14.4378"', gpx)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    @patch.dict(os.environ, {'MAPY_API_KEY': 'test_key', 'ORS_API_KEY': 'test_key'})
    def test_factory_creates_services(self):
        """Test factory can create services with mock API keys."""
        factory = RoutingServiceFactory()
        
        # Should have both services available with mock keys
        services = factory.get_available_services()
        self.assertIn('openroute', services)
        self.assertIn('mapy', services)
    
    def test_waypoint_optimization_flow(self):
        """Test the complete waypoint optimization flow."""
        reducer = MapyWaypointReducer()
        
        # Create many waypoints
        waypoints = []
        for i in range(30):
            waypoints.append((14.4 + i*0.01, 50.0 + i*0.01))
        
        # Reduce waypoints
        reduced = reducer.reduce_waypoints(waypoints, target_distance=100)
        
        # Check optimization worked
        self.assertLessEqual(len(reduced), 15)
        self.assertGreaterEqual(len(reduced), 2)
        
        # Check quality metrics
        quality = reducer.estimate_route_quality(waypoints, reduced)
        self.assertIn('waypoint_reduction', quality)
        self.assertIn('distance_ratio', quality)
        self.assertGreater(quality['waypoint_reduction'], 0)
        self.assertLessEqual(quality['waypoint_reduction'], 1)


if __name__ == '__main__':
    unittest.main()