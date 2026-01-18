#include "parquetLayerData.h"

#include <pxr/usd/sdf/schema.h>
#include <pxr/base/vt/array.h>

#include <parquet/arrow/reader.h>
#include <parquet/column_reader.h>
#include <parquet/properties.h>
#include <arrow/io/file.h>
#include <arrow/table.h>

#include <pxr/usd/sdf/layer.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/sdf/types.h>
#include <iostream>
#include <algorithm>

PXR_NAMESPACE_OPEN_SCOPE

ParquetLayerData::ParquetLayerData() {
}

ParquetLayerData::~ParquetLayerData() {
}

bool ParquetLayerData::StreamsData() const {
    return false;
}

bool ParquetLayerData::Open(const std::string& filePath) {
    try {
        _reader = parquet::ParquetFileReader::OpenFile(filePath, false);
        _fileMetadata = _reader->metadata();

        auto schema = _fileMetadata->schema();
        int numColumns = schema->num_columns();

        // 1. Determine "path" column index and collect other properties
        int pathColIdx = -1;
        _propertyNames.clear();

        for (int i = 0; i < numColumns; ++i) {
            std::string name = schema->Column(i)->name();
            if (name == "path") {
                pathColIdx = i;
            } else {
                _propertyNames.push_back(TfToken(name));
            }
        }

        if (pathColIdx == -1) {
            std::cerr << "Parquet file missing 'path' column: " << filePath << std::endl;
            return false;
        }

        // 2. Eagerly read the "path" column to build the index
        int numRowGroups = _fileMetadata->num_row_groups();
        for (int rg = 0; rg < numRowGroups; ++rg) {
            auto rowGroupReader = _reader->RowGroup(rg);
            auto colReader = std::static_pointer_cast<parquet::ByteArrayReader>(
                rowGroupReader->Column(pathColIdx));

            int64_t valuesRead = 0;
            int64_t rowsInGroup = _fileMetadata->RowGroup(rg)->num_rows();
            
            // For simplicity, reading all at once. For massive files, we'd loop.
            std::vector<parquet::ByteArray> values(rowsInGroup);
            std::vector<int16_t> defLevels(rowsInGroup);
            std::vector<int16_t> repLevels(rowsInGroup);
            
            colReader->ReadBatch(rowsInGroup, defLevels.data(), repLevels.data(), 
                               values.data(), &valuesRead);

            for (int64_t i = 0; i < valuesRead; ++i) {
                std::string pathStr(reinterpret_cast<const char*>(values[i].ptr), values[i].len);
                SdfPath path(pathStr);
                if (path.IsAbsolutePath()) {
                    _pathIndex[path] = {rg, i};
                }
            }
        }

        // Build the path hierarchy for proper USD traversal
        _BuildPathHierarchy();

        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error opening Parquet: " << e.what() << std::endl;
        return false;
    }
}

bool ParquetLayerData::HasSpec(const SdfPath& path) const {
    // Check pseudo-root
    if (path == SdfPath::AbsoluteRootPath()) return true;
    
    // Check property paths (e.g., /World/Sphere1.temperature)
    if (path.IsPropertyPath()) {
        SdfPath primPath = path.GetPrimPath();
        TfToken propName = path.GetNameToken();
        // Check if the prim exists and has this property
        if (_pathIndex.count(primPath)) {
            for (const auto& prop : _propertyNames) {
                if (prop == propName) {
                     return true;
                }
            }
        }
        return false;
    }
    
    // Check all prim paths including intermediate ancestors
    return _allPaths.count(path) > 0;
}

void ParquetLayerData::CreateSpec(const SdfPath& path, SdfSpecType specType) {
    // Read-only
}

