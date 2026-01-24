#!/usr/bin/env python3
"""
Quick smoke test for new PPWR bulk action routes
Tests the 3 new API endpoints without modifying data
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"
TEST_SKU = "TEST_SKU_PPWR"

def test_declarations_list():
    """Test GET /api/ppwr/declarations/<sku>"""
    print("\n1. Testing GET /api/ppwr/declarations/<sku>...")
    url = f"{BASE_URL}/api/ppwr/declarations/{TEST_SKU}"
    
    try:
        resp = requests.get(url, timeout=10)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Total rows: {data.get('total', 0)}")
            if data.get('rows'):
                print(f"   First row: {json.dumps(data['rows'][0], indent=2)}")
            return True
        else:
            print(f"   Error: {resp.text}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False


def test_mapping_table():
    """Test GET /api/ppwr/mapping/<sku>"""
    print("\n2. Testing GET /api/ppwr/mapping/<sku>...")
    url = f"{BASE_URL}/api/ppwr/mapping/{TEST_SKU}"
    
    try:
        resp = requests.get(url, timeout=10)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Total rows: {data.get('total', 0)}")
            if data.get('rows'):
                print(f"   First row: {json.dumps(data['rows'][0], indent=2)}")
            return True
        else:
            print(f"   Error: {resp.text}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False


def test_bulk_action_validation():
    """Test POST /api/ppwr/bulk-action with invalid params (should fail gracefully)"""
    print("\n3. Testing POST /api/ppwr/bulk-action validation...")
    url = f"{BASE_URL}/api/ppwr/bulk-action"
    
    # Test with missing parameters
    try:
        resp = requests.post(url, json={}, timeout=10)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 400:
            print("   ✅ Correctly rejected invalid request")
            return True
        else:
            print(f"   ⚠️ Expected 400, got {resp.status_code}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False


def test_bulk_action_empty_list():
    """Test POST /api/ppwr/bulk-action with empty material list"""
    print("\n4. Testing POST /api/ppwr/bulk-action with empty list...")
    url = f"{BASE_URL}/api/ppwr/bulk-action"
    
    payload = {
        "action": "delete",
        "sku": TEST_SKU,
        "material_ids": []
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"   Status: {resp.status_code}")
        data = resp.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Should succeed with 0 deleted
        if resp.status_code == 200:
            print("   ✅ Handled empty list gracefully")
            return True
        else:
            print(f"   ⚠️ Unexpected status code")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False


def main():
    print("="*60)
    print("PPWR Bulk Action Routes Smoke Test")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test SKU: {TEST_SKU}")
    
    results = {
        "declarations_list": test_declarations_list(),
        "mapping_table": test_mapping_table(),
        "bulk_validation": test_bulk_action_validation(),
        "bulk_empty_list": test_bulk_action_empty_list(),
    }
    
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed_count = sum(1 for p in results.values() if p)
    
    print("\n" + "="*60)
    print(f"Summary: {passed_count}/{total} tests passed")
    print("="*60)
    
    # Return exit code
    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
