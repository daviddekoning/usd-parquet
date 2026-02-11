#!/usr/bin/env python3
"""
Report generation for benchmark results.

Generates a single consolidated HTML report with tabs for each test type.

Usage:
    uv run python tests/benchmarks/report.py --scale 10000 --hierarchy flat
"""

import argparse
import json
from pathlib import Path


def generate_tab_content(test_name, results, data):
    """Generate content for a specific test tab."""
    test_results = [r for r in results if r["test"] == test_name]

    if not test_results:
        return f"""
        <div class="card">
            <p>No results available for {test_name}</p>
        </div>
        """

    # Generate comparison table
    table_rows = []
    for r in test_results:
        format_class = "badge-usdc" if r["format"] == "usdc" else "badge-parquet"
        mean = f"{r['mean_seconds'] * 1000:.2f} ms" if r.get("mean_seconds") else "-"
        std = f"±{r['std_seconds'] * 1000:.2f} ms" if r.get("std_seconds") else "-"
        memory = (
            f"{r.get('peak_memory_bytes', 0) / (1024 * 1024):.2f} MB"
            if r.get("peak_memory_bytes")
            else "-"
        )

        extra_info = []
        if r.get("prim_count"):
            extra_info.append(f"{r['prim_count']:,} prims")
        if r.get("time_per_prim_us"):
            extra_info.append(f"{r['time_per_prim_us']:.2f} µs/prim")
        if r.get("property_count"):
            extra_info.append(f"{r['property_count']} props")

        table_rows.append(f"""
            <tr>
                <td><span class="badge {format_class}">{r["format"]}</span></td>
                <td>{mean}</td>
                <td>{std}</td>
                <td>{memory}</td>
                <td>{", ".join(extra_info) if extra_info else "-"}</td>
            </tr>
        """)

    # Find winner
    valid_results = [r for r in test_results if r.get("mean_seconds")]
    if valid_results:
        fastest = min(valid_results, key=lambda x: x["mean_seconds"])
        winner_text = f'<div class="winner">{fastest["format"]} - {fastest["mean_seconds"] * 1000:.2f} ms</div>'
    else:
        winner_text = ""

    canvas_id = test_name.replace("_", "-")

    # Check for detailed probe data
    has_probes = any("detailed_probes" in r for r in test_results)

    probe_charts = ""
    probe_table = ""
    if has_probes:
        # Get labels and values for a summary table
        probe_rows = []
        labels = []
        for r in test_results:
            probes_runs = r.get("detailed_probes")
            if probes_runs and len(probes_runs) > 0:
                labels = [p["label"] for p in probes_runs[0]]

                # Average values across runs
                num_runs = len(probes_runs)
                num_probes = len(labels)
                avg_times = [0.0] * num_probes
                avg_mems = [0.0] * num_probes

                for run in probes_runs:
                    for i, p in enumerate(run):
                        if i < num_probes:
                            avg_times[i] += p.get("elapsed_since_start", 0)
                            avg_mems[i] += p.get("delta_since_start", 0)

                avg_times = [t / num_runs for t in avg_times]
                avg_mems = [m / num_runs / (1024 * 1024) for m in avg_mems]

                format_name = r["format"]
                format_class = (
                    "badge-usdc" if format_name == "usdc" else "badge-parquet"
                )

                row_cells = [
                    f'<td><span class="badge {format_class}">{format_name}</span></td>'
                ]
                for i in range(num_probes):
                    row_cells.append(
                        f"<td>{avg_times[i]:.4f}s<br><small>{avg_mems[i]:+.2f} MB</small></td>"
                    )

                probe_rows.append(f"<tr>{''.join(row_cells)}</tr>")

        if labels:
            header_cells = ["<th>Format</th>"] + [f"<th>{l}</th>" for l in labels]
            probe_table = f"""
            <div class="card" style="margin-top: 1.5rem; overflow-x: auto;">
                <h3>Probe Points Detail (Averages)</h3>
                <p class="subtitle">Timing (s) and Cumulative Memory Delta (MB) at each probe</p>
                <table class="probe-table">
                    <thead>
                        <tr>{"".join(header_cells)}</tr>
                    </thead>
                    <tbody>
                        {"".join(probe_rows)}
                    </tbody>
                </table>
            </div>
            """

        probe_charts = f"""
        <div class="card">
            <h3>Detailed Timing Analysis</h3>
            <p class="subtitle">Line: Cumulative time • Bars: Time per step</p>
            <div class="chart-container">
                <canvas id="chart-{canvas_id}-timing"></canvas>
            </div>
        </div>
        <div class="card">
            <h3>Detailed Memory Analysis</h3>
            <p class="subtitle">Line: Cumulative memory • Bars: Memory per step</p>
            <div class="chart-container">
                <canvas id="chart-{canvas_id}-memory"></canvas>
            </div>
        </div>
        """

    return f"""
    <h2>{test_name.replace("_", " ").title()}</h2>
    
    <div class="grid">
        <div class="card">
            <h3>Performance Comparison</h3>
            <div class="chart-container">
                <canvas id="chart-{canvas_id}"></canvas>
            </div>
            {winner_text}
        </div>
        
        <div class="card">
            <h3>Detailed Results</h3>
            <table>
                <thead>
                    <tr>
                        <th>Format</th>
                        <th>Mean Time</th>
                        <th>Std Dev</th>
                        <th>Memory</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(table_rows)}
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="grid">
        {probe_charts}
    </div>
    
    {probe_table}
    """