bool ParquetLayerData::Has(const SdfPath& path, const TfToken& field, VtValue* value) const {
    // Debug: trace what USD is querying
    if (field == SdfChildrenKeys->PrimChildren) {
        std::cerr << "[ParquetPlugin] Has(" << path << ", primChildren) called, _childrenMap.count=" 
                  << _childrenMap.count(path) << std::endl;
    }
    
    // Handle property paths (e.g., /World/Sphere1.temperature)
    if (path.IsPropertyPath()) {
        SdfPath primPath = path.GetPrimPath();
        TfToken propName = path.GetNameToken();
        
        // Check if this is one of our properties
        auto it = _pathIndex.find(primPath);
        if (it != _pathIndex.end()) {
            for (const auto& prop : _propertyNames) {
                if (prop == propName) {
                    // Return attribute fields
                    if (field == SdfFieldKeys->Default) {
                        VtValue val = Get(path, field); // Call our own Get for property path
                        bool hasVal = !val.IsEmpty();
                        if (hasVal && value) *value = val;
                        return hasVal;
                    }
                    if (field == SdfFieldKeys->TypeName) {
                        // Get type from cached block
                        _LoadBlock(propName, it->second.rowGroup);
                        const VtValue& block = _blockCache[propName][it->second.rowGroup];
                        if (block.IsHolding<VtArray<float>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->Float);
                        } else if (block.IsHolding<VtArray<double>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->Double);
                        } else if (block.IsHolding<VtArray<int>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->Int);
                        } else if (block.IsHolding<VtArray<int64_t>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->Int64);
                        } else if (block.IsHolding<VtArray<bool>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->Bool);
                        } else if (block.IsHolding<VtArray<std::string>>()) {
                            if (value) *value = VtValue(SdfValueTypeNames->String);
                        }
                        return true;
                    }
                    if (field == SdfFieldKeys->Variability) {
                        if (value) *value = VtValue(SdfVariabilityVarying);
                        return true;
                    }
                    if (field == SdfFieldKeys->Custom) {
                        if (value) *value = VtValue(false);
                        return true;
                    }
                    break;
                }
            }
        }
        return false;
    }
    
    // PrimChildren is available for any path in the hierarchy
    if (field == SdfChildrenKeys->PrimChildren) {
        if (_childrenMap.count(path) || path == SdfPath::AbsoluteRootPath()) {
            if (value) *value = Get(path, field);
            return true;
        }
    }
    
    // PropertyChildren for data prims
    if (field == SdfChildrenKeys->PropertyChildren && _pathIndex.count(path)) {
        if (value) *value = VtValue(VtTokenArray(_propertyNames.begin(), _propertyNames.end()));
        return true;
    }
    
    // Specifier field - all prims in this layer use "over"
    if (field == SdfFieldKeys->Specifier && _allPaths.count(path)) {
        if (value) *value = VtValue(SdfSpecifierOver);
        return true;
    }
    
    return false;
}

bool ParquetLayerData::Has(const SdfPath& path, const TfToken& field, SdfAbstractDataValue* value) const {
    VtValue val;
    if (Has(path, field, &val)) {
        if (value) value->StoreValue(val);
        return true;
    }
    return false;
}

