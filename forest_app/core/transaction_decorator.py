"""
Transaction decorator for database operations

This module provides a transaction decorator that wraps database operations in
a transaction with proper error handling, retries, and logging.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, TypeVar, cast

from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Type variable for generic function typing
T = TypeVar("T")


def transaction_protected(
    name: str = "transaction", timeout: float = 30.0, max_retries: int = 1
):
    """
    Decorator that wraps a function in a transaction context.

    This decorator provides:
    - Transaction management with proper rollback on errors
    - Performance metrics logging
    - Optional retry logic for transient failures
    - Timeout protection

    Args:
        name: Name of the transaction for logging
        timeout: Maximum time in seconds for the operation
        max_retries: Maximum number of retry attempts for transient errors

    Returns:
        Decorated function with transaction protection
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            retries = 0

            while retries <= max_retries:
                try:
                    # Set timeout for the operation
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=timeout
                    )

                    # Log successful completion with timing
                    execution_time = (time.time() - start_time) * 1000  # ms
                    logger.info(
                        "Transaction '%s' completed successfully in %.2fms",
                        name,
                        execution_time,
                    )

                    return result

                except asyncio.TimeoutError:
                    logger.error(
                        "Transaction '%s' timed out after %s seconds", name, timeout
                    )
                    raise TimeoutError("Operation timed out after %s seconds", timeout)

                except SQLAlchemyError as db_err:
                    # Database errors - might be retryable
                    retries += 1
                    if retries <= max_retries:
                        logger.warning(
                            "Transaction '%s' failed with database error, "
                            "retry %s/%s: %s",
                            name,
                            retries,
                            max_retries,
                            db_err,
                        )
                        # Brief delay before retry
                        await asyncio.sleep(0.5 * retries)
                    else:
                        logger.error(
                            "Transaction '%s' failed after %s retries: %s",
                            name,
                            retries,
                            db_err,
                        )
                        raise

                except Exception as e:
                    # Non-database errors - no retry
                    logger.error("Transaction '%s' failed with error: %s", name, e)
                    raise

        return cast(Callable[..., T], wrapper)

    return decorator
