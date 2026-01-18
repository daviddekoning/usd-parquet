#ifndef PARQUET_FILE_FORMAT_H
#define PARQUET_FILE_FORMAT_H

#include <pxr/pxr.h>
#include <pxr/usd/sdf/fileFormat.h>
#include <pxr/base/tf/staticTokens.h>

PXR_NAMESPACE_OPEN_SCOPE

TF_DECLARE_WEAK_AND_REF_PTRS(ParquetFileFormat);

class ParquetFileFormat : public SdfFileFormat {
public:
    // Returns true if this file format can read the file at filePath.
    bool CanRead(const std::string& filePath) const override;

    // Reads the file at filePath into the given layer.
    bool Read(SdfLayer* layer,
              const std::string& resolvedPath,
              bool metadataOnly) const override;

protected:
    SdfAbstractDataRefPtr InitData(const FileFormatArguments& args) const override;

private:
    SDF_FILE_FORMAT_FACTORY_ACCESS;

    ParquetFileFormat();
    ~ParquetFileFormat() override;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif // PARQUET_FILE_FORMAT_H