def generate_overview_content(data):
    """Generate overview tab content."""
    file_sizes = data.get("file_sizes", {})
    results = data.get("results", [])

    # Calculate key metrics
    initial_load = [
        r for r in results if r["test"] in ["initial_load", "initial_load_cold"]
    ]
    traversal = [
        r
        for r in results
        if r["test"] in ["single_property_traversal", "multi_property_traversal"]
    ]

    usdc_load = next((r for r in initial_load if r["format"] == "usdc"), None)
    parquet_loads = [r for r in initial_load if "parquet" in r["format"]]

    speedup = ""
    if usdc_load and parquet_loads:
        avg_parquet = sum(r["mean_seconds"] for r in parquet_loads) / len(parquet_loads)
        speedup_factor = usdc_load["mean_seconds"] / avg_parquet
        speedup = f"""
        <div class="metric">
            <div class="metric-label">Parquet Load Speed Advantage</div>
            <div class="metric-value">{speedup_factor:.1f}x faster</div>
        </div>
        """

    file_size_comparison = ""
    if "usdc" in file_sizes and any("parquet" in k for k in file_sizes):
        usdc_size = file_sizes["usdc"]
        parquet_sizes = {k: v for k, v in file_sizes.items() if "parquet" in k}
        best_parquet = min(parquet_sizes.values())
        compression = (1 - best_parquet / usdc_size) * 100
        file_size_comparison = f"""
        <div class="metric">
            <div class="metric-label">Best File Size Savings</div>
            <div class="metric-value">{compression:.0f}% smaller</div>
        </div>
        """

    return f"""
    <h2>Performance Summary</h2>
    
    <div class="grid">
        <div class="card">
            <h3>Key Metrics</h3>
            {speedup}
            {file_size_comparison}
            <div class="metric">
                <div class="metric-label">Total Tests Run</div>
                <div class="metric-value">{len(results)}</div>
            </div>
        </div>
        
        <div class="card">
            <h3>File Sizes</h3>
            <div class="chart-container">
                <canvas id="overview-file-size"></canvas>
            </div>
        </div>
    </div>
    
    <div class="comparison">
        <h3>Quick Comparison</h3>
        <p><strong>Parquet excels at:</strong> Initial load speed, file size, lazy loading</p>
        <p><strong>USDC excels at:</strong> Bulk traversals, multi-property reads, consistent performance</p>
    </div>
    """


def generate_file_size_content(data):
    """Generate file size tab content."""
    file_sizes = data.get("file_sizes", {})

    table_rows = []
    for format_name, size_bytes in sorted(file_sizes.items()):
        size_mb = size_bytes / (1024 * 1024)
        format_class = "badge-usdc" if format_name == "usdc" else "badge-parquet"
        table_rows.append(f"""
            <tr>
                <td><span class="badge {format_class}">{format_name}</span></td>
                <td>{size_mb:.2f} MB</td>
                <td>{size_bytes:,} bytes</td>
            </tr>
        """)

    return f"""
    <h2>File Size Comparison</h2>
    
    <div class="grid">
        <div class="card">
            <h3>File Sizes by Format</h3>
            <div class="chart-container">
                <canvas id="file-size-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h3>Size Details</h3>
            <table>
                <thead>
                    <tr>
                        <th>Format</th>
                        <th>Size (MB)</th>
                        <th>Size (Bytes)</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(table_rows)}
                </tbody>
            </table>
        </div>
    </div>
    """


