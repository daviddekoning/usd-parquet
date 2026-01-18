#include "parquetFileFormat.h"
#include "parquetLayerData.h"

#include <pxr/usd/sdf/layer.h>
#include <pxr/base/tf/type.h>
#include <pxr/base/tf/pathUtils.h>

#include <iostream>

PXR_NAMESPACE_OPEN_SCOPE

TF_REGISTRY_FUNCTION(TfType) {
    SDF_DEFINE_FILE_FORMAT(ParquetFileFormat, SdfFileFormat);
}

ParquetFileFormat::ParquetFileFormat()
    : SdfFileFormat(TfToken("parquetFormat"),
                    TfToken("1.0"),
                    TfToken("usd"),
                    TfToken("parquet")) {
}

ParquetFileFormat::~ParquetFileFormat() {
}

bool ParquetFileFormat::CanRead(const std::string& filePath) const {
    std::cerr << "[ParquetPlugin] CanRead checking: " << filePath << std::endl;
    bool match = TfGetExtension(filePath) == "parquet";
    std::cerr << "[ParquetPlugin] CanRead result: " << (match ? "TRUE" : "FALSE") << std::endl;
    return match;
}

bool ParquetFileFormat::Read(SdfLayer* layer,
                            const std::string& resolvedPath,
                            bool metadataOnly) const {
    std::cerr << "[ParquetPlugin] Read called for: " << resolvedPath << std::endl;
    if (!TF_VERIFY(layer)) {
        return false;
    }

    // Create the custom data object using our InitData override
    const FileFormatArguments& args = layer->GetFileFormatArguments();
    SdfAbstractDataRefPtr data = InitData(args);
    ParquetLayerDataRefPtr parquetData = 
        TfStatic_cast<ParquetLayerDataRefPtr>(data);
    
    // Open and initialize the parquet file
    if (!parquetData->Open(resolvedPath)) {
        return false;
    }

    // Set the data on the layer using the protected method from SdfFileFormat
    _SetLayerData(layer, data);

    // Enforce read-only since this is a read-only format
    layer->SetPermissionToSave(false);
    layer->SetPermissionToEdit(false);

    return true;
}

SdfAbstractDataRefPtr ParquetFileFormat::InitData(const FileFormatArguments& args) const {
    return TfCreateRefPtr(new ParquetLayerData());
}

PXR_NAMESPACE_CLOSE_SCOPE
