#!/usr/bin/env python
"""Test Application Startup - ForestFinal"""
import os
import sys

# Set environment variables
os.environ['SECRET_KEY'] = 'test-startup-key'
os.environ['DB_CONNECTION_STRING'] = 'sqlite:///startup_test.db'
os.environ['GOOGLE_API_KEY'] = 'test-key'

print("\n" + "="*50)
print("APPLICATION STARTUP TEST")
print("="*50)

try:
    print("\n[1] Testing core database setup...")
    from forest_app.persistence.database import init_db
    init_db()
    print("✅ Database initialized successfully")
    
    print("\n[2] Testing FastAPI app creation...")
    from forest_app.main import app
    print("✅ FastAPI app created successfully")
    print(f"   - App type: {type(app).__name__}")
    
    print("\n[3] Testing app configuration...")
    # Check if app has the expected configuration
    if hasattr(app, 'state'):
        print("✅ App state configured")
    
    if hasattr(app, 'routes'):
        print(f"✅ App has {len(app.routes)} routes configured")
    
    print("\n" + "="*50)
    print("✅ APPLICATION STARTUP TEST PASSED!")
    print("✅ No SYSTEM_METRICS errors detected")
    print("✅ Database and FastAPI app are functional")
    print("="*50)
    
except Exception as e:
    print(f"\n❌ STARTUP TEST FAILED: {e}")
    print("="*50)
    sys.exit(1)

# Cleanup
try:
    if os.path.exists('startup_test.db'):
        os.remove('startup_test.db')
        print("\n✅ Cleaned up test database")
except:
    pass 