#!/usr/bin/env python3
"""
Quick test script to verify the Statshunters Route Optimizer system.
This tests the core components without requiring external API keys.
"""

import sys
import os
import json
from typing import Set, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_tile_system():
    """Test the tile coordinate system and basic functionality."""
    print("Testing tile system...")
    
    try:
        from statshunters import StatshuntersClient
        
        # Test tile coordinate conversion (without API calls)
        client = StatshuntersClient()  # No credentials for testing basic functions
        
        # Test tile bounds calculation
        bounds = client.tile_to_bounds(8800, 5400)  # Example tile in Berlin area
        print(f"PASS Tile bounds calculation: {bounds}")
        
        # Test tiles in bounds
        tiles = client.get_tiles_in_bounds(13.0, 52.3, 13.8, 52.7)  # Berlin area
        print(f"PASS Found {len(tiles)} tiles in Berlin area")
        
        # Test GeoJSON conversion
        sample_tiles = {(8800, 5400), (8801, 5400), (8800, 5401)}
        geojson = client.tiles_to_geojson(sample_tiles)
        print(f"PASS GeoJSON conversion: {len(geojson['features'])} features")
        
        return True
        
    except Exception as e:
        print(f"FAIL Tile system test failed: {e}")
        return False

def test_optimizer():
    """Test the route optimization algorithm."""
    print("Testing route optimizer...")
    
    try:
        from optimizer import TileOptimizer
        
        # Create sample tile data
        visited_tiles = {(100, 100), (101, 100), (100, 101)}
        all_tiles = {(100, 100), (101, 100), (100, 101), (102, 100), (100, 102), (101, 101)}
        
        optimizer = TileOptimizer(visited_tiles, all_tiles)
        
        # Test distance calculation
        dist = optimizer.haversine_distance((13.404954, 52.520008), (13.424954, 52.540008))
        print(f"PASS Distance calculation: {dist:.2f} km")
        
        # Test tile center conversion
        center = optimizer.tile_to_center(8800, 5400)
        print(f"PASS Tile center: {center}")
        
        # Test route optimization (simplified)
        start = (13.404954, 52.520008)  # Berlin
        waypoints = optimizer.optimize_tile_coverage(
            start_point=start,
            target_distance=20,
            max_tiles=5,
            prefer_unvisited=True
        )
        print(f"PASS Route optimization: {len(waypoints)} waypoints")
        
        return True
        
    except Exception as e:
        print(f"FAIL Optimizer test failed: {e}")
        return False

def test_routing_config():
    """Test routing service configuration (without API calls)."""
    print("Testing routing service config...")
    
    try:
        from routing import RouteService
        
        # Test profile mapping
        profiles = RouteService.PROFILES
        expected_profiles = {'road', 'gravel', 'mountain', 'ebike'}
        
        if set(profiles.keys()) >= expected_profiles:
            print(f"PASS Bike profiles available: {list(profiles.keys())}")
            print(f"PASS Profile mapping: {profiles}")
            return True
        else:
            print(f"FAIL Missing bike profiles. Expected: {expected_profiles}, Got: {set(profiles.keys())}")
            return False
        
    except Exception as e:
        print(f"FAIL Routing config test failed: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available."""
    print("Testing dependencies...")
    
    required_modules = [
        'fastapi', 'uvicorn', 'requests', 'mercantile', 
        'shapely', 'geojson', 'gpxpy', 'openrouteservice',
        'numpy', 'scipy', 'networkx'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"PASS {module}")
        except ImportError:
            print(f"FAIL {module} - MISSING")
            missing.append(module)
    
    if missing:
        print(f"\nFAIL Missing dependencies: {missing}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def test_file_structure():
    """Test that all required files are present."""
    print("Testing file structure...")
    
    required_files = [
        'requirements.txt',
        '.env.example',
        'README.md',
        'backend/main.py',
        'backend/statshunters.py',
        'backend/routing.py',
        'backend/optimizer.py',
        'frontend/index.html',
        'frontend/styles.css',
        'frontend/app.js'
    ]
    
    missing = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"PASS {file_path}")
        else:
            print(f"FAIL {file_path} - MISSING")
            missing.append(file_path)
    
    if missing:
        print(f"\nFAIL Missing files: {missing}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("Statshunters Route Optimizer - System Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Dependencies", test_dependencies),
        ("Tile System", test_tile_system),
        ("Route Optimizer", test_optimizer),
        ("Routing Config", test_routing_config)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 30)
        results.append(test_func())
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results)
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\nAll tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your Statshunters share link and ORS API key to .env")
        print("3. Run: cd backend && python main.py")
        print("4. Open http://localhost:8000 in your browser")
    else:
        print(f"\n{total_tests - total_passed} test(s) failed. Please fix issues before running.")
        sys.exit(1)

if __name__ == "__main__":
    main()