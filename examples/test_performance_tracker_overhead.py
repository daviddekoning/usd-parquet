#!/usr/bin/env python3
"""
Test to verify that probe overhead is correctly excluded from timing.
"""

import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.benchmarks.results import PerformanceTracker


def test_overhead_exclusion():
    """Verify that probe overhead doesn't accumulate in elapsed_since_start."""
    print("Testing overhead exclusion...\n")

    with PerformanceTracker(name="Overhead Test", verbose=False) as tracker:
        # First work segment: sleep for 0.1 seconds
        time.sleep(0.1)
        tracker.probe("after_sleep_1")

        # Second work segment: sleep for 0.1 seconds
        time.sleep(0.1)
        tracker.probe("after_sleep_2")

        # Third work segment: sleep for 0.1 seconds
        time.sleep(0.1)
        tracker.probe("after_sleep_3")

    print("Results:")
    print(f"{'Probe':<20} {'Elapsed from Start':<20} {'Delta from Last':<20}")
    print("-" * 60)

    for probe in tracker.probes:
        print(
            f"{probe.label:<20} {probe.elapsed_since_start:>18.4f}s "
            f"{probe.elapsed_since_last:>18.4f}s"
        )

    print("\nAnalysis:")
    # Each sleep should be ~0.1s
    # elapsed_since_start should be cumulative work time (0.1, 0.2, 0.3)
    # elapsed_since_last should be ~0.1 for each

    expected_times = [0.1, 0.2, 0.3]
    for i, (probe, expected) in enumerate(zip(tracker.probes, expected_times)):
        actual = probe.elapsed_since_start
        error = abs(actual - expected)
        status = "✓ PASS" if error < 0.02 else "✗ FAIL"  # 20ms tolerance
        print(
            f"  Probe {i + 1} elapsed_since_start: {actual:.4f}s "
            f"(expected ~{expected:.1f}s) {status}"
        )

    # Check that deltas are consistent
    print("\nDelta consistency:")
    for i, probe in enumerate(tracker.probes):
        delta = probe.elapsed_since_last
        status = "✓ PASS" if 0.08 < delta < 0.12 else "✗ FAIL"  # Allow some variance
        print(f"  Probe {i + 1} delta: {delta:.4f}s (expected ~0.1s) {status}")

    # The total overhead should be tracked
    print(
        f"\nTotal probe overhead tracked: {tracker._total_probe_overhead * 1000:.2f}ms"
    )
    print(f"Number of probes: {len(tracker.probes)}")
    print(
        f"Average overhead per probe: {tracker._total_probe_overhead / len(tracker.probes) * 1000:.2f}ms"
    )


if __name__ == "__main__":
    test_overhead_exclusion()
