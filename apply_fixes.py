"""
Apply code duplication fixes across the codebase.

This script updates files with duplicated code to use the centralized utilities.
"""

import os
import re
import sys


def main():
    """Apply fixes to all identified files with duplicate code."""

    # List of files to update
    files_to_update = [
        # Router files
        "forest_app/routers/core.py",
        "forest_app/routers/onboarding.py",
        "forest_app/routers/goals.py",
        "forest_app/routers/snapshots.py",
        # Module files
        "forest_app/modules/emotional_integrity.py",
        "forest_app/modules/financial_readiness.py",
        "forest_app/modules/offering_reward.py",
        "forest_app/modules/relational.py",
        "forest_app/modules/practical_consequence.py",
    ]

    # Ensure all files exist
    missing_files = [f for f in files_to_update if not os.path.exists(f)]
    if missing_files:
        print(f"Error: The following files are missing: {missing_files}")
        sys.exit(1)

    # Apply fixes to each file
    for file_path in files_to_update:
        print(f"Processing {file_path}...")
        apply_fixes_to_file(file_path)

    print("\nAll fixes have been applied!")


def apply_fixes_to_file(file_path):
    """Apply fixes to a specific file."""

    # Read the file content
    with open(file_path, "r") as f:
        content = f.read()

    # Apply all fixes
    content = replace_llm_dummy_classes(content)
    content = replace_constants_placeholder(content)
    content = replace_error_handling(content)
    content = replace_timestamp_handling(content)
    content = replace_clamp01_function(content)
    content = replace_category_thresholds(content)

    # Write the updated content
    with open(file_path, "w") as f:
        f.write(content)


def replace_llm_dummy_classes(content):
    """Replace LLM dummy class definitions with imports from utils."""
    # Match LLM dummy class definitions
    llm_pattern = re.compile(
        r"""try:.*?from\s+forest_app\.integrations.*?llm.*?
    except\s+ImportError.*?as\s+e:.*?
    logger\..*?"Failed\s+to\s+import\s+LLM.*?".*?
    llm_import_ok\s*=\s*False

    .*?class\s+LLMClient:.*?pass.*?

    class\s+LLMError.*?pass.*?

    class\s+LLMValidationError.*?pass.*?

    class\s+LLMConfigurationError.*?pass.*?

    class\s+LLMConnectionError.*?pass""",
        re.DOTALL | re.MULTILINE,
    )

    # Replacement
    llm_replacement = """try:
    from forest_app.integrations import llm
    from forest_app.integrations.llm import LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError
    llm_import_ok = True
    logger.info("Successfully imported LLM integration components.")
except ImportError as e:
    llm_import_ok, LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError = \\
        forest_app.utils.handle_llm_import_error(e)"""

    # Add the import if it's not already there
    if "forest_app.utils" not in content:
        content = "import forest_app.utils\n" + content

    # Apply the replacement
    return re.sub(llm_pattern, llm_replacement, content)


def replace_constants_placeholder(content):
    """Replace constants placeholder with import from utils."""
    # Match constants placeholder
    constants_pattern = re.compile(
        r"""try:\s*
    from\s+forest_app\.config\s+import\s+constants.*?
except\s+ImportError:.*?

    class\s+ConstantsPlaceholder:.*?
        MAX_CODENAME_LENGTH.*?
        MIN_PASSWORD_LENGTH.*?
        ONBOARDING_STATUS.*?
        .*?
        SEED_STATUS.*?
        .*?DEFAULT_RESONANCE_THEME.*?

    constants\s*=\s*ConstantsPlaceholder\(\)""",
        re.DOTALL | re.MULTILINE,
    )

    # Replacement
    constants_replacement = """# Import constants with fallback to placeholder if needed
from forest_app.utils import get_constants_module
constants = get_constants_module()"""

    # Apply the replacement
    return re.sub(constants_pattern, constants_replacement, content)