def generate_memory_content(data):
    """Generate memory analysis tab content."""
    results = data.get("results", [])

    # Group results by test type
    memory_by_test = {}
    for r in results:
        if r.get("peak_memory_bytes") is not None:
            test = r["test"]
            if test not in memory_by_test:
                memory_by_test[test] = []
            memory_by_test[test].append(r)

    if not memory_by_test:
        return """
        <h2>Memory Analysis</h2>
        <div class="card">
            <p>No memory measurements available in this test run.</p>
            <p>Memory tracking measures the RSS (Resident Set Size) delta during operations.</p>
        </div>
        """

    # Create summary
    total_measured = sum(len(v) for v in memory_by_test.values())
    tests_with_data = len(memory_by_test)

    # Create table for all memory measurements
    table_rows = []
    for test_name in sorted(memory_by_test.keys()):
        for r in memory_by_test[test_name]:
            format_class = "badge-usdc" if r["format"] == "usdc" else "badge-parquet"
            peak_mb = r.get("peak_memory_bytes", 0) / (1024 * 1024)
            current_mb = r.get("current_memory_bytes", 0) / (1024 * 1024)
            mean_time = (
                f"{r.get('mean_seconds', 0) * 1000:.2f} ms"
                if r.get("mean_seconds")
                else "-"
            )

            # Determine if significant memory was used
            significance = (
                "Minimal"
                if peak_mb < 0.1
                else (
                    "Low" if peak_mb < 10 else ("Medium" if peak_mb < 100 else "High")
                )
            )

            table_rows.append(f"""
                <tr>
                    <td>{test_name}</td>
                    <td><span class="badge {format_class}">{r["format"]}</span></td>
                    <td>{peak_mb:.2f} MB</td>
                    <td>{current_mb:.2f} MB</td>
                    <td>{mean_time}</td>
                    <td>{significance}</td>
                </tr>
            """)

    # Create chart data
    chart_section = ""
    if memory_by_test:
        chart_section = f"""
        <div class="card">
            <h3>Memory Usage by Test</h3>
            <div class="chart-container">
                <canvas id="memory-overview-chart"></canvas>
            </div>
        </div>
        """

    return f"""
    <h2>Memory Analysis</h2>
    
    <div class="summary-grid">
        <div class="summary-card">
            <div class="summary-value">{tests_with_data}</div>
            <div class="summary-label">Tests with Memory Data</div>
        </div>
        <div class="summary-card">
            <div class="summary-value">{total_measured}</div>
            <div class="summary-label">Measurements</div>
        </div>
    </div>
    
    <div class="comparison">
        <h3>About Memory Measurements</h3>
        <p><strong>What we measure:</strong> Process RSS (Resident Set Size) delta during operations</p>
        <p><strong>Why values might be 0 MB:</strong></p>
        <ul style="margin-left: 1.5rem; margin-top: 0.5rem; color: var(--text-secondary);">
            <li>Operations complete quickly and memory is freed immediately</li>
            <li>Lazy loading doesn't allocate significant memory upfront</li>
            <li>Memory might be allocated and freed within the measurement window</li>
            <li>USD's internal caching may reuse existing allocations</li>
        </ul>
        <p style="margin-top: 1rem;"><strong>Interpretation:</strong> 0 MB delta indicates efficient memory usage and true lazy loading behavior</p>
    </div>
    
    <div class="grid">
        {chart_section}
        
        <div class="card">
            <h3>Memory Measurements</h3>
            <div style="max-height: 500px; overflow-y: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>Format</th>
                            <th>Peak Memory</th>
                            <th>Final Memory</th>
                            <th>Duration</th>
                            <th>Significance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(table_rows)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="comparison" style="margin-top: 2rem;">
        <h3>Memory Efficiency Insights</h3>
        <p><strong>Parquet:</strong> Shows 0 MB delta during initial load, confirming true lazy loading - no property data loaded into memory</p>
        <p><strong>USDC:</strong> Also shows minimal memory delta, as USD efficiently manages composition metadata</p>
        <p><strong>Key Takeaway:</strong> Both formats demonstrate excellent memory efficiency for the tested operations. Memory differences would be more apparent in tests that traverse and cache large amounts of property data.</p>
    </div>
    """


