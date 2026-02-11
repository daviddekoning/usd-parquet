# HTML Report Update - Tabbed Interface

## Changes Made

Updated `tests/benchmarks/report.py` to generate a **single HTML file with tabs** instead of showing all tests in one scrolling page.

## New Structure

### Tab Navigation
The report now includes 11 tabs:

1. **Overview** - Summary metrics and key comparisons
2. **File Size** - File size comparison across formats
3. **Initial Load** - Sublayer load performance
4. **Single Property Cold** - First access after load
5. **Single Property Warm** - Cached access
6. **Single Property Traversal** - Read one property from all prims
7. **Multi Property Single Prim** - Read 6 properties from one prim
8. **Multi Property Traversal** - Read 6 properties from all prims
9. **Random Access Traversal** - Randomized access pattern
10. **Sequential Access** - Sequential access pattern
11. **All Results** - Complete results table

### Features

#### Each Test Tab Contains:
- **Performance Chart** - Bar chart comparing all formats
- **Winner Badge** - Highlights the fastest format
- **Detailed Table** - Mean time, std dev, memory, and extra info
- **Consistent Styling** - Dark theme with color-coded badges

#### Overview Tab Shows:
- Key metrics (load speed advantage, file size savings)
- File size comparison chart
- Quick comparison summary

#### Interactive Elements:
- Smooth tab transitions with fade-in animation
- Color-coded badges (purple for Parquet, green for USDC)
- Hover effects on tables and buttons
- Responsive grid layout

## Color Scheme

Each format has its own color:
- **Parquet (none)**: Purple `rgba(163, 113, 247, 0.9)`
- **Parquet (snappy)**: Blue `rgba(88, 166, 255, 0.9)`
- **Parquet (zstd)**: Orange `rgba(210, 153, 34, 0.9)`
- **USDC**: Green `rgba(63, 185, 80, 0.9)`

## Usage

### Generate Report

```bash
# For 10K prims, flat hierarchy
uv run python tests/benchmarks/report.py --scale 10000 --hierarchy flat

# For other configurations
uv run python tests/benchmarks/report.py --scale 1000 --hierarchy deep
```

### View Report

Open the generated file in a browser:
```bash
open tests/data/benchmarks/10000_flat/benchmark_report.html
```

## Benefits

### Before (Scrolling Page)
- All tests in one long page
- Required scrolling through all sections
- Hard to compare specific tests
- All charts loaded at once (slower)

### After (Tabbed Interface)
- ✅ **Organized by test type**
- ✅ **Quick navigation** between tests
- ✅ **Focused view** - one test at a time
- ✅ **Better performance** - charts load on demand
- ✅ **Mobile friendly** - tab overflow scrolls horizontally
- ✅ **Overview tab** for quick insights

## Example Output

The report includes:

### Overview Tab
```
Performance Summary
- Parquet Load Speed Advantage: 18.3x faster
- Best File Size Savings: 55% smaller
- Total Tests Run: 33
```

### Each Test Tab
```
[Chart comparing all formats]

✓ parquet_zstd - 47.69 ms

Detailed Results
Format          Mean Time    Std Dev      Memory
parquet_none    46.65 ms     ±0.12 ms     0.00 MB
parquet_snappy  46.67 ms     ±0.18 ms     0.00 MB
parquet_zstd    46.71 ms     ±0.39 ms     0.00 MB
usdc            855.71 ms    ±18.61 ms    0.00 MB
```

## File Location

Reports are generated in the same directory as the results:
```
tests/data/benchmarks/
└── 10000_flat/
    ├── benchmark_results.json    # Raw data
    └── benchmark_report.html     # Tabbed visual report ← NEW
```

## Technical Implementation

- **Pure HTML/CSS/JavaScript** - No build step required
- **Chart.js** via CDN for visualizations
- **Vanilla JS** for tab switching
- **CSS Grid** for responsive layout
- **Dark theme** matching GitHub's design system

## Backward Compatibility

- JSON results format unchanged
- Same command-line interface
- Old single-page HTML replaced with tabbed version
- All existing functionality preserved
