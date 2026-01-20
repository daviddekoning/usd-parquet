# Performance Test Specification: Parquet vs USDC

This document defines a comprehensive test harness for comparing property read performance between Parquet and USDC files in OpenUSD.

## Test Objectives

Compare the performance characteristics of storing prim properties in:
- **Parquet files** (using the custom `parquetFormat` plugin with lazy block-aware caching)
- **USDC files** (native OpenUSD binary format)

All tests use `Usd.Stage` with composition, where the property file is a sublayer over a base scene.

---

## Test Setup

### Base Scene

A USDA file defining the prim hierarchy without properties:

```usda
#usda 1.0
def Xform "World" {
    # Prims will be defined programmatically at multiple scales
}
```

### Property Files

Two files with **identical content** but different formats:
- `properties.parquet` – Properties stored in Parquet format
- `properties.usdc` – Properties stored in native USDC format

Both files define properties as `over` specifiers to compose onto the base scene.

### Property Schema

| Column/Attribute | Type | Description |
|------------------|------|-------------|
| `path` | string | Prim path (Parquet only, used for indexing) |
| `cost` | double | Material cost |
| `carbon_A1` | double | Embodied carbon (A1 stage) |
| `carbon_A2` | double | Embodied carbon (A2 stage) |
| `carbon_A3` | double | Embodied carbon (A3 stage) |
| `carbon_A4` | double | Embodied carbon (A4 stage) |
| `carbon_A5` | double | Embodied carbon (A5 stage) |
| `weight` | double | Component weight (kg) |
| `temperature` | double | Operating temperature (°C) |
| `pressure` | double | Operating pressure (Pa) |
| `velocity_x` | double | Velocity X component |
| `velocity_y` | double | Velocity Y component |
| `velocity_z` | double | Velocity Z component |
| `stress` | double | Material stress (MPa) |
| `strain` | double | Material strain |
| `efficiency` | double | Component efficiency (0-1) |
| `lifespan` | int | Expected lifespan (years) |
| `is_active` | bool | Whether component is active |
| `supplier_id` | string | Supplier identifier |
| `material_code` | string | Material classification code |
| `install_date` | string | Installation date (ISO 8601) |

**Total: 20 properties** (14 double, 1 int, 1 bool, 4 string)

### Parquet Configuration Parameters

The following parameters should be varied across test runs:

**Compression Algorithms**:
- `NONE` – No compression (baseline)
- `SNAPPY` – Fast compression, moderate ratio
- `ZSTD` – Higher compression ratio, slower

**Row Group Sizes**:
- `100` rows per group (many small groups)
- `1,000` rows per group (default)
- `10,000` rows per group (fewer large groups)

### Test Scales

Tests should be run at multiple prim counts to understand scaling behavior:

| Scale | Prim Count | Use Case |
|-------|------------|----------|
| Small | 1,000 | Quick iteration |
| Medium | 10,000 | Typical building model |
| Large | 100,000 | Large industrial facility |
| XL | 1,000,000 | City-scale or stress test |

### Hierarchy Patterns

Two hierarchy patterns to test:
- **Flat**: `/World/Prim_0`, `/World/Prim_1`, ...
- **Deep**: `/World/Zone_0/Level_0/Room_0/Component_0`, ...

---

## Measurements

### Timing

- Use Python's `time.perf_counter()` for high-resolution timing
- Run each test **10 times** minimum
- Report: **mean**, **standard deviation**, **min**, **max**
- Include a **warmup run** (discarded) before measurement runs

### Memory

- Use `tracemalloc` to measure memory delta during operations
- Report: **peak memory** and **current memory** after operation

---

## Test Cases

### 1. File Size Comparison

**Purpose**: Compare storage efficiency across formats and compression settings.

**Metrics**:
- File size in bytes for each configuration
- Compression ratio vs uncompressed Parquet

**Matrix**: Measure for all combinations of compression × row group size.

---

### 2. Initial Stage Load

**Purpose**: Measure time to open a stage with the property sublayer.

**Measurement**:
```python
start = time.perf_counter()
stage = Usd.Stage.Open(base_layer)
stage.GetRootLayer().subLayerPaths.append(property_layer)
_ = stage.GetPseudoRoot()  # Force composition
elapsed = time.perf_counter() - start
```

**Report**: Load time in seconds, memory delta.

---

### 3. Single Property Retrieval

**Purpose**: Measure time to access one property on one prim.

**Variants**:
- **Cold**: First access after stage load
- **Warm**: Repeated access to same property
- **Random prim**: Access random prim (tests cache misses)
- **Sequential prim**: Access prims in path order (tests cache hits)

---

### 4. Single Property Traversal

**Purpose**: Time to read the same property from every prim in the scene.

**Report**: Total time, time per prim.

---

### 5. Multiple Property Retrieval (Single Prim)

**Purpose**: Time to read 6 properties from one prim.

**Properties**: `cost`, `carbon_A1`, `weight`, `temperature`, `is_active`, `supplier_id`

---

### 6. Multiple Property Traversal

**Purpose**: Time to read 6 properties from every prim.

---

### 7. Random Access Pattern

**Purpose**: Stress test cache behavior with worst-case access pattern (shuffled prim order).

---

### 8. Memory After Load

**Purpose**: Measure memory footprint after various operations.

**Variants**: After initial load, after single access, after full traversal.

---

## Output Format

### JSON Results

Results written to `benchmark_results.json`:

```json
{
  "test_run": "2026-01-20T12:00:00",
  "scale": 10000,
  "hierarchy": "flat",
  "file_sizes": {
    "usdc": 1234567,
    "parquet_none_100": 2345678,
    "parquet_none_1000": 2234567,
    "parquet_snappy_1000": 1567890,
    "parquet_zstd_1000": 1234567
  },
  "results": [
    {
      "test": "initial_load",
      "format": "parquet_snappy_1000",
      "mean_seconds": 0.234,
      "std_seconds": 0.012,
      "min_seconds": 0.218,
      "max_seconds": 0.256,
      "memory_bytes": 12345678
    }
  ]
}
```

### HTML Visualization

Generate an `benchmark_report.html` file with interactive charts:

- **File size comparison**: Bar chart comparing all formats/configurations
- **Load time comparison**: Grouped bar chart by scale
- **Traversal performance**: Line chart showing time vs prim count
- **Memory usage**: Bar chart comparing memory footprint
- **Summary table**: All metrics in a sortable table

Use a lightweight charting library (e.g., Chart.js via CDN) for visualization.

---

## Test Harness Structure

```
tests/
├── benchmarks/
│   ├── conftest.py              # Pytest fixtures for test data
│   ├── generate_test_data.py    # Create parquet + usdc files
│   ├── test_file_size.py        # Test case 1
│   ├── test_initial_load.py     # Test case 2
│   ├── test_single_property.py  # Test cases 3, 4
│   ├── test_multi_property.py   # Test cases 5, 6
│   ├── test_random_access.py    # Test case 7
│   ├── test_memory.py           # Test case 8
│   ├── results.py               # Result collection utilities
│   └── report.py                # Generate JSON + HTML report
└── data/
    └── benchmarks/              # Generated test files
```

---

## Success Criteria

The test harness is complete when:
1. ✅ All 8 test cases are implemented
2. ✅ Tests run at multiple scales (1K, 10K, 100K, 1M prims)
3. ✅ Parquet tested with 3 compression algorithms × 3 row group sizes
4. ✅ Results exported to JSON with file sizes included
5. ✅ HTML report generated with interactive visualizations
6. ✅ Both Parquet and USDC formats tested with identical data
7. ✅ Statistical measures (mean, std, min, max) reported
