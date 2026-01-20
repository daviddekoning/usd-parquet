# USD Parquet Plugin

This is a proof of concept custom OpenUSD file format plugin that reads prim properties from Parquet files. The parquet is presented as a USD layer, and the properties are added to prims via an `over`. 

The aim of this PoC is to explore the possiblity of bridging the VFX / 3D modelling world with the data science / engineering world.

Both OpenUSD and Parquet allow large files to be processed without fully loading them into memory. This PoC uses Parquets storage mechanism to lazily load the property data as it is access, rather than loading it all at load time. 

**Disclaimer**: This has been mostly built by various AI models. The overall architecture (see [A   rchitecture](./architecture.md)) was elaborated in Google Gemini (the chatbot), with me reading the OpenUSD API reference, feeding in the high-level concept and correcting certain method names. This architecture was then implemented in Antigravity (using Opus 4.5, and various Gemini models). I am not a proficient C++ developer, so I mainly controlled the model's work by specifying the test cases I wanted to see.

## Parquet schema

This plugin expects a parquet file with a column called 'path' (string) and then a number of other columns with the property values. The path column is used to reconstruct the USD hierarchy. The other columns correspond to a property that will be accessible on the prim.

For example, a parquet file with the following data:

| path | temperature | pressure |
|------|-------------|----------|
| /World/Sphere1 | 20.0 | 101325.0 |
| /World/Cube1 | 25.0 | 101325.0 |

is presented as:

```usda
#usda 1.0

over "World"
{
    over "Sphere1"
    {
        double temperature = 20.0
        double pressure = 101325.0
    }
    over "Cube1"
    {
        double temperature = 25.0
        double pressure = 101325.0
    }
}
```

There is a small utility script in the test folder called `view_parquet.py` that can be used to inspect the contents of a parquet file. If you have uv installed, you can make the script executable (`chmod u+x ...`) and run it directly.

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

Run the scripts `create_test_parquet.py` and `generate_large_parquet.py` to create test data. 
