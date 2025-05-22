"""
Run pylint and pyrefly checks on the codebase.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return its exit code and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, f"Error running command: {e}"

def main():
    """Run code quality checks."""
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Run pylint
    print("\n=== Running pylint ===")
    pylint_cmd = [
        "pylint",
        "--rcfile=.pylintrc",
        "forest_app"
    ]
    pylint_code, pylint_output = run_command(pylint_cmd)
    print(pylint_output)
    
    # Run pyrefly
    print("\n=== Running pyrefly ===")
    pyrefly_cmd = [
        "pyrefly",
        "--max-line-length=100",
        "--max-complexity=10",
        "--max-args=6",
        "--max-locals=15",
        "--max-statements=50",
        "--max-branches=12",
        "forest_app"
    ]
    pyrefly_code, pyrefly_output = run_command(pyrefly_cmd)
    print(pyrefly_output)
    
    # Return overall status
    if pylint_code != 0 or pyrefly_code != 0:
        print("\nCode quality checks failed!")
        sys.exit(1)
    else:
        print("\nAll code quality checks passed!")

if __name__ == "__main__":
    main() 