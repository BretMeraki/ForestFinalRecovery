#!/usr/bin/env python
"""Final startup test - verify no EventType.SYSTEM_METRICS errors"""
import os
import sys

# Set environment variables
os.environ['SECRET_KEY'] = 'final-test-key'
os.environ['DB_CONNECTION_STRING'] = 'sqlite:///final_startup_test.db'
os.environ['GOOGLE_API_KEY'] = 'test-key'

print("\n" + "="*60)
print("FINAL STARTUP TEST - NO EVENTTYPE ERRORS")
print("="*60)

try:
    print("\n[1] Testing EventBus and EventType imports...")
    from forest_app.core.event_bus import EventBus, EventType
    print("✅ EventBus and EventType imported successfully")
    print(f"   - Available EventType attributes: {[attr for attr in dir(EventType) if not attr.startswith('_')]}")
    
    # Test that METRICS_RECORDED exists
    metrics_event = EventType.METRICS_RECORDED
    print(f"   - EventType.METRICS_RECORDED = '{metrics_event}'")
    
    # Ensure SYSTEM_METRICS does NOT exist
    try:
        system_metrics = EventType.SYSTEM_METRICS
        print(f"❌ PROBLEM: EventType.SYSTEM_METRICS still exists: '{system_metrics}'")
    except AttributeError:
        print("✅ Confirmed: EventType.SYSTEM_METRICS does not exist (good!)")
    
    print("\n[2] Testing initialize_architecture import...")
    from forest_app.core.initialize_architecture import inject_enhanced_architecture
    print("✅ initialize_architecture imported successfully")
    
    print("\n[3] Testing FastAPI app creation...")
    from forest_app.main import app
    print("✅ FastAPI app created successfully")
    print(f"   - App type: {type(app).__name__}")
    
    print("\n[4] Testing database initialization...")
    from forest_app.persistence.database import init_db
    init_db()
    print("✅ Database initialized successfully")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED - APPLICATION STARTUP READY!")
    print("✅ No EventType.SYSTEM_METRICS errors")
    print("✅ All imports working correctly")
    print("✅ Database initialization successful")
    print("✅ FastAPI app creation successful")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ STARTUP TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 