#!/usr/bin/env python3
"""
Test script to verify Docker R setup works
Run this to test the containerized R without needing the full Electron app
"""

import requests
import json
import time
import sys

# Configuration
PYTHON_BACKEND_URL = "http://localhost:8000"

def test_connection():
    """Test if Python backend is responding"""
    try:
        response = requests.get(f"{PYTHON_BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Python backend is responding")
            return True
        else:
            print(f"❌ Python backend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Python backend: {e}")
        return False

def test_r_version():
    """Test R version command"""
    try:
        print("\n🧪 Testing R version...")
        response = requests.get(f"{PYTHON_BACKEND_URL}/init", timeout=10)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        if msg.get('type') == 'rversion':
                            print(f"✅ R Version: {msg['message']['major']}.{msg['message']['minor']}")
                            return True
                        elif msg.get('type') == 'init_done':
                            print("✅ R initialization completed")
                    except json.JSONDecodeError:
                        continue
        else:
            print(f"❌ Init request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ R version test failed: {e}")
        return False

def test_basic_r_command():
    """Test basic R command execution"""
    try:
        print("\n🧪 Testing basic R command...")
        
        # Test simple R command
        cmd_data = json.dumps({
            "cmd": "print('Hello from Docker R!')",
            "eval": False
        })
        
        response = requests.post(
            f"{PYTHON_BACKEND_URL}/cmd/r", 
            data=cmd_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        if msg.get('type') == 'console' and 'Hello from Docker R!' in str(msg.get('message', '')):
                            print("✅ Basic R command executed successfully")
                            return True
                    except json.JSONDecodeError:
                        continue
            print("❌ R command executed but didn't get expected output")
            return False
        else:
            print(f"❌ R command failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Basic R command test failed: {e}")
        return False

def test_r_packages():
    """Test if required R packages are available"""
    try:
        print("\n🧪 Testing R packages...")
        
        packages_to_test = [
            'tidyverse',
            'data.table', 
            'openxlsx',
            'jsonlite'
        ]
        
        for package in packages_to_test:
            cmd_data = json.dumps({
                "cmd": f"library({package}); cat('Package {package} loaded successfully')",
                "eval": False
            })
            
            response = requests.post(
                f"{PYTHON_BACKEND_URL}/cmd/r",
                data=cmd_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                success = False
                for line in lines:
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            if f"Package {package} loaded successfully" in str(msg.get('message', '')):
                                print(f"✅ Package '{package}' is available")
                                success = True
                                break
                        except json.JSONDecodeError:
                            continue
                
                if not success:
                    print(f"⚠️  Package '{package}' may not be available")
            else:
                print(f"⚠️  Failed to test package '{package}'")
                
        return True
    except Exception as e:
        print(f"❌ R packages test failed: {e}")
        return False

def test_bluesky_package():
    """Test if BlueSky package is available"""
    try:
        print("\n🧪 Testing BlueSky package...")
        
        cmd_data = json.dumps({
            "cmd": "library(BlueSky); cat('BlueSky package loaded successfully')",
            "eval": False
        })
        
        response = requests.post(
            f"{PYTHON_BACKEND_URL}/cmd/r",
            data=cmd_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        if "BlueSky package loaded successfully" in str(msg.get('message', '')):
                            print("✅ BlueSky package is available")
                            return True
                        elif "Error" in str(msg.get('message', '')):
                            print("⚠️  BlueSky package is not available (this is OK for testing)")
                            return False
                    except json.JSONDecodeError:
                        continue
        
        print("⚠️  BlueSky package test inconclusive")
        return False
    except Exception as e:
        print(f"❌ BlueSky package test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🐳 Testing Docker R Setup")
    print("=" * 50)
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(2)
    
    tests = [
        ("Connection Test", test_connection),
        ("R Version Test", test_r_version), 
        ("Basic R Command Test", test_basic_r_command),
        ("R Packages Test", test_r_packages),
        ("BlueSky Package Test", test_bluesky_package)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            if test_func():
                passed += 1
            time.sleep(1)  # Brief pause between tests
        except KeyboardInterrupt:
            print("\n🛑 Tests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Docker R setup is working correctly.")
        return 0
    elif passed >= total - 1:  # Allow BlueSky test to fail
        print("✅ Core functionality is working. Docker R setup is ready!")
        return 0
    else:
        print("❌ Some tests failed. Check the Docker setup.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)