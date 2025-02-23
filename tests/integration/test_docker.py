import requests
import json
import time
import sys

def test_frontend():
    """Test if frontend is accessible"""
    try:
        response = requests.get('http://localhost:80')
        assert response.status_code == 200
        print("✅ Frontend is accessible")
        return True
    except Exception as e:
        print(f"❌ Frontend test failed: {str(e)}")
        return False

def test_backend_health():
    """Test if backend health check is working"""
    try:
        response = requests.get('http://localhost:8000/health')
        assert response.status_code == 200
        print("✅ Backend health check passed")
        return True
    except Exception as e:
        print(f"❌ Backend health check failed: {str(e)}")
        return False

def test_schema_endpoints():
    """Test basic schema operations"""
    try:
        # Test schema listing
        response = requests.get('http://localhost:8000/schemas')
        assert response.status_code == 200
        schemas = response.json()
        print("✅ Schema listing works")

        # If there are schemas, test getting one
        if schemas:
            schema_id = schemas[0]['id']
            response = requests.get(f'http://localhost:8000/schemas/{schema_id}')
            assert response.status_code == 200
            print("✅ Schema retrieval works")
        
        return True
    except Exception as e:
        print(f"❌ Schema operations failed with response: {str(e)}")
        # Print detailed response if available
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return False

def run_all_tests():
    """Run all tests and return overall status"""
    tests = [
        test_frontend,
        test_backend_health,
        test_schema_endpoints
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test {test.__name__} failed with error: {str(e)}")
            results.append(False)
    
    # Overall status
    if all(results):
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    print("Starting ReproSchema Docker tests...")
    time.sleep(5)  # Give services time to fully start
    sys.exit(run_all_tests())