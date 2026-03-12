#!/usr/bin/env python3
"""Quick test of dashboard APIs"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("✓ Testing health endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=2)
        if r.status_code == 200:
            print(f"  ✅ Health OK: {r.json()['status']}")
            return True
    except:
        print("  ⚠️  Health check failed (server might not be running)")
        return False

def test_deployments():
    print("\n✓ Testing deployments endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/api/deployments", timeout=2)
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Found {data.get('count', 0)} deployments")
            for dep in data.get('deployments', [])[:3]:
                print(f"    - {dep['id']}: {dep['status']}")
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_dashboard():
    print("\n✓ Testing dashboard endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/api/dashboard", timeout=2)
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Dashboard loaded")
            print(f"    - Deployments: {data.get('stats', {}).get('total', 0)}")
            print(f"    - Online: {data.get('stats', {}).get('online', 0)}")
            print(f"    - Critical events: {len(data.get('critical_events', []))}")
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running quick API tests...")
    print("=" * 50)
    
    all_ok = all([
        test_health(),
        test_deployments(),
        test_dashboard()
    ])
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed - make sure server is running")
        print("   Start with: cd /Users/alexren/.openclaw/workspace/mission_control_master && bash start.sh")
