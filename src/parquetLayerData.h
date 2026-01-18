#ifndef PARQUET_LAYER_DATA_H
#define PARQUET_LAYER_DATA_H

#include <pxr/pxr.h>
#include <pxr/usd/sdf/abstractData.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/base/vt/value.h>
#include <pxr/base/tf/token.h>

#include <parquet/file_reader.h>
#include <arrow/api.h>

#include <map>
#include <memory>
#include <set>
#include <vector>

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(ParquetLayerData);

class ParquetLayerData : public SdfAbstractData {
public:
    ParquetLayerData();
    ~ParquetLayerData() override;

    // SdfAbstractData overrides
    bool StreamsData() const override;
    bool HasSpec(const SdfPath& path) const override;
    void CreateSpec(const SdfPath& path, SdfSpecType specType) override;
    bool Has(const SdfPath& path, const TfToken& field, VtValue* value) const override;
    bool Has(const SdfPath& path, const TfToken& field, SdfAbstractDataValue* value) const override;
    VtValue Get(const SdfPath& path, const TfToken& field) const override;
    void Set(const SdfPath& path, const TfToken& field, const VtValue& value) override;
    void Set(const SdfPath& path, const TfToken& field, const SdfAbstractDataConstValue& value) override;
    void Erase(const SdfPath& path, const TfToken& field) override;
    std::vector<TfToken> List(const SdfPath& path) const override;

    // Time samples
    std::set<double> ListAllTimeSamples() const override;
    std::set<double> ListTimeSamplesForPath(const SdfPath& path) const override;
    bool GetBracketingTimeSamples(double time, double* tLower, double* tUpper) const override;
    bool GetBracketingTimeSamplesForPath(const SdfPath& path, double time, double* tLower, double* tUpper) const override;
    size_t GetNumTimeSamplesForPath(const SdfPath& path) const override;
    bool QueryTimeSample(const SdfPath& path, double time, VtValue* value) const override;
    bool QueryTimeSample(const SdfPath& path, double time, SdfAbstractDataValue* value) const override;
    void SetTimeSample(const SdfPath& path, double time, const VtValue& value) override;
    void EraseTimeSample(const SdfPath& path, double time) override;

    // Prim data access
    SdfSpecType GetSpecType(const SdfPath& path) const override;
    void EraseSpec(const SdfPath& path) override;
    void MoveSpec(const SdfPath& oldPath, const SdfPath& newPath) override;

    // Visitation
    void _VisitSpecs(SdfAbstractDataSpecVisitor* visitor) const override;

    // Lazy behavior - we need to open the file and index it.
    bool Open(const std::string& filePath);

private:
    struct ParquetLocation {
        int rowGroup;
        int64_t rowOffset;
    };

    // Index of prim paths to their location in the parquet file.
    std::map<SdfPath, ParquetLocation> _pathIndex;
    
    // All paths including generated ancestors (for hierarchical support)
    std::set<SdfPath> _allPaths;
    
    // Map of parent path to child names for efficient children lookup
    std::map<SdfPath, std::vector<TfToken>> _childrenMap;
    
    // Column Names (properties)
    std::vector<TfToken> _propertyNames;

    // Cache: field name -> row group index -> data for that block
    // Using a simple VtValue array per block for now.
    mutable std::map<TfToken, std::map<int, VtValue>> _blockCache;

    std::unique_ptr<parquet::ParquetFileReader> _reader;
    std::shared_ptr<parquet::FileMetaData> _fileMetadata;

    // Internal helper to load a block into cache if missing
    void _LoadBlock(const TfToken& field, int rowGroup) const;
    
    // Build the path hierarchy from indexed paths
    void _BuildPathHierarchy();
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif // PARQUET_LAYER_DATA_H
