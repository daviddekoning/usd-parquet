# OpenUSD File Format Plugin Implementation Plan: Parquet Metadata Reader

## Overview

This document outlines the plan for implementing a custom OpenUSD File Format Plugin capable of reading metadata from Parquet files and presenting it as a USD Layer. The primary goal is to achieve high performance and memory efficiency by leveraging a **Block-Aware Column Caching** strategy, ensuring that data is lazy-loaded at the Parquet Row Group (Block) level.  
The resulting layer will contain only **over PrimSpecs** whose paths are defined by the path column in the Parquet file, and whose properties are defined by the remaining columns.

## Goals and Use Cases

This plugin bridges the gap between high-scale data engineering formats (Parquet) and 3D scene description (USD). It enables non-destructive, high-performance injection of tabular data into a 3D pipeline.

### Core Objectives

- Scalable Metadata Injection: Handle millions of prims by leveraging Parquet's columnar storage.
- Non-Destructive Workflows: Use USD's "over" mechanism to add attributes without modifying the original geometric assets.
- Low Memory Footprint: Only load the specific properties and row groups required by the current viewport or render task.

### Example Use Cases

- Simulation Overlays: Reading per-prim velocity, temperature, or stress data from an external physics solver and applying it as USD attributes for visualization.
- ML Training Data: Injecting classification labels or confidence scores from a machine learning pipeline onto a 3D dataset for verification.
- Digital Twins: Connecting live IoT sensor data (archived in Parquet) to 3D equipment models in a scene by matching sensor IDs to USD prim paths.

## I. Core Components and Architecture

The plugin will consist of three main components:

### 1. plugInfo.json

* **Purpose:** Registers the plugin with the USD system (PlugRegistry and Sdf\_FileFormatRegistry).  
* **Action:** Defines the file format ID, the file extension (e.g., .parquet), and registers the custom SdfFileFormat class.

### **2\. MyParquetFileFormat (Derived from SdfFileFormat)**

* **Purpose:** The entry point for USD to open a layer.  
* **Action:** Overrides the virtual method InitData() to instantiate and return an object of the custom lazy data class (MyParquetLazyData).

### **3\. MyParquetLazyData (Derived from SdfAbstractData)**

* **Purpose:** The core class responsible for handling all USD scene description queries (HasSpec, Get, GetChildrenNames) by translating them into optimized Parquet I/O operations. This class holds the caching logic.

## **II. Implementation Phases**

### **Phase 1: Foundation and Path Indexing (Eager Read)**

This phase establishes the layer's structure and the crucial index required for all future lazy lookups.  
| Step | Detail | USD Method/Class |  
|------|------|------|
| 1\. Parquet Integration | Integrate a C++ Parquet/Apache Arrow library (e.g., via std::unique\_ptr in the data class). | N/A |  
| 2\. Path Indexing | On initialization of MyParquetLazyData, perform an EAGER bulk read of the entire path column from the Parquet file. | MyParquetLazyData constructor |  
| 3\. Index Creation | Create the \_pathLocationIndex map: std::map\<SdfPath, ParquetLocation\>. Map each SdfPath to its physical Parquet location: {rowGroupID, rowOffset}. | MyParquetLazyData constructor |  
| 4\. Basic Query Support | Implement HasSpec(path) to perform a fast lookup in the \_pathLocationIndex. | MyParquetLazyData::HasSpec |  
| 5\. Property Listing | Read the Parquet file schema to determine all column names (excluding path). This list is used to satisfy USD queries for the available properties on a prim. | MyParquetLazyData::Get(path, 'properties') |

### **Phase 2: Block-Aware Caching (Lazy Data Read)**

This phase implements the memory-efficient lazy loading by structuring the cache around Parquet blocks.  
| Step | Detail | Data Structure |  
|------|------|------|
| 1\. Define Cache Structure | Implement the nested cache structure keyed by property name and block ID. | std::map\<TfToken, std::map\<int, VtValueArray\>\> \_blockColumnCache; |  
| 2\. Implement Get() | For any property query (Get(path, propName)): a. Use the \_pathLocationIndex (Phase 1\) to retrieve rowGroupID and rowOffset. b. Check the \_blockColumnCache\[propName\]\[rowGroupID\]. | MyParquetLazyData::Get |  
| 3\. Cache Miss Handler | If a block is not in the cache (miss): a. Trigger a single, bulk I/O read to fetch only the propName column data for only rowGroupID. b. Deserialize the block data and store it in \_blockColumnCache. | MyParquetLazyData::Get (internal logic) |  
| 4\. Cache Hit Fulfillment | Retrieve the value at rowOffset from the cached VtValueArray for that block. | MyParquetLazyData::Get |  
| 5\. Type Conversion | Implement robust logic to convert Parquet types (e.g., INT32, FLOAT, BYTE\_ARRAY) into the corresponding USD VtValue types. | Utility functions |

### **Phase 3: Advanced Optimization**

| Step | Detail | Optimization |  
| 1\. Cache Pruning | Implement a Least Recently Used (LRU) eviction policy on the outermost cache layer (\_blockColumnCache). | Limits the memory footprint of loaded Parquet blocks. |

## **III. File Format Capabilities**

The plugInfo.json capabilities will be set as follows:

* supportsReading: **true**  
* supportsWriting: **false** (The plugin is designed as a read-only metadata layer).  
* supportsEditing: **false**