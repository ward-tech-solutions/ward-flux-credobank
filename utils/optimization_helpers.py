"""
Optimization helper functions for Ward-Ops
Performance optimization utilities for query resolution and caching
"""


def get_optimal_vm_step(hours: int) -> str:
    """
    Choose optimal VictoriaMetrics query resolution based on time range

    Balances data granularity with query performance by selecting appropriate
    step intervals based on the requested time range.

    Args:
        hours: Number of hours of history requested

    Returns:
        Step interval string for VictoriaMetrics query (e.g., "5m", "15m", "1h")

    Resolution strategy:
        - 24h at 5m  = 288 points   (high detail for recent data)
        - 7d at 15m  = 672 points   (good balance of detail and performance)
        - 30d at 1h  = 720 points   (overview without overwhelming)

    Performance impact:
        - Reduces 30-day queries from 8,640 points to 720 points (12x reduction)
        - Faster query execution, smaller payloads, smoother chart rendering
        - No loss of meaningful information for long-term trends

    Example:
        >>> get_optimal_vm_step(24)
        '5m'
        >>> get_optimal_vm_step(168)  # 7 days
        '15m'
        >>> get_optimal_vm_step(720)  # 30 days
        '1h'
    """
    if hours <= 24:
        return "5m"   # 288 points - high detail for recent data
    elif hours <= 168:  # 7 days
        return "15m"  # 672 points - balanced detail
    else:  # 30+ days
        return "1h"   # 720 points - overview

    # Future enhancement: Could add more granular steps
    # elif hours <= 720:  # 30 days
    #     return "1h"
    # else:  # 90+ days
    #     return "6h"