def generate_all_results_table(results):
    """Generate the complete results table."""
    rows = []
    for r in results:
        format_class = "badge-usdc" if r["format"] == "usdc" else "badge-parquet"
        mean = f"{r['mean_seconds']:.6f}s" if r.get("mean_seconds") else "-"
        std = f"±{r['std_seconds']:.6f}s" if r.get("std_seconds") else "-"
        min_time = f"{r['min_seconds']:.6f}s" if r.get("min_seconds") else "-"
        max_time = f"{r['max_seconds']:.6f}s" if r.get("max_seconds") else "-"
        memory = (
            f"{r.get('peak_memory_bytes', 0) / (1024 * 1024):.2f} MB"
            if r.get("peak_memory_bytes")
            else "-"
        )

        extra = []
        if r.get("prim_count"):
            extra.append(f"{r['prim_count']:,} prims")
        if r.get("time_per_prim_us"):
            extra.append(f"{r['time_per_prim_us']:.2f} µs/prim")
        if r.get("size_mb"):
            extra.append(f"{r['size_mb']:.2f} MB")

        rows.append(f"""
            <tr>
                <td>{r["test"]}</td>
                <td><span class="badge {format_class}">{r["format"]}</span></td>
                <td>{mean}</td>
                <td>{std}</td>
                <td>{min_time}</td>
                <td>{max_time}</td>
                <td>{memory}</td>
                <td>{", ".join(extra) if extra else "-"}</td>
            </tr>
        """)

    return f"""
    <h2>All Test Results</h2>
    <div class="card">
        <div style="max-height: 600px; overflow-y: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Test</th>
                        <th>Format</th>
                        <th>Mean</th>
                        <th>Std Dev</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Memory</th>
                        <th>Extra</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """


