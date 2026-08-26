cmake_minimum_required(VERSION 3.24)
project(pyjpegli LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Build only the static jpegli core: no tools, tests, docs, or extra codecs.
foreach(_opt
    BUILD_TESTING BUILD_SHARED_LIBS
    JPEGLI_ENABLE_TOOLS JPEGLI_ENABLE_DEVTOOLS JPEGLI_ENABLE_FUZZERS
    JPEGLI_ENABLE_BENCHMARK JPEGLI_ENABLE_DOXYGEN JPEGLI_ENABLE_MANPAGES
    JPEGLI_ENABLE_JNI JPEGLI_ENABLE_SJPEG JPEGLI_ENABLE_OPENEXR
    JPEGLI_ENABLE_TCMALLOC JPEGLI_ENABLE_JPEGLI_LIBJPEG
    JPEGLI_TEST_TOOLS JPEGLI_BUNDLE_LIBPNG
    HWY_ENABLE_TESTS HWY_ENABLE_EXAMPLES HWY_ENABLE_CONTRIB HWY_ENABLE_INSTALL)
  set(${_opt} OFF CACHE BOOL "" FORCE)
endforeach()
# skcms is the colour-management backend; keeping it on avoids needing lcms2.
set(JPEGLI_ENABLE_SKCMS ON CACHE BOOL "" FORCE)

set(JPEGLI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/jpegli")
if(NOT EXISTS "${JPEGLI_DIR}/CMakeLists.txt")
  message(FATAL_ERROR "third_party/jpegli is empty: run git submodule update --init")
endif()
add_subdirectory("${JPEGLI_DIR}" EXCLUDE_FROM_ALL)

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(pyjpegli src/pyjpegli.cpp)
target_link_libraries(pyjpegli PRIVATE jpegli-static)
# jpegli headers are included as "lib/jpegli/encode.h", relative to its source root.
target_include_directories(pyjpegli PRIVATE "${JPEGLI_DIR}")
target_compile_definitions(pyjpegli PRIVATE VERSION_INFO=${SKBUILD_PROJECT_VERSION})

install(TARGETS pyjpegli DESTINATION .)
