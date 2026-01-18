cmake_minimum_required(VERSION 3.10)
project(usd-parquet)

set(CMAKE_CXX_STANDARD 17)

# Paths to OpenUSD and Arrow should be passed via CMAKE_PREFIX_PATH
# or set here if they are in standard locations.
# For this project, we expects them in ~/OpenUSD-install and /opt/homebrew

find_package(pxr REQUIRED)
find_package(Arrow REQUIRED)
find_package(Parquet REQUIRED)

include_directories(
    ${PXR_INCLUDE_DIRS}
    ${ARROW_INCLUDE_DIR}
    ${PARQUET_INCLUDE_DIR}
    ${PROJECT_SOURCE_DIR}/src
)

add_library(parquetFormat SHARED
    src/parquetFileFormat.cpp
    src/parquetLayerData.cpp
)

target_link_libraries(parquetFormat
    PRIVATE
    ${PXR_LIBRARIES}
    Arrow::arrow_shared
    Parquet::parquet_shared
)

# Install plugInfo.json alongside the library
install(FILES src/plugInfo.json DESTINATION lib/resources)
