# USD Parquet Plugin

A custom OpenUSD file format plugin that natively reads Parquet files as USD layers. This plugin allows you to treat Parquet files like regular USD files, enabling high-performance reading of tabular data into the USD stage.

## Overview

This plugin implements `SdfFileFormat` to read Parquet files using the Apache Arrow C++ library. It features:

- **Native Parquet Reading**: Direct zero-copy reading using Arrow.
- **Hierarchical Path Support**: Automatically reconstructs USD hierarchy from path columns (e.g., `/World/Sphere1`).
- **Lazy Loading**: Attributes are loaded only when requested using block caching.
- **Full Composition Support**: Parquet layers can be sublayered and will correctly override base layer defaults.

For a deep dive into the technical design, see [Architecture](./architecture.md).

## Usage

### Prerequisites

- OpenUSD v25.11+
- Apache Arrow C++
- Python 3.12+

### Building

```bash
mkdir build && cd build
cmake -Dpxr_DIR=~/OpenUSD-25.11-install ..
make
```

### Running

Ensure the plugin is in your `PXR_PLUGINPATH_NAME`:

```bash
export PXR_PLUGINPATH_NAME=$(pwd)/build/resources
export PYTHONPATH=~/OpenUSD-25.11-install/lib/python

# Run the test script
uv run python tests/test_parquet_plugin.py
```

## Features

- **Read-Only**: The plugin currently supports reading Parquet files.
- **Data Types**: Supports float, double, int, int64, boolean, and string arrays.
- **Specifiers**: All prims are loaded as "over" specifiers to support composition.

## Testing

The project includes a comprehensive test suite in `tests/test_parquet_plugin.py` that verifies:
1. Plugin loading and registration
2. Hierarchical path reconstruction
3. Attribute value resolution
4. Layer composition (Parquet layer overriding base layer)