def replace_error_handling(content):
    """Replace error handling code with imports from utils."""
    # Match error handling pattern
    error_pattern = re.compile(
        r"""except\s+\(SQLAlchemyError,\s*ValueError\)\s+as\s+db_val_err:.*?
        detail\s*=\s*\(\s*
            "DB\s+error\.".*?
            if\s+isinstance\(db_val_err,\s+SQLAlchemyError\).*?
            else\s+f"Invalid\s+data:.*?
        \).*?
        status_code\s*=\s*\(.*?
            status\.HTTP_503_SERVICE_UNAVAILABLE.*?
            if\s+isinstance\(db_val_err,\s+SQLAlchemyError\).*?
            else\s+status\.HTTP_400_BAD_REQUEST.*?
        \).*?
        raise\s+HTTPException\(status_code=status_code,\s+detail=detail\)""",
        re.DOTALL | re.MULTILINE,
    )

    # Replacement
    error_replacement = """except (SQLAlchemyError, ValueError) as db_val_err:
        # Handle database and validation errors consistently
        forest_app.utils.handle_db_errors(db_val_err)"""

    # Apply the replacement
    content = re.sub(error_pattern, error_replacement, content)

    # Look for appropriate functions to decorate
    if "forest_app.utils.handle_db_exceptions" not in content:
        # Add import if not present
        if "from forest_app.utils import handle_db_exceptions" not in content:
            if "from forest_app.utils import" in content:
                content = re.sub(
                    r"from forest_app.utils import (.*?)\n",
                    r"from forest_app.utils import \1, handle_db_exceptions\n",
                    content,
                )
            else:
                content = (
                    "from forest_app.utils import handle_db_exceptions\n" + content
                )

    return content


def replace_timestamp_handling(content):
    """Replace timestamp handling code with import from utils."""
    # Match timestamp validation pattern
    timestamp_pattern = re.compile(
        r"""loaded_ts\s*=\s*data\.get\("last_update"\).*?
        if\s+isinstance\(loaded_ts,\s+str\):.*?
            # Could add ISO format validation here.*?
            self\.last_update\s*=\s*loaded_ts.*?
        elif\s+loaded_ts\s+is\s+not\s+None:.*?
            logger\.warning\(.*?
                "Invalid\s+'last_update'\s+type\s+in\s+data:.*?
                type\(loaded_ts\),.*?
            \).*?
            self\.last_update\s*=\s*None.*?  # Reset if invalid.*?
        else:.*?
            self\.last_update\s*=\s*None.*?  # Reset if missing""",
        re.DOTALL | re.MULTILINE,
    )

    # Replacement
    timestamp_replacement = """        # Validate and set timestamp using utility function
        self.last_update = forest_app.utils.validate_dict_timestamp(data, "last_update")"""

    # Apply the replacement
    return re.sub(timestamp_pattern, timestamp_replacement, content)


def replace_clamp01_function(content):
    """Replace clamp01 function with import from utils."""
    # Match clamp01 function
    clamp_pattern = re.compile(
        r"""def\s+_clamp01\(x:\s+float\)\s*->\s*float:.*?
    \"\"\"Clamp\s+a\s+float\s+to\s+the\s+0\.0.?1\.0\s+range\.\"\"\"\s*
    .*?return\s+max\(0\.0,\s+min\(float\(x\),\s+1\.0\)\).*?""",
        re.DOTALL | re.MULTILINE,
    )

    # Check if the file contains the clamp01 function
    if re.search(clamp_pattern, content):
        # Add the import if needed
        if "forest_app.utils.clamp01" not in content:
            if "from forest_app.utils import" in content:
                content = re.sub(
                    r"from forest_app.utils import (.*?)\n",
                    r"from forest_app.utils import \1, clamp01\n",
                    content,
                )
            else:
                content = "from forest_app.utils import clamp01\n" + content

        # Replace all occurrences of _clamp01 with clamp01
        content = re.sub(r"_clamp01\(", "clamp01(", content)

        # Replace the function definition
        content = re.sub(clamp_pattern, "", content)

    return content


def replace_category_thresholds(content):
    """Replace category threshold determination with import from utils."""
    # Match category threshold function pattern
    category_pattern = re.compile(
        r"""def\s+get_category_from_thresholds\(.*?\):.*?
        if\s+not\s+valid_thresholds:.*?
            return\s+"Unknown".*?
        sorted_thresholds\s*=\s*sorted\(.*?
            valid_thresholds\.items\(\),\s+key=lambda\s+item:\s+item\[1\],\s+reverse=True.*?
        \).*?
        for\s+label,\s+thresh\s+in\s+sorted_thresholds:.*?
            if\s+float_value\s*>=\s*thresh:.*?
                return\s+str\(label\).*?
        return\s+str\(sorted_thresholds\[-1\]\[0\]\)\s+if\s+sorted_thresholds\s+else\s+"Dormant".*?
    except\s+\(ValueError,\s+TypeError\)\s+as\s+e:""",
        re.DOTALL | re.MULTILINE,
    )

    # Check if the file contains the category threshold function
    if re.search(category_pattern, content):
        # Add the import if needed
        if "forest_app.utils.get_category_from_thresholds" not in content:
            if "from forest_app.utils import" in content:
                content = re.sub(
                    r"from forest_app.utils import (.*?)\n",
                    r"from forest_app.utils import \1, get_category_from_thresholds\n",
                    content,
                )
            else:
                content = (
                    "from forest_app.utils import get_category_from_thresholds\n"
                    + content
                )

    return content


if __name__ == "__main__":
    main()
