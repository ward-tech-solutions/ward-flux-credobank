"""
AUTO-SCALING Batch Processing
Automatically adjusts batch size based on device count
"""

import math


def calculate_optimal_batch_size(device_count: int, target_batches: int = 10) -> int:
    """
    Calculate optimal batch size to keep task count manageable

    For 875 devices: 875 / 10 = 88 → round to 100
    For 1,500 devices: 1,500 / 10 = 150
    For 3,000 devices: 3,000 / 10 = 300

    This keeps batch count at ~10 regardless of device count!
    """
    batch_size = math.ceil(device_count / target_batches)

    # Round to nearest 50 for cleaner batches
    batch_size = math.ceil(batch_size / 50) * 50

    return max(50, min(batch_size, 500))  # Between 50-500 devices per batch


# Example usage in tasks
def ping_all_devices_batched_scalable():
    """
    Auto-scaling version that adjusts batch size
    """
    db = SessionLocal()
    try:
        devices = db.query(StandaloneDevice).filter_by(enabled=True).all()

        # Auto-calculate batch size
        BATCH_SIZE = calculate_optimal_batch_size(len(devices))

        logger.info(f"Auto-scaled batch size: {BATCH_SIZE} for {len(devices)} devices")

        # Rest of batching logic...