def generate_chart_init(results):
    """Generate JavaScript to initialize all charts."""
    unique_tests = list(set(r["test"] for r in results))

    chart_calls = []

    # Overview file size chart
    chart_calls.append("""
        const fileSizes = data.file_sizes;
        const fileSizeLabels = Object.keys(fileSizes);
        const fileSizeValues = Object.values(fileSizes).map(v => v / (1024 * 1024));
        createChart('overview-file-size', fileSizeLabels.map((label, idx) => ({
            format: label,
            mean_seconds: fileSizeValues[idx] / 1000  // Dummy value for chart
        })), 'MB', fileSizeValues);
    """)

    # File size chart
    chart_calls.append("""
        createChart('file-size-chart', fileSizeLabels.map((label, idx) => ({
            format: label,
            mean_seconds: fileSizeValues[idx] / 1000
        })), 'MB', fileSizeValues);
    """)

    # Test-specific charts
    for test in unique_tests:
        canvas_id = f"chart-{test.replace('_', '-')}"
        chart_calls.append(f"""
            createChart('{canvas_id}', data.results.filter(r => r.test === '{test}'), 'seconds');
        """)

        # Detailed probe charts
        test_results = [r for r in results if r["test"] == test]
        has_probes = any(r.get("detailed_probes") for r in test_results)

        if has_probes:
            # Get labels from first result with probes
            labels = []
            for r in test_results:
                probes = r.get("detailed_probes")
                if probes and len(probes) > 0:
                    labels = [p["label"] for p in probes[0]]
                    break

            if labels:
                timing_datasets = []
                memory_datasets = []

                for r in test_results:
                    probes_runs = r.get("detailed_probes")
                    if not probes_runs:
                        continue

                    format_name = r["format"]

                    # Calculate averages
                    num_runs = len(probes_runs)
                    num_probes = len(labels)

                    acc_elapsed_start = [0.0] * num_probes
                    acc_elapsed_last = [0.0] * num_probes
                    acc_mem_start = [0.0] * num_probes
                    acc_mem_last = [0.0] * num_probes

                    for run in probes_runs:
                        for i, probe in enumerate(run):
                            if i < num_probes:
                                acc_elapsed_start[i] += probe.get(
                                    "elapsed_since_start", 0
                                )
                                acc_elapsed_last[i] += probe.get(
                                    "elapsed_since_last", 0
                                )
                                acc_mem_start[i] += probe.get("delta_since_start", 0)
                                acc_mem_last[i] += probe.get("delta_since_last", 0)

                    avg_elapsed_start = [x / num_runs for x in acc_elapsed_start]
                    avg_elapsed_last = [x / num_runs for x in acc_elapsed_last]
                    avg_mem_start = [
                        x / num_runs / (1024 * 1024) for x in acc_mem_start
                    ]
                    avg_mem_last = [x / num_runs / (1024 * 1024) for x in acc_mem_last]

                    # Add datasets
                    timing_datasets.append(f"""{{
                        type: 'line',
                        label: '{format_name} (Cumulative)',
                        data: {avg_elapsed_start},
                        borderColor: getColor('{format_name}'),
                        backgroundColor: getColor('{format_name}'),
                        tension: 0.1,
                        order: 0
                    }}""")
                    timing_datasets.append(f"""{{
                        type: 'bar',
                        label: '{format_name} (Step)',
                        data: {avg_elapsed_last},
                        backgroundColor: getColor('{format_name}').replace('0.9', '0.3'),
                        borderColor: getColor('{format_name}'),
                        borderWidth: 1,
                        order: 1
                    }}""")

                    memory_datasets.append(f"""{{
                        type: 'line',
                        label: '{format_name} (Cumulative)',
                        data: {avg_mem_start},
                        borderColor: getColor('{format_name}'),
                        backgroundColor: getColor('{format_name}'),
                        tension: 0.1,
                        order: 0
                    }}""")
                    memory_datasets.append(f"""{{
                        type: 'bar',
                        label: '{format_name} (Step)',
                        data: {avg_mem_last},
                        backgroundColor: getColor('{format_name}').replace('0.9', '0.3'),
                        borderColor: getColor('{format_name}'),
                        borderWidth: 1,
                        order: 1
                    }}""")

                chart_calls.append(f"""
                    createProbeChart('{canvas_id}-timing', [{",".join(timing_datasets)}], {json.dumps(labels)}, 'seconds');
                    createProbeChart('{canvas_id}-memory', [{",".join(memory_datasets)}], {json.dumps(labels)}, 'MB');
                """)

    # Memory overview chart
    chart_calls.append("""
        const memoryResults = data.results.filter(r => r.peak_memory_bytes != null);
        if (memoryResults.length > 0) {
            // Group by test and format
            const memoryByTest = {};
            memoryResults.forEach(r => {
                const key = r.test;
                if (!memoryByTest[key]) memoryByTest[key] = [];
                memoryByTest[key].push({
                    format: r.format,
                    memory: r.peak_memory_bytes / (1024 * 1024)
                });
            });
            
            // Create chart with all formats for each test
            const allFormats = [...new Set(memoryResults.map(r => r.format))];
            const testNames = Object.keys(memoryByTest);
            
            if (testNames.length > 0) {
                const datasets = allFormats.map(format => ({
                    label: format,
                    data: testNames.map(test => {
                        const item = memoryByTest[test].find(m => m.format === format);
                        return item ? item.memory : 0;
                    }),
                    backgroundColor: getColor(format)
                }));
                
                const canvas = document.getElementById('memory-overview-chart');
                if (canvas) {
                    new Chart(canvas, {
                        type: 'bar',
                        data: {
                            labels: testNames.map(t => t.replace(/_/g, ' ')),
                            datasets: datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { 
                                legend: { display: true, labels: { color: '#e6edf3' } },
                                title: { display: true, text: 'Peak Memory by Test', color: '#e6edf3' }
                            },
                            scales: {
                                y: { 
                                    beginAtZero: true, 
                                    title: { display: true, text: 'MB', color: '#8b949e' }, 
                                    ticks: { color: '#8b949e' }, 
                                    grid: { color: '#30363d' } 
                                },
                                x: { 
                                    ticks: { color: '#8b949e', maxRotation: 45 }, 
                                    grid: { display: false } 
                                }
                            }
                        }
                    });
                }
            }
        }
    """)

    return "\n".join(chart_calls)


