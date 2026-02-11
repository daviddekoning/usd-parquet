"""
Test Case 7: Random Access Pattern

Stress test cache behavior with worst-case access pattern (shuffled prim order).
"""

import random
from pathlib import Path

import pytest
from pxr import Usd

from .results import BenchmarkResult, BenchmarkTimer, get_collector


def _open_stage_with_sublayer(base_path: Path, prop_path: Path) -> Usd.Stage:
    """Helper to open a stage with property sublayer.

    Creates a fresh in-memory stage that sublayers both the base scene and
    property file, ensuring no cached state from previous runs.
    """
    # Create a new in-memory stage to avoid USD stage caching
    stage = Usd.Stage.CreateInMemory()
    root = stage.GetRootLayer()
    # Add base scene first, then property file (property file overrides)
    root.subLayerPaths.append(str(base_path))
    root.subLayerPaths.append(str(prop_path))
    return stage


class TestRandomAccess:
    """Random access pattern tests (Test Case 7)."""

    @pytest.mark.skip(reason="Benchmark not yet reliable")
    def test_random_access_traversal(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure traversal with randomized prim order (worst case for caching)."""
        format_name, prop_path = property_file
        collector = result_collector

        # Pre-collect prim paths from initial stage (not timed)
        initial_stage = _open_stage_with_sublayer(base_scene_path, prop_path)
        prim_paths = [str(prim.GetPath()) for prim in initial_stage.TraverseAll()]
        del initial_stage  # Release stage to free any cache

        # Shuffle for random access pattern
        random.seed(42)  # Reproducible randomness
        shuffled_paths = prim_paths.copy()
        random.shuffle(shuffled_paths)

        def setup():
            """Create fresh stage with empty cache before each timing run."""
            return _open_stage_with_sublayer(base_scene_path, prop_path)

        def random_access(stage):
            """Access prims in random order."""
            count = 0
            for path in shuffled_paths:
                prim = stage.GetPrimAtPath(path)
                attr = prim.GetAttribute("temperature")
                if attr:
                    value = attr.Get()
                    if value is not None:
                        count += 1
            return count

        timer = BenchmarkTimer(runs=3, warmup=1)
        timing = timer.measure(random_access, setup=setup)

        prim_count = len(prim_paths)

        collector.add_result(
            BenchmarkResult(
                test_name="random_access_traversal",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                extra={
                    "prim_count": prim_count,
                    "time_per_prim_us": (timing.mean_seconds / prim_count) * 1_000_000
                    if prim_count > 0
                    else 0,
                },
            )
        )

        print(f"\n{format_name} random access traversal:")
        print(f"  Total: {timing.mean_seconds:.4f}s for {prim_count} prims")
        print(
            f"  Per prim: {(timing.mean_seconds / prim_count) * 1_000_000:.2f} µs"
            if prim_count > 0
            else "  Per prim: N/A"
        )

    @pytest.mark.skip(reason="Benchmark not yet reliable")
    def test_sequential_vs_random_comparison(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Compare sequential vs random access patterns."""
        format_name, prop_path = property_file
        collector = result_collector

        # Pre-collect prim paths from initial stage (not timed)
        initial_stage = _open_stage_with_sublayer(base_scene_path, prop_path)
        prim_paths = [str(prim.GetPath()) for prim in initial_stage.TraverseAll()]
        del initial_stage  # Release stage to free any cache

        # Random access order
        random.seed(42)
        shuffled_paths = prim_paths.copy()
        random.shuffle(shuffled_paths)

        def setup():
            """Create fresh stage with empty cache before each timing run."""
            return _open_stage_with_sublayer(base_scene_path, prop_path)

        def sequential_access(stage):
            """Access prims in sequential order."""
            for path in prim_paths:
                prim = stage.GetPrimAtPath(path)
                attr = prim.GetAttribute("temperature")
                if attr:
                    _ = attr.Get()

        def random_access_pattern(stage):
            """Access prims in random order."""
            for path in shuffled_paths:
                prim = stage.GetPrimAtPath(path)
                attr = prim.GetAttribute("temperature")
                if attr:
                    _ = attr.Get()

        timer = BenchmarkTimer(runs=3, warmup=1)

        seq_timing = timer.measure(sequential_access, setup=setup)
        rand_timing = timer.measure(random_access_pattern, setup=setup)

        # Record sequential result
        collector.add_result(
            BenchmarkResult(
                test_name="sequential_access",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=seq_timing,
                extra={"prim_count": len(prim_paths)},
            )
        )

        # Calculate slowdown factor
        slowdown = (
            rand_timing.mean_seconds / seq_timing.mean_seconds
            if seq_timing.mean_seconds > 0
            else 0
        )

        print(f"\n{format_name} sequential vs random:")
        print(f"  Sequential: {seq_timing.mean_seconds:.4f}s")
        print(f"  Random: {rand_timing.mean_seconds:.4f}s")
        print(f"  Slowdown factor: {slowdown:.2f}x")