VtValue ParquetLayerData::Get(const SdfPath& path, const TfToken& field) const {
    // Handle PrimChildren for any path in the hierarchy
    if (field == SdfChildrenKeys->PrimChildren) {
        auto it = _childrenMap.find(path);
        if (it != _childrenMap.end()) {
            VtTokenArray children(it->second.begin(), it->second.end());
            return VtValue(children);
        }
        return VtValue(VtTokenArray());
    }
    
    // Handle PropertyChildren for data prims
    if (field == SdfChildrenKeys->PropertyChildren && _pathIndex.count(path)) {
        return VtValue(VtTokenArray(_propertyNames.begin(), _propertyNames.end()));
    }
    
    // Handle specifier field - all prims use "over"
    if (field == SdfFieldKeys->Specifier && _allPaths.count(path)) {
        return VtValue(SdfSpecifierOver);
    }
    
    // Handle property specs (e.g., /World/Sphere1.temperature)
    if (path.IsPropertyPath()) {
        SdfPath primPath = path.GetPrimPath();
        TfToken propName = path.GetNameToken();
        auto it = _pathIndex.find(primPath);
        
        if (it != _pathIndex.end()) {
            bool found = false;
            for (const auto& prop : _propertyNames) {
                if (prop == propName) {
                    found = true;
                    break;
                }
            }
            
            if (found) {
                if (field == SdfFieldKeys->Default) {
                    // Get value from cache
                    const auto& loc = it->second;
                    _LoadBlock(propName, loc.rowGroup);
                    const VtValue& block = _blockCache[propName][loc.rowGroup];
                    
                    if (block.IsHolding<VtArray<float>>()) {
                        return VtValue(block.UncheckedGet<VtArray<float>>()[loc.rowOffset]);
                    } else if (block.IsHolding<VtArray<double>>()) {
                        return VtValue(block.UncheckedGet<VtArray<double>>()[loc.rowOffset]);
                    } else if (block.IsHolding<VtArray<int>>()) {
                        return VtValue(block.UncheckedGet<VtArray<int>>()[loc.rowOffset]);
                    } else if (block.IsHolding<VtArray<int64_t>>()) {
                        return VtValue(block.UncheckedGet<VtArray<int64_t>>()[loc.rowOffset]);
                    } else if (block.IsHolding<VtArray<bool>>()) {
                        return VtValue(block.UncheckedGet<VtArray<bool>>()[loc.rowOffset]);
                    } else if (block.IsHolding<VtArray<std::string>>()) {
                        return VtValue(block.UncheckedGet<VtArray<std::string>>()[loc.rowOffset]);
                    }
                } else if (field == SdfFieldKeys->TypeName) {
                    const auto& loc = it->second;
                    _LoadBlock(propName, loc.rowGroup);
                    const VtValue& block = _blockCache[propName][loc.rowGroup];
                    
                    if (block.IsHolding<VtArray<float>>()) return VtValue(SdfValueTypeNames->Float.GetAsToken());
                    if (block.IsHolding<VtArray<double>>()) return VtValue(SdfValueTypeNames->Double.GetAsToken());
                    if (block.IsHolding<VtArray<int>>()) return VtValue(SdfValueTypeNames->Int.GetAsToken());
                    if (block.IsHolding<VtArray<int64_t>>()) return VtValue(SdfValueTypeNames->Int64.GetAsToken());
                    if (block.IsHolding<VtArray<bool>>()) return VtValue(SdfValueTypeNames->Bool.GetAsToken());
                    if (block.IsHolding<VtArray<std::string>>()) return VtValue(SdfValueTypeNames->String.GetAsToken());
                } else if (field == SdfFieldKeys->Variability) {
                    return VtValue(SdfVariabilityVarying);
                } else if (field == SdfFieldKeys->Custom) {
                    return VtValue(false);
                }
            }
        }
    }

    return VtValue();
}

void ParquetLayerData::Set(const SdfPath& path, const TfToken& field, const VtValue& value) {}
void ParquetLayerData::Set(const SdfPath& path, const TfToken& field, const SdfAbstractDataConstValue& value) {}
void ParquetLayerData::Erase(const SdfPath& path, const TfToken& field) {}

std::vector<TfToken> ParquetLayerData::List(const SdfPath& path) const {
    std::vector<TfToken> fields;
    
    // Handle property paths (return attribute fields)
    if (path.IsPropertyPath()) {
        fields.push_back(SdfFieldKeys->Default);
        fields.push_back(SdfFieldKeys->TypeName);
        fields.push_back(SdfFieldKeys->Variability);
        fields.push_back(SdfFieldKeys->Custom);
        return fields;
    }
    
    // If this path has children, include PrimChildren
    if (_childrenMap.count(path) || path == SdfPath::AbsoluteRootPath()) {
        fields.push_back(SdfChildrenKeys->PrimChildren);
    }
    
    // If this is a prim, include Specifier
    if (_allPaths.count(path)) {
        fields.push_back(SdfFieldKeys->Specifier);
    }
    
    // If this is a data prim, include PropertyChildren
    if (_pathIndex.count(path) && !_propertyNames.empty()) {
        fields.push_back(SdfChildrenKeys->PropertyChildren);
    }
    
    return fields;
}

