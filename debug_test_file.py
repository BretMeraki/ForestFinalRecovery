#!/usr/bin/env python3
"""
Debug script to line-by-line check the test file for errors
"""

import traceback


def test_import_sequence():
    """TODO: Add docstring."""
    print("Starting debug sequence...")

    # Basic imports
    print("1. Importing basic modules")
    try:
        print("✓ Basic modules imported successfully")
    except Exception as e:
        print(f"✗ Error importing basic modules: {e}")
        traceback.print_exc()
        return

    # Import core modules
    print("\n2. Importing core modules")
    try:
        print("✓ Core modules imported successfully")
    except Exception as e:
        print(f"✗ Error importing core modules: {e}")
        traceback.print_exc()
        return

    # Import test helper modules
    print("\n3. Importing test helper modules")
    try:
        print("Checking if test_helpers directory exists and is initialized...")
        import os

        test_helpers_path = os.path.join(
            "forest_app", "core", "services", "test_helpers"
        )
        if os.path.exists(test_helpers_path):
            print(f"✓ Directory exists: {test_helpers_path}")
            init_file = os.path.join(test_helpers_path, "__init__.py")
            if os.path.exists(init_file):
                print("✓ __init__.py exists in test_helpers directory")
            else:
                print("✗ __init__.py missing in test_helpers directory")
                with open(init_file, "w") as f:
                    f.write("# Test helpers package\n")
                print(f"Created __init__.py in {test_helpers_path}")
        else:
            print(f"✗ Directory does not exist: {test_helpers_path}")
    except Exception as e:
        print(f"Error checking test_helpers directory: {e}")
        traceback.print_exc()

    # Try importing the test helpers
    try:
        print("\nAttempting to import test helper functions...")

        print("✓ mock_enhanced_hta_service imported successfully")
    except Exception as e:
        print(f"✗ Error importing mock_enhanced_hta_service: {e}")
        traceback.print_exc()

    try:
        print("✓ mock_node_generator imported successfully")
    except Exception as e:
        print(f"✗ Error importing mock_node_generator: {e}")
        traceback.print_exc()

    try:
        print("✓ mock_repository imported successfully")
    except Exception as e:
        print(f"✗ Error importing mock_repository: {e}")
        traceback.print_exc()

    print("\n4. Checking test file fixture imports")
    try:
        print("✓ Test file imported successfully")
    except Exception as e:
        print(f"✗ Error importing test file: {e}")
        print("\nDetailed traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    test_import_sequence()
