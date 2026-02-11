#!/usr/bin/env python3
"""
Example of using the enhanced MemoryTracker with probes.

This demonstrates how to measure timing and memory at different
stages of a USD loading operation.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.benchmarks.results import MemoryTracker


def example_basic_usage():
    """Basic usage: automatic reporting on exit."""
    print("EXAMPLE 1: Basic usage with automatic reporting\n")

    with MemoryTracker(name="Basic Test", verbose=True) as tracker:
        # Simulate some work
        data = [i for i in range(1000000)]
        tracker.probe("created_list")

        # More work
        data_doubled = [x * 2 for x in data]
        tracker.probe("doubled_list")

        # Cleanup
        del data
        tracker.probe("deleted_first_list")

    # Results are printed automatically


def example_manual_access():
    """Access probe results programmatically."""
    print("\n\nEXAMPLE 2: Manual access to probe data\n")

    with MemoryTracker(name="Manual Test", verbose=False) as tracker:
        data = [i for i in range(1000000)]
        tracker.probe("step_1")

        data2 = [x * 2 for x in data]
        tracker.probe("step_2")

    # Access results after completion
    print(f"Total probes recorded: {len(tracker.probes)}")
    for probe in tracker.probes:
        print(f"\nProbe: {probe.label}")
        print(f"  Time since start: {probe.elapsed_since_start:.4f}s")
        print(f"  Time for this step: {probe.elapsed_since_last:.4f}s")
        print(f"  Memory delta: {probe.delta_since_last / (1024 * 1024):+.2f} MB")


def example_cold_load_simulation():
    """Simulate multiple cold load runs."""
    print("\n\nEXAMPLE 3: Multiple cold runs\n")

    times = []
    memory_deltas = []

    for i in range(3):
        print(f"Run {i + 1}:")
        with MemoryTracker(name=f"Run {i + 1}", verbose=False) as tracker:
            # Simulate loading
            data = [i for i in range(500000)]
            tracker.probe("load_step_1")

            processed = [x * 2 for x in data]
            tracker.probe("load_step_2")

        if tracker.probes:
            total_time = tracker.probes[-1].elapsed_since_start
            total_mem = tracker.probes[-1].delta_since_start
            times.append(total_time)
            memory_deltas.append(total_mem)
            print(f"  {total_time:.4f}s, {total_mem / (1024 * 1024):+.2f} MB\n")

    # Summary statistics
    import statistics

    print(f"Summary across {len(times)} runs:")
    print(f"  Mean time: {statistics.mean(times):.4f}s")
    print(f"  Mean memory: {statistics.mean(memory_deltas) / (1024 * 1024):+.2f} MB")


if __name__ == "__main__":
    example_basic_usage()
    example_manual_access()
    example_cold_load_simulation()