std::set<double> ParquetLayerData::ListAllTimeSamples() const {
    return std::set<double>();
}

std::set<double> ParquetLayerData::ListTimeSamplesForPath(const SdfPath& path) const {
    return std::set<double>();
}

bool ParquetLayerData::GetBracketingTimeSamples(double time, double* tLower, double* tUpper) const {
    return false;
}

bool ParquetLayerData::GetBracketingTimeSamplesForPath(const SdfPath& path, double time, double* tLower, double* tUpper) const {
    return false;
}

size_t ParquetLayerData::GetNumTimeSamplesForPath(const SdfPath& path) const {
    return 0;
}

bool ParquetLayerData::QueryTimeSample(const SdfPath& path, double time, VtValue* value) const {
    return false;
}

bool ParquetLayerData::QueryTimeSample(const SdfPath& path, double time, SdfAbstractDataValue* value) const {
    return false;
}

void ParquetLayerData::SetTimeSample(const SdfPath& path, double time, const VtValue& value) {}

void ParquetLayerData::EraseTimeSample(const SdfPath& path, double time) {}

SdfSpecType ParquetLayerData::GetSpecType(const SdfPath& path) const {
    if (path == SdfPath::AbsoluteRootPath()) return SdfSpecTypePseudoRoot;
    
    // Check for property paths
    if (path.IsPropertyPath()) {
        SdfPath primPath = path.GetPrimPath();
        TfToken propName = path.GetNameToken();
        if (_pathIndex.count(primPath)) {
            for (const auto& prop : _propertyNames) {
                if (prop == propName) return SdfSpecTypeAttribute;
            }
        }
        return SdfSpecTypeUnknown;
    }
    
    // Both data prims and intermediate ancestor prims are prim specs
    if (_allPaths.count(path)) return SdfSpecTypePrim;
    return SdfSpecTypeUnknown;
}

void ParquetLayerData::EraseSpec(const SdfPath& path) {}
void ParquetLayerData::MoveSpec(const SdfPath& oldPath, const SdfPath& newPath) {}

void ParquetLayerData::_VisitSpecs(SdfAbstractDataSpecVisitor* visitor) const {
    // Visit the pseudo-root
    if (!visitor->VisitSpec(*this, SdfPath::AbsoluteRootPath())) {
        return;
    }
    
    // Visit all paths (both data prims and intermediate ancestors)
    for (const auto& path : _allPaths) {
        if (!visitor->VisitSpec(*this, path)) {
            return;
        }
        
        // If this is a data prim, visit its properties
        if (_pathIndex.count(path)) {
            for (const auto& prop : _propertyNames) {
                SdfPath propPath = path.AppendProperty(prop);
                if (!visitor->VisitSpec(*this, propPath)) {
                    return;
                }
            }
        }
    }
}

