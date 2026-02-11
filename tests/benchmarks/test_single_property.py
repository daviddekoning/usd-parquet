"""
Test Cases 3 & 4: Single Property Tests

- Test 3: Single property retrieval (cold + warm repetition)
- Test 4: Single property traversal
"""

import multiprocessing
from pathlib import Path
import pytest
from pxr import Usd


from .results import BenchmarkResult, BenchmarkTimer, MemoryTracker, TimingResult, MemoryResult
from pxr.Usd import Prim


def _run_single_property_iteration(base_scene_path_str, prop_path_str, prim_path, format_name, run_index, result_queue):
    """Run a single iteration in a separate process."""
    try:        
        with MemoryTracker(name=f"{format_name} Run {run_index}", verbose=False) as tracker:
            tracker.probe("start")
            
            # 1. Base layer load
            stage = Usd.Stage.CreateInMemory()
            root = stage.GetRootLayer()
            root.subLayerPaths.append(base_scene_path_str)
            tracker.probe("base_layer_loaded")
            
            # 2. Sublayer composition
            root.subLayerPaths.append(prop_path_str)
            tracker.probe("sublayer_composition")
            
            # 3. Read property (Cold)
            prim = stage.GetPrimAtPath(prim_path)
            attr = prim.GetAttribute("payload")
            value = attr.Get()
            tracker.probe("property_read_cold")
            
            # 4. Read property (Warm - 50 iterations)
            for _ in range(50):
                value = attr.Get()
            tracker.probe("property_read_warm_50x")
        
        result_queue.put(tracker.probes)
    except Exception as e:
        result_queue.put(e)


def _run_single_property_traversal_iteration(base_scene_path_str, prop_path_str, format_name, run_index, expected_prims, result_queue):
    """Run a single traversal iteration in a separate process."""
    try:
        # We need to capture prim_count to return it
        prim_count = 0
        print(f"  Expected prims with property: {expected_prims}", flush=True)
        
        with MemoryTracker(name=f"{format_name} Run {run_index}", verbose=False) as tracker:
            tracker.probe("start")
            
            stage = Usd.Stage.Open(base_scene_path_str)
            root = stage.GetRootLayer()
            tracker.probe("base_layer_loaded")

            root.subLayerPaths.append(prop_path_str)
            tracker.probe("stage_loaded")
            
            chunk_size = max(1, expected_prims // 10)
            
            # Traverse and read
            total_visited = 0
            count = 0
            for prim in stage.Traverse():
                attr = prim.GetAttribute("payload")
                if attr:
                    _ = attr.Get()
                    count += 1
                
                total_visited += 1
                if total_visited % chunk_size == 0:
                    tracker.probe(f"traversal_{count}")
                        
            if total_visited == 0:
                raise RuntimeError("No prims were visited during traversal, which is unexpected.")

            # Ensure final probe if not covered by chunking
            tracker.probe("finished")
                
        result_queue.put((tracker.probes, count))
        
    except Exception as e:
        result_queue.put(e)


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


class TestSinglePropertyRetrieval:
    """Single property retrieval tests (Test Case 3)."""

    @pytest.mark.skip(reason="Covered by traverse test")
    def test_single_property_cold(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure cold access to a single property (first access after load)."""
        format_name, prop_path = property_file
        collector = result_collector

        # Pick a prim in the middle of the dataset
        prim_index = benchmark_scale // 2
        if benchmark_hierarchy == "flat":
            prim_path = f"/World/Prim_{prim_index}"
        else:
            prim_path = f"/World/Zone_0/Level_5/Room_0/Component_0"
            
        num_runs = 5
        times = []
        memory_peaks = []
        all_probe_data = []
        
        print(f"\n{'='*70}")
        print(f"{format_name} single property cold ({num_runs} runs)")
        print(f"{'='*70}\n")

        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}:")
            
            # Use multiprocessing to isolate memory and run clean
            queue = multiprocessing.Queue()
            
            p = multiprocessing.Process(
                target=_run_single_property_iteration,
                args=(str(base_scene_path), str(prop_path), prim_path, format_name, i+1, queue)
            )
            p.start()
            
            try:
                # Wait for result (timeout 60s)
                probes = queue.get(timeout=60)
                p.join()
                
                if isinstance(probes, Exception):
                    raise probes
                
                if probes:
                    # Calculate results from probes
                    total_time = probes[-1].elapsed_since_start
                    total_memory = probes[-1].delta_since_start
                    
                    times.append(total_time)
                    memory_peaks.append(total_memory)
                    
                    # Convert probes to dictionary format for storage
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

        collector.add_result(
            BenchmarkResult(
                test_name="single_property_cold",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                memory=final_memory,
                extra={"detailed_probes": all_probe_data}
            )
        )

        print(f"\n{format_name} single property cold: {timing.mean_seconds:.6f}s")


class TestSinglePropertyTraversal:
    """Single property traversal test (Test Case 4)."""

    def test_single_property_traversal(
        self,
        property_file: tuple[str, Path],
        base_scene_path: Path,
        benchmark_scale: int,
        benchmark_hierarchy: str,
        result_collector,
    ):
        """Measure time to read same property from every prim."""
        format_name, prop_path = property_file
        collector = result_collector
        
        num_runs = 5
        times = []
        memory_peaks = []
        all_probe_data = []
        last_prim_count = 0
        
        print(f"\n{'='*70}")
        print(f"{format_name} single property traversal ({num_runs} runs)")
        print(f"{'='*70}\n")
        
        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}:")
            
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=_run_single_property_traversal_iteration,
                args=(str(base_scene_path), str(prop_path), format_name, i+1, benchmark_scale, queue)
            )
            p.start()
            
            try:
                # Wait for result (timeout 120s as traversal can be slow)
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

        collector.add_result(
            BenchmarkResult(
                test_name="single_property_traversal",
                format_name=format_name,
                scale=benchmark_scale,
                hierarchy=benchmark_hierarchy,
                timing=timing,
                memory=final_memory,
                extra={
                    "prim_count": last_prim_count,
                    "time_per_prim_us": (timing.mean_seconds / last_prim_count) * 1_000_000
                    if last_prim_count > 0
                    else 0,
                    "detailed_probes": all_probe_data
                },
            )
        )

        if last_prim_count != benchmark_scale:
            raise ValueError(f"Expected to read property from {benchmark_scale} prims, but got {last_prim_count}")

        print(f"\n{format_name} single property traversal:")
        print(f"  Total: {timing.mean_seconds:.4f}s for {last_prim_count} prims")
        print(
            f"  Per prim: {(timing.mean_seconds / last_prim_count) * 1_000_000:.2f} µs"
            if last_prim_count > 0
            else "  Per prim: N/A"
        )
        if final_memory:
            print(f"  Memory: {final_memory.peak_bytes / (1024 * 1024):.2f} MB peak")
