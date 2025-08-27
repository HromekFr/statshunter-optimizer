#!/usr/bin/env python3
"""
Test the new cycling route preferences system.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_bike_profile_options():
    """Test that bike profiles have correct cycling preferences."""
    print("Testing bike profile cycling preferences...")
    
    try:
        from routing import RouteService
        
        # Test that profile options are configured
        profiles = RouteService.PROFILES
        profile_options = RouteService.PROFILE_OPTIONS
        
        print("Available bike types and their preferences:")
        
        for bike_type in profiles.keys():
            options = profile_options.get(bike_type, {})
            avoid_features = options.get('avoid_features', [])
            prefer_green = options.get('prefer_greenness', False)
            weightings = options.get('profile_params', {}).get('weightings', {})
            
            print(f"\n{bike_type.upper()}:")
            print(f"  Profile: {profiles[bike_type]}")
            print(f"  Avoids: {avoid_features}")
            print(f"  Prefers green routes: {prefer_green}")
            print(f"  Green weighting: {weightings.get('green', 'not set')}")
            print(f"  Quiet weighting: {weightings.get('quiet', 'not set')}")
            print(f"  Steepness difficulty: {weightings.get('steepness_difficulty', 'not set')}")
        
        # Test specific gravel bike preferences
        gravel_options = profile_options.get('gravel', {})
        
        # Verify gravel bike has cycling-friendly settings
        if 'highways' in gravel_options.get('avoid_features', []):
            print("\nPASS: Gravel bike avoids highways")
        else:
            print("\nFAIL: Gravel bike should avoid highways")
            return False
            
        if gravel_options.get('prefer_greenness', False):
            print("PASS: Gravel bike prefers green/quiet routes")
        else:
            print("FAIL: Gravel bike should prefer green routes")
            return False
            
        green_weight = gravel_options.get('profile_params', {}).get('weightings', {}).get('green', 0)
        if green_weight >= 0.5:
            print(f"PASS: Gravel bike has high green route preference (weight: {green_weight})")
        else:
            print(f"FAIL: Gravel bike should have high green route preference, got: {green_weight}")
            return False
        
        return True
        
    except Exception as e:
        print(f"FAIL: Profile options test failed: {e}")
        return False

def test_route_preferences_api():
    """Test the route preferences description system."""
    print("Testing route preferences API...")
    
    try:
        from routing import RouteService
        
        # Create a mock service (without API key for testing)
        service = RouteService.__new__(RouteService)  # Create without calling __init__
        service.PROFILES = RouteService.PROFILES
        service.PROFILE_OPTIONS = RouteService.PROFILE_OPTIONS
        
        # Test get_route_preferences method
        gravel_prefs = service.get_route_preferences('gravel')
        
        print(f"Gravel bike preferences: {gravel_prefs}")
        
        # Verify expected fields
        required_fields = ['profile', 'description', 'avoids', 'prefers_green_routes', 'difficulty_level']
        for field in required_fields:
            if field in gravel_prefs:
                print(f"PASS: Field '{field}' present")
            else:
                print(f"FAIL: Field '{field}' missing")
                return False
        
        # Verify gravel-specific values
        if gravel_prefs['prefers_green_routes']:
            print("PASS: Gravel preferences indicate green route preference")
        else:
            print("FAIL: Gravel should prefer green routes")
            return False
            
        if 'highways' in gravel_prefs['avoids']:
            print("PASS: Gravel preferences avoid highways")
        else:
            print("FAIL: Gravel should avoid highways")
            return False
            
        if 'cycling paths' in gravel_prefs['description'].lower():
            print("PASS: Gravel description mentions cycling paths")
        else:
            print("WARN: Gravel description doesn't explicitly mention cycling paths")
        
        return True
        
    except Exception as e:
        print(f"FAIL: Route preferences API test failed: {e}")
        return False

def test_routing_options_format():
    """Test that routing options are properly formatted for OpenRouteService."""
    print("Testing routing options format...")
    
    try:
        from routing import RouteService
        
        # Test gravel bike routing options format
        gravel_options = RouteService.PROFILE_OPTIONS['gravel']
        
        # Check structure
        if 'avoid_features' in gravel_options:
            avoid_features = gravel_options['avoid_features']
            if isinstance(avoid_features, list):
                print(f"PASS: avoid_features is a list: {avoid_features}")
            else:
                print(f"FAIL: avoid_features should be a list, got: {type(avoid_features)}")
                return False
        
        if 'profile_params' in gravel_options:
            profile_params = gravel_options['profile_params']
            if isinstance(profile_params, dict):
                print("PASS: profile_params is a dictionary")
                
                if 'weightings' in profile_params:
                    weightings = profile_params['weightings']
                    print(f"PASS: weightings configured: {weightings}")
                    
                    # Check that weightings are numeric
                    for key, value in weightings.items():
                        if isinstance(value, (int, float)):
                            print(f"PASS: {key} weighting is numeric: {value}")
                        else:
                            print(f"FAIL: {key} weighting should be numeric, got: {type(value)}")
                            return False
                else:
                    print("FAIL: profile_params missing weightings")
                    return False
            else:
                print(f"FAIL: profile_params should be a dict, got: {type(profile_params)}")
                return False
        
        return True
        
    except Exception as e:
        print(f"FAIL: Routing options format test failed: {e}")
        return False

def main():
    """Run cycling preferences tests."""
    print("Testing Cycling Route Preferences")
    print("=" * 40)
    
    tests = [
        ("Bike Profile Options", test_bike_profile_options),
        ("Route Preferences API", test_route_preferences_api),
        ("Routing Options Format", test_routing_options_format),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 30)
        results.append(test_func())
    
    print("\n" + "=" * 40)
    print("TEST RESULTS")
    print("=" * 40)
    
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results)
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\nCycling preferences are properly configured!")
        print("\nKey improvements for gravel bike routing:")
        print("- Avoids highways for safer cycling")
        print("- Prefers green routes and cycling paths")
        print("- Optimized for quiet, scenic routes")
        print("- Higher difficulty tolerance for varied terrain")
    else:
        print(f"\n{total_tests - total_passed} test(s) failed.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())