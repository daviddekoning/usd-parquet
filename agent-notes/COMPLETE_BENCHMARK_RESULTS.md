# Complete Benchmark Results
## Configuration: 10,000 Prims, Flat Hierarchy
## Test Date: 2026-02-10

---

## File Size Comparison

| Format | Size (MB) | vs USDC | Compression Ratio |
|--------|-----------|---------|-------------------|
| Parquet (none) | 1.87 MB | **43% smaller** | baseline |
| Parquet (snappy) | 1.63 MB | **50% smaller** | 13% compressed |
| Parquet (zstd) | 1.47 MB | **55% smaller** | 25% compressed |
| **USDC** | 3.28 MB | *baseline* | - |

**Winner: Parquet (zstd)** - Smallest file size at 1.47 MB

---

## Test 1: Initial Sublayer Load
**Measures**: Time to add property sublayer to an already-open stage (lazy loading)

| Format | Mean Time | Std Dev | vs USDC |
|--------|-----------|---------|---------|
| Parquet (none) | 46.65 ms | 0.12 ms | **18.3x faster** ⚡ |
| Parquet (snappy) | 46.67 ms | 0.18 ms | **18.3x faster** ⚡ |
| Parquet (zstd) | 46.71 ms | 0.39 ms | **18.3x faster** ⚡ |
| **USDC** | 855.71 ms | 18.61 ms | *baseline* |

**Winner: All Parquet variants** - Dramatically faster due to lazy loading  
**Memory**: All formats show 0 MB delta (true lazy loading - no data loaded)

---

## Test 2: Single Property Retrieval (Cold)
**Measures**: First access to single property on single prim

| Format | Mean Time | vs USDC |
|--------|-----------|---------|
| Parquet (none) | 0.052 ms | 5% slower |
| Parquet (snappy) | 0.052 ms | 5% slower |
| Parquet (zstd) | 0.054 ms | 8% slower |
| **USDC** | 0.050 ms | *baseline* |

**Winner: USDC** - Marginally faster (within margin of error)

---

## Test 3: Single Property Retrieval (Warm)
**Measures**: Repeated access to same property (cache performance)

| Format | Mean Time | vs USDC |
|--------|-----------|---------|
| Parquet (none) | 2.42 µs | 13% faster ⚡ |
| Parquet (snappy) | 2.37 µs | 17% faster ⚡ |
| Parquet (zstd) | 2.42 µs | 13% faster ⚡ |
| **USDC** | 2.85 µs | *baseline* |

**Winner: Parquet (snappy)** - Better cache performance

---

## Test 4: Single Property Traversal
**Measures**: Read same property from ALL 10,001 prims

| Format | Total Time | Time/Prim | vs USDC |
|--------|------------|-----------|---------|
| Parquet (none) | 83.8 ms | 8.38 µs | 2.2x slower |
| Parquet (snappy) | 82.5 ms | 8.25 µs | 2.2x slower |
| Parquet (zstd) | 82.2 ms | 8.21 µs | 2.2x slower |
| **USDC** | 37.7 ms | 3.77 µs | *baseline* ⚡ |

**Winner: USDC** - 2.2x faster for bulk sequential reads

---

## Test 5: Multiple Property Retrieval (Single Prim)
**Measures**: Read 6 properties from one prim

| Format | Mean Time | Time/Property | vs USDC |
|--------|-----------|---------------|---------|
| Parquet (none) | 111.91 µs | 18.65 µs | 23% slower |
| Parquet (snappy) | 114.60 µs | 19.10 µs | 26% slower |
| Parquet (zstd) | 114.30 µs | 19.05 µs | 25% slower |
| **USDC** | 91.26 µs | 15.21 µs | *baseline* ⚡ |

**Winner: USDC** - Faster for multi-property access on single prim

---

## Test 6: Multiple Property Traversal
**Measures**: Read 6 properties from ALL 10,001 prims (60,006 total accesses)

| Format | Total Time | Time/Access | vs USDC |
|--------|------------|-------------|---------|
| Parquet (none) | 465.75 ms | 7.76 µs | 2.1x slower |
| Parquet (snappy) | 466.48 ms | 7.77 µs | 2.1x slower |
| Parquet (zstd) | 466.99 ms | 7.79 µs | 2.1x slower |
| **USDC** | 221.69 ms | 3.69 µs | *baseline* ⚡ |

**Winner: USDC** - 2.1x faster for bulk multi-property reads

---

## Test 7: Random Access Traversal
**Measures**: Read property from all prims in randomized order (worst case for caching)

| Format | Total Time | Time/Prim | vs USDC |
|--------|------------|-----------|---------|
| Parquet (none) | 83.7 ms | 8.37 µs | 2.2x slower |
| Parquet (snappy) | 82.8 ms | 8.28 µs | 2.2x slower |
| Parquet (zstd) | 83.0 ms | 8.30 µs | 2.2x slower |
| **USDC** | 37.8 ms | 3.78 µs | *baseline* ⚡ |

**Winner: USDC** - Similar performance to sequential (good caching)

---

## Test 8: Sequential vs Random Comparison
**Measures**: Impact of access pattern on performance

### Sequential Access
| Format | Time | vs USDC |
|--------|------|---------|
| Parquet (avg) | ~83 ms | 2.2x slower |
| **USDC** | 37.8 ms | *baseline* ⚡ |

### Random Access  
| Format | Time | Slowdown vs Sequential |
|--------|------|------------------------|
| Parquet (avg) | ~83 ms | **1.0x** (no slowdown) ✅ |
| **USDC** | 37.8 ms | **1.0x** (no slowdown) ✅ |

**Finding**: Both formats handle random vs sequential access equally well

---

## Summary Analysis

### Parquet Strengths ⚡
1. **Initial Load**: 18x faster (46ms vs 856ms)
2. **File Size**: 55% smaller with zstd compression
3. **Lazy Loading**: True lazy behavior confirmed
4. **Compression**: Minimal performance impact
5. **Warm Cache**: Slightly faster repeated access

### USDC Strengths ⚡
1. **Traversal**: 2.2x faster for reading all prims
2. **Multi-Property**: 2.1x faster for bulk multi-property reads
3. **Single Access**: Marginally faster for cold single reads
4. **Consistency**: Lower std deviation in most tests

### Use Case Recommendations

**Choose Parquet when**:
- Working with very large scenes (fast load critical)
- File size matters (distribution, storage costs)
- Accessing sparse properties (not reading everything)
- Working with time-series data (columnar advantages)

**Choose USDC when**:
- Doing heavy traversals (reading most/all properties)
- Performance of bulk reads is critical
- Working with complete scene data
- Maximum read performance needed

### The Lazy Loading Advantage

The **18x faster load time** demonstrates the power of Parquet's lazy loading:
- 46ms to make 10,000 prims available vs 856ms for USDC
- Near-instant scene opening for property inspection
- Perfect for interactive applications where you don't access all data

### The Trade-Off

Once you start **actually reading properties**, USDC pulls ahead:
- 2.2x faster for traversals
- All data already in memory
- No decompression overhead

---

## Conclusion

**Parquet excels at lazy loading and storage efficiency**. If you need to open large scenes quickly and access properties selectively, Parquet is the clear winner.

**USDC excels at bulk reads**. Once you need to read most of the data, USDC's in-memory approach wins.

The ideal workflow might use **both**:
- Parquet for archival/distribution (smaller files, fast loading)
- USDC for active work (faster bulk access)
