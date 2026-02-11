#!/usr/bin/env python3
"""
Demonstration of probe overhead correction in MemoryTracker.

This example shows how the tracker correctly excludes probe measurement
overhead from timing calculations, ensuring accurate elapsed times even
with many probes.
"""

import time
from pathlib import Path
import sys

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.benchmarks.results import MemoryTracker


def demo_with_explanation():
    """Demonstrate overhead correction with clear explanation."""
    
    print("="*70)
    print("MemoryTracker Overhead Correction Demo")
    print("="*70)
    print("\nThis test performs 5 work steps, each taking exactly 0.1 seconds.")
    print("Multiple probes are used to measure progress.\n")
    print("Without overhead correction, elapsed_since_start would drift")
    print("due to accumulated probe measurement time.")
    print("\nWith overhead correction (implemented), the times should be:")
    print("  - Each step: ~0.1s")
    print("  - Cumulative: 0.1s, 0.2s, 0.3s, 0.4s, 0.5s")
    print("\n" + "="*70)
    
    with MemoryTracker(name="Overhead Correction Demo", verbose=False) as tracker:
        # Work step 1
        time.sleep(0.1)
        tracker.probe("step_1")
        
        # Work step 2
        time.sleep(0.1)
        tracker.probe("step_2")
        
        # Work step 3
        time.sleep(0.1)
        tracker.probe("step_3")
        
        # Work step 4
        time.sleep(0.1)
        tracker.probe("step_4")
        
        # Work step 5
        time.sleep(0.1)
        tracker.probe("step_5")
    
    # Display results
    print("\nMeasured Results:")
    print(f"{'Step':<10} {'Cumulative Time':>16} {'Step Time':>12} {'Expected':>12} {'Status':>8}")
    print("-"*70)
    
    expected_cumulative = [0.1, 0.2, 0.3, 0.4, 0.5]
    all_pass = True
    
    for i, (probe, expected) in enumerate(zip(tracker.probes, expected_cumulative), 1):
        error = abs(probe.elapsed_since_start - expected)
        status = "✓ PASS" if error < 0.02 else "✗ FAIL"
        if status == "✗ FAIL":
            all_pass = False
        
        print(f"{probe.label:<10} {probe.elapsed_since_start:>14.4f}s "
              f"{probe.elapsed_since_last:>10.4f}s "
              f"{expected:>10.1f}s "
              f"{status:>8}")
    
    print("-"*70)
    print(f"\nTotal probe overhead excluded: {tracker._total_probe_overhead * 1000:.3f}ms")
    print(f"Average per probe: {tracker._total_probe_overhead / len(tracker.probes) * 1000:.3f}ms")
    
    if all_pass:
        print("\n✓ All timing measurements are accurate (overhead correctly excluded)")
    else:
        print("\n✗ Some measurements failed (overhead may not be fully excluded)")
    
    print("\n" + "="*70)
    print("Conclusion:")
    print("The elapsed_since_start values correctly reflect actual work time,")
    print("not including the (tiny) overhead of checking memory at each probe.")
    print("="*70 + "\n")


if __name__ == "__main__":
    demo_with_explanation()