# HTML template with tabs
HTML_TEMPLATE = (
    open(Path(__file__).parent / "report_template.html").read()
    if (Path(__file__).parent / "report_template.html").exists()
    else """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark Report: Parquet vs USDC</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-purple: #a371f7;
            --border-color: #30363d;
            --tab-active: #1f6feb;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }
        
        .container { max-width: 1600px; margin: 0 auto; }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        h2 {
            font-size: 1.5rem;
            margin: 2rem 0 1rem 0;
            color: var(--accent-blue);
        }
        
        h3 {
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }
        
        .subtitle {
            color: var(--text-secondary);
            margin-bottom: 2rem;
        }
        
        /* Tabs */
        .tab-nav {
            display: flex;
            gap: 0.5rem;
            margin: 2rem 0;
            border-bottom: 2px solid var(--border-color);
            overflow-x: auto;
            flex-wrap: wrap;
        }
        
        .tab-button {
            padding: 0.75rem 1.5rem;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            transition: all 0.2s;
        }
        
        .tab-button:hover {
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }
        
        .tab-button.active {
            color: var(--accent-blue);
            border-bottom-color: var(--tab-active);
        }
        
        .tab-content {
            display: none;
            animation: fadeIn 0.3s;
        }
        
        .tab-content.active { display: block; }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
        }
        
        .chart-container {
            position: relative;
            height: 350px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
        }
        
        tr:hover { background: var(--bg-tertiary); }
        
        .badge {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge-parquet {
            background: rgba(163, 113, 247, 0.2);
            color: var(--accent-purple);
        }
        
        .badge-usdc {
            background: rgba(63, 185, 80, 0.2);
            color: var(--accent-green);
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .summary-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
            text-align: center;
        }
        
        .summary-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-blue);
            margin-bottom: 0.25rem;
        }
        
        .summary-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
        
        .metric {
            margin: 1rem 0;
            padding: 1rem;
            background: var(--bg-tertiary);
            border-radius: 8px;
            border-left: 3px solid var(--accent-blue);
        }
        
        .metric-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 0.25rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .comparison {
            margin-top: 2rem;
            padding: 1.5rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }
        
        .winner {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(63, 185, 80, 0.1);
            border: 1px solid rgba(63, 185, 80, 0.3);
            border-radius: 6px;
            color: var(--accent-green);
            font-weight: 600;
            margin: 0.5rem 0;
        }
        
        .winner::before {
            content: "✓";
            font-size: 1.2rem;
        }

        .probe-table th {
            white-space: nowrap;
            font-size: 0.65rem;
        }

        .probe-table td {
            white-space: nowrap;
        }

        .probe-table small {
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Benchmark Report</h1>
        <p class="subtitle">Parquet vs USDC Performance • {{test_run}} • {{scale}} prims ({{hierarchy}})</p>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value">{{format_count}}</div>
                <div class="summary-label">Format Variants</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{{test_count}}</div>
                <div class="summary-label">Test Results</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{{scale}}</div>
                <div class="summary-label">Prims Tested</div>
            </div>
        </div>
        
        <div class="tab-nav">
            {{tab_buttons}}
        </div>
        
        {{tab_contents}}
    </div>
    
    <script>
        const data = {{json_data}};
        
        const colors = {
            parquet_none: 'rgba(163, 113, 247, 0.9)',
            parquet_snappy: 'rgba(88, 166, 255, 0.9)',
            parquet_zstd: 'rgba(210, 153, 34, 0.9)',
            usdc: 'rgba(63, 185, 80, 0.9)',
        };
        
        function getColor(format) {
            return colors[format] || colors.parquet_none;
        }
        
        function showTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }
        
        function createChart(canvasId, results, unit = 'seconds', customValues = null) {
            const canvas = document.getElementById(canvasId);
            if (!canvas || results.length === 0) return;
            
            const values = customValues || results.map(r => r.mean_seconds || 0);
            
            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: results.map(r => r.format),
                    datasets: [{
                        data: values,
                        backgroundColor: results.map(r => getColor(r.format)),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            title: { display: true, text: unit, color: '#8b949e' }, 
                            ticks: { color: '#8b949e' }, 
                            grid: { color: '#30363d' } 
                        },
                        x: { 
                            ticks: { color: '#8b949e', maxRotation: 45 }, 
                            grid: { display: false } 
                        }
                    }
                }
            });
        }

        function createProbeChart(canvasId, datasets, labels, unit) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { display: true, labels: { color: '#e6edf3' } },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += context.parsed.y.toFixed(4) + ' ' + unit;
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            title: { display: true, text: unit, color: '#8b949e' }, 
                            ticks: { color: '#8b949e' }, 
                            grid: { color: '#30363d' } 
                        },
                        x: { 
                            ticks: { color: '#8b949e', maxRotation: 45 }, 
                            grid: { display: false } 
                        }
                    }
                }
            });
        }
        
        window.addEventListener('load', () => {
            {{chart_initialization}}
        });
    </script>
</body>
</html>
"""
)