void ParquetLayerData::_LoadBlock(const TfToken& field, int rowGroup) const {
    if (_blockCache[field].count(rowGroup)) return;

    // Trigger lazy read for this column in this row group
    auto rowGroupReader = _reader->RowGroup(rowGroup);
    
    // Find column index for field
    int colIdx = -1;
    auto schema = _fileMetadata->schema();
    for (int i = 0; i < schema->num_columns(); ++i) {
        if (schema->Column(i)->name() == field.GetString()) {
            colIdx = i;
            break;
        }
    }

    if (colIdx == -1) return;

    auto colReader = rowGroupReader->Column(colIdx);
    int64_t rowsInGroup = _fileMetadata->RowGroup(rowGroup)->num_rows();

    if (colReader->type() == parquet::Type::FLOAT) {
        auto floatReader = std::static_pointer_cast<parquet::FloatReader>(colReader);
        VtArray<float> data(rowsInGroup);
        int64_t valuesRead = 0;
        floatReader->ReadBatch(rowsInGroup, nullptr, nullptr, data.data(), &valuesRead);
        _blockCache[field][rowGroup] = VtValue(data);
    } else if (colReader->type() == parquet::Type::DOUBLE) {
        auto doubleReader = std::static_pointer_cast<parquet::DoubleReader>(colReader);
        VtArray<double> data(rowsInGroup);
        int64_t valuesRead = 0;
        doubleReader->ReadBatch(rowsInGroup, nullptr, nullptr, data.data(), &valuesRead);
        _blockCache[field][rowGroup] = VtValue(data);
    } else if (colReader->type() == parquet::Type::INT32) {
        auto intReader = std::static_pointer_cast<parquet::Int32Reader>(colReader);
        VtArray<int> data(rowsInGroup);
        int64_t valuesRead = 0;
        intReader->ReadBatch(rowsInGroup, nullptr, nullptr, data.data(), &valuesRead);
        _blockCache[field][rowGroup] = VtValue(data);
    } else if (colReader->type() == parquet::Type::INT64) {
        auto int64Reader = std::static_pointer_cast<parquet::Int64Reader>(colReader);
        VtArray<int64_t> data(rowsInGroup);
        int64_t valuesRead = 0;
        int64Reader->ReadBatch(rowsInGroup, nullptr, nullptr, data.data(), &valuesRead);
        _blockCache[field][rowGroup] = VtValue(data);
    } else if (colReader->type() == parquet::Type::BOOLEAN) {
        auto boolReader = std::static_pointer_cast<parquet::BoolReader>(colReader);
        VtArray<bool> data(rowsInGroup);
        int64_t valuesRead = 0;
        boolReader->ReadBatch(rowsInGroup, nullptr, nullptr, data.data(), &valuesRead);
        _blockCache[field][rowGroup] = VtValue(data);
    } else if (colReader->type() == parquet::Type::BYTE_ARRAY) {
        auto stringReader = std::static_pointer_cast<parquet::ByteArrayReader>(colReader);
        std::vector<parquet::ByteArray> rawData(rowsInGroup);
        int64_t valuesRead = 0;
        stringReader->ReadBatch(rowsInGroup, nullptr, nullptr, rawData.data(), &valuesRead);
        VtArray<std::string> data(valuesRead);
        for (int64_t i = 0; i < valuesRead; ++i) {
            data[i] = std::string(reinterpret_cast<const char*>(rawData[i].ptr), rawData[i].len);
        }
        _blockCache[field][rowGroup] = VtValue(data);
    }
}

void ParquetLayerData::_BuildPathHierarchy() {
    // Clear existing data
    _allPaths.clear();
    _childrenMap.clear();
    
    // Process each indexed path
    for (const auto& pair : _pathIndex) {
        const SdfPath& path = pair.first;
        _allPaths.insert(path);
        
        // Walk up the path hierarchy and register all ancestors
        SdfPath current = path;
        while (current != SdfPath::AbsoluteRootPath()) {
            SdfPath parent = current.GetParentPath();
            
            // Add this path as a child of its parent
            TfToken childName = current.GetNameToken();
            auto& children = _childrenMap[parent];
            if (std::find(children.begin(), children.end(), childName) == children.end()) {
                children.push_back(childName);
            }
            
            // Add ancestor to allPaths (if not the root)
            if (parent != SdfPath::AbsoluteRootPath()) {
                _allPaths.insert(parent);
            }
            
            current = parent;
        }
    }
}

PXR_NAMESPACE_CLOSE_SCOPE

