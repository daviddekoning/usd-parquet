"""
Test Cases 5 & 6: Multiple Property Tests

- Test 5: Multiple property retrieval (single prim)
- Test 6: Multiple property traversal (all prims)
"""

import multiprocessing
from pathlib import Path

import pytest
from pxr import Usd

from .conftest import TEST_PROPERTIES
from .results import BenchmarkResult, BenchmarkTimer, MemoryTracker, TimingResult, MemoryResult


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


def _run_multi_property_traversal_iteration(base_scene_path_str, prop_path_str, format_name, run_index, expected_prims, result_queue):
    """Run a multi-property traversal iteration in a separate process."""
    try:
        from .conftest import TEST_PROPERTIES
        prim_count = 0
        
        with MemoryTracker(name=f"{format_name} Run {run_index}", verbose=False) as tracker:
            tracker.probe("start")
            
            stage = Usd.Stage.CreateInMemory()
            root = stage.GetRootLayer()
            root.subLayerPaths.append(base_scene_path_str)
            root.subLayerPaths.append(prop_path_str)
            _ = stage.GetPseudoRoot()
            tracker.probe("stage_loaded")
            
            chunk_size = max(1, expected_prims // 10)
            
            # Traverse and read
            count = 0
            for prim in stage.Traverse():
                has_props = False
                for attr_name in TEST_PROPERTIES:
                    attr = prim.GetAttribute(attr_name)
                    if attr:
                        value = attr.Get()
                        if value is not None:
                            has_props = True
                
                if has_props:
                    prim_count += 1
                
                count += 1
                if count % chunk_size == 0:
                    percent = min(100, int(count / expected_prims * 100))
                    tracker.probe(f"traversal_{percent}pct")
            
            # Ensure final probe if not covered by chunking
            if count > 0 and count % chunk_size != 0:
                tracker.probe("finished")
            elif count > 0:
                tracker.probe("finished")
                
        result_queue.put((tracker.probes, prim_count))
        
    except Exception as e:
        result_queue.put(e)


class TestMultiplePropertyRetrieval:
    """Multiple property retrieval tests (Test Case 5)."""

    @pytest.mark.skip(reason="Benchmark not yet reliable")
    def test_multi_property_single_prim(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure time to read 6 properties from one prim."""
        format_name, prop_path = property_file
        collector = result_collector

        prim_index = benchmark_scale // 2
        if benchmark_hierarchy == "flat":
            prim_path = f"/World/Prim_{prim_index}"
        else:
            prim_path = f"/World/Zone_0/Level_5/Room_0/Component_0"

        def setup():
            """Create fresh stage with empty cache before each timing run."""
            return _open_stage_with_sublayer(base_scene_path, prop_path)

        def read_multiple_properties(stage):
            """Read 6 properties from the target prim."""
            prim = stage.GetPrimAtPath(prim_path)
            values = []
            for attr_name in TEST_PROPERTIES:
                attr = prim.GetAttribute(attr_name)
                if attr.IsValid():
                    values.append(attr.Get())
            return values

        timer = BenchmarkTimer(runs=50, warmup=5)
        timing = timer.measure(read_multiple_properties, setup=setup)

        collector.add_result(
            BenchmarkResult(
                test_name="multi_property_single_prim",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                extra={
                    "property_count": len(TEST_PROPERTIES),
                    "time_per_property_us": (timing.mean_seconds / len(TEST_PROPERTIES))
                    * 1_000_000,
                },
            )
        )

        print(f"\n{format_name} multi-property single prim:")
        print(
            f"  Total: {timing.mean_seconds * 1000:.4f}ms for {len(TEST_PROPERTIES)} properties"
        )
        print(
            f"  Per property: {(timing.mean_seconds / len(TEST_PROPERTIES)) * 1_000_000:.2f} µs"
        )


class TestMultiplePropertyTraversal:
    """Multiple property traversal tests (Test Case 6)."""

    @pytest.mark.skip(reason="Benchmark not yet reliable")
    def test_multi_property_traversal(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure time to read 6 properties from every prim."""
        format_name, prop_path = property_file
        collector = result_collector
        
        num_runs = 5
        times = []
        memory_peaks = []
        all_probe_data = []
        last_prim_count = 0
        
        print(f"\n{'='*70}")
        print(f"{format_name} multi property traversal ({num_runs} runs)")
        print(f"{'='*70}\n")
        
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}:")
            
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=_run_multi_property_traversal_iteration,
                args=(str(base_scene_path), str(prop_path), format_name, i+1, benchmark_scale, queue)
            )
            p.start()
            
            try:
                # Wait for result (timeout 120s)
                result = queue.get(timeout=120)
                p.join()
                
                if isinstance(result, Exception):
                    raise result
                
                probes, prim_count = result
                last_prim_count = prim_count
                
                if probes:
                    total_time = probes[-1].elapsed_since_start
                    total_memory = probes[-1].delta_since_start
                    
                    times.append(total_time)
                    memory_peaks.append(total_memory)
                    
                    run_probes = []
                    for probe in probes:
                        run_probes.append({
                            "label": probe.label,
                            "elapsed_since_start": probe.elapsed_since_start,
                            "elapsed_since_last": probe.elapsed_since_last,
                            "total_memory_bytes": probe.total_memory_bytes,
                            "delta_since_start": probe.delta_since_start,
                            "delta_since_last": probe.delta_since_last
                        })
                    all_probe_data.append(run_probes)
                    
                    if i < num_runs - 1:
                        print(f"  Total: {total_time:.4f}s, {total_memory / (1024*1024):+.2f} MB\n")
            
            except Exception as e:
                if p.is_alive():
                    p.terminate()
                raise e

        timing = TimingResult.from_times(times)
        avg_peak = sum(memory_peaks) / len(memory_peaks) if memory_peaks else 0
        final_memory = MemoryResult(current_bytes=int(avg_peak), peak_bytes=int(avg_peak))

        total_accesses = last_prim_count * len(TEST_PROPERTIES)

        collector.add_result(
            BenchmarkResult(
                test_name="multi_property_traversal",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                memory=final_memory,
                extra={
                    "prim_count": last_prim_count,
                    "property_count": len(TEST_PROPERTIES),
                    "total_accesses": total_accesses,
                    "time_per_access_us": (timing.mean_seconds / total_accesses)
                    * 1_000_000
                    if total_accesses > 0
                    else 0,
                    "detailed_probes": all_probe_data
                },
            )
        )

        print(f"\n{format_name} multi-property traversal:")
        print(
            f"  Total: {timing.mean_seconds:.4f}s for {last_prim_count} prims × {len(TEST_PROPERTIES)} properties"
        )
        print(
            f"  Per access: {(timing.mean_seconds / total_accesses) * 1_000_000:.2f} µs"
            if total_accesses > 0
            else "  Per access: N/A"
        )
        if final_memory:
            print(f"  Memory: {final_memory.peak_bytes / (1024 * 1024):.2f} MB peak")