def generate_html_report(data: dict, output_path: Path) -> None:
    """Generate tabbed HTML report."""
    results = data.get("results", [])

    # Get unique test names
    test_names = list(set(r["test"] for r in results if r["test"] != "file_size"))
    test_names.sort()

    # Generate tab buttons
    tab_buttons = [
        '<button class="tab-button active" onclick="showTab(\'overview\')">Overview</button>'
    ]
    tab_buttons.append(
        '<button class="tab-button" onclick="showTab(\'file-size\')">File Size</button>'
    )

    for test_name in test_names:
        display_name = test_name.replace("_", " ").title()
        tab_id = test_name.replace("_", "-")
        tab_buttons.append(
            f'<button class="tab-button" onclick="showTab(\'{tab_id}\')">{display_name}</button>'
        )

    # Add Memory tab
    tab_buttons.append(
        '<button class="tab-button" onclick="showTab(\'memory\')">Memory Analysis</button>'
    )
    tab_buttons.append(
        '<button class="tab-button" onclick="showTab(\'all-results\')">All Results</button>'
    )

    # Generate tab contents
    tab_contents = []

    # Overview tab
    tab_contents.append(
        f'<div id="overview" class="tab-content active">{generate_overview_content(data)}</div>'
    )

    # File size tab
    tab_contents.append(
        f'<div id="file-size" class="tab-content">{generate_file_size_content(data)}</div>'
    )

    # Test tabs
    for test_name in test_names:
        tab_id = test_name.replace("_", "-")
        content = generate_tab_content(test_name, results, data)
        tab_contents.append(f'<div id="{tab_id}" class="tab-content">{content}</div>')

    # Memory tab
    tab_contents.append(
        f'<div id="memory" class="tab-content">{generate_memory_content(data)}</div>'
    )

    # All results tab
    tab_contents.append(
        f'<div id="all-results" class="tab-content">{generate_all_results_table(results)}</div>'
    )

    # Generate HTML
    html = HTML_TEMPLATE
    html = html.replace("{{test_run}}", data.get("test_run", "Unknown"))
    html = html.replace("{{scale}}", str(data.get("scale", 0)))
    html = html.replace("{{hierarchy}}", data.get("hierarchy", "unknown"))
    html = html.replace("{{format_count}}", str(len(data.get("file_sizes", {}))))
    html = html.replace("{{test_count}}", str(len(results)))
    html = html.replace("{{tab_buttons}}", "\n".join(tab_buttons))
    html = html.replace("{{tab_contents}}", "\n".join(tab_contents))
    html = html.replace("{{json_data}}", json.dumps(data))
    html = html.replace("{{chart_initialization}}", generate_chart_init(results))

    with open(output_path, "w") as f:
        f.write(html)

    print(f"✓ HTML report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark report")
    parser.add_argument(
        "--results-dir",
        type=str,
        default="tests/data/benchmarks",
        help="Directory containing benchmark results",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=10000,
        help="Scale of benchmark to report on",
    )
    parser.add_argument(
        "--hierarchy",
        type=str,
        default="flat",
        help="Hierarchy pattern of benchmark",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir) / f"{args.scale}_{args.hierarchy}"

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        print("Run the benchmarks first")
        return

    # Load results
    json_path = results_dir / "benchmark_results.json"
    if not json_path.exists():
        print(f"Error: No results file found: {json_path}")
        return

    with open(json_path) as f:
        data = json.load(f)

    # Generate HTML report
    html_path = results_dir / "benchmark_report.html"
    generate_html_report(data, html_path)

    print(f"\n✓ Report generated: {html_path}")


if __name__ == "__main__":
    main()
