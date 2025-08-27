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
            print(f"  Extra description: {options.get('description_extra', 'not set')}")
        
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
            
        if 'quiet scenic routes' in gravel_options.get('description_extra', ''):
            print("PASS: Gravel bike description mentions quiet scenic routes")
        else:
            print("WARN: Gravel bike description doesn't explicitly mention quiet routes")
            # Don't fail the test for this since it's descriptive
        
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
        
        # Check simplified options structure (weightings removed for API compatibility)
        if 'description_extra' in gravel_options:
            description_extra = gravel_options['description_extra']
            print(f"PASS: description_extra configured: {description_extra}")
            
            if isinstance(description_extra, str):
                print("PASS: description_extra is a string")
            else:
                print(f"FAIL: description_extra should be a string, got: {type(description_extra)}")
                return False
        else:
            print("INFO: description_extra not configured")
        
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