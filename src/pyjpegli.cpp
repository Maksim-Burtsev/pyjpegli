#include <csetjmp>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <stdexcept>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "lib/jpegli/decode.h"
#include "lib/jpegli/encode.h"

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;

namespace {

struct ErrorMgr {
  jpeg_error_mgr base;
  jmp_buf env;
  char msg[JMSG_LENGTH_MAX];
};

void ErrorExit(j_common_ptr cinfo) {
  ErrorMgr* err = reinterpret_cast<ErrorMgr*>(cinfo->err);
  (*cinfo->err->format_message)(cinfo, err->msg);
  longjmp(err->env, 1);
}

// No non-trivial destructors live in the setjmp frames below: everything is
// raw pointers, so longjmp cannot skip a destructor.

bool EncodeRaw(const unsigned char* pixels, int width, int height, int quality,
               unsigned char** out, unsigned long* out_size, char* msg) {
  jpeg_compress_struct cinfo;
  ErrorMgr err;
  *out = nullptr;
  *out_size = 0;
  cinfo.err = jpegli_std_error(&err.base);
  err.base.error_exit = ErrorExit;
  if (setjmp(err.env)) {
    memcpy(msg, err.msg, JMSG_LENGTH_MAX);
    jpegli_destroy_compress(&cinfo);
    free(*out);
    *out = nullptr;
    return false;
  }
  jpegli_create_compress(&cinfo);
  jpegli_mem_dest(&cinfo, out, out_size);
  cinfo.image_width = static_cast<JDIMENSION>(width);
  cinfo.image_height = static_cast<JDIMENSION>(height);
  cinfo.input_components = 3;
  cinfo.in_color_space = JCS_RGB;
  jpegli_set_defaults(&cinfo);
  jpegli_set_quality(&cinfo, quality, TRUE);
  jpegli_start_compress(&cinfo, TRUE);
  const size_t stride = static_cast<size_t>(width) * 3;
  while (cinfo.next_scanline < cinfo.image_height) {
    JSAMPROW row = const_cast<JSAMPROW>(pixels + cinfo.next_scanline * stride);
    jpegli_write_scanlines(&cinfo, &row, 1);
  }
  jpegli_finish_compress(&cinfo);
  jpegli_destroy_compress(&cinfo);
  return true;
}

bool DecodeRaw(const unsigned char* data, unsigned long size,
               size_t max_pixels, unsigned char** out, size_t* out_size,
               int* width, int* height, char* msg) {
  jpeg_decompress_struct cinfo;
  ErrorMgr err;
  *out = nullptr;
  *out_size = 0;
  cinfo.err = jpegli_std_error(&err.base);
  err.base.error_exit = ErrorExit;
  if (setjmp(err.env)) {
    memcpy(msg, err.msg, JMSG_LENGTH_MAX);
    jpegli_destroy_decompress(&cinfo);
    free(*out);
    *out = nullptr;
    return false;
  }
  jpegli_create_decompress(&cinfo);
  jpegli_mem_src(&cinfo, data, size);
  jpegli_read_header(&cinfo, TRUE);
  cinfo.out_color_space = JCS_RGB;
  jpegli_start_decompress(&cinfo);
  *width = static_cast<int>(cinfo.output_width);
  *height = static_cast<int>(cinfo.output_height);
  const size_t pixels =
      static_cast<size_t>(*width) * static_cast<size_t>(*height);
  if (max_pixels != 0 && pixels > max_pixels) {
    snprintf(msg, JMSG_LENGTH_MAX, "image with %dx%d pixels exceeds max_pixels=%zu",
             *width, *height, max_pixels);
    jpegli_destroy_decompress(&cinfo);
    return false;
  }
  *out_size = pixels * 3;
  *out = static_cast<unsigned char*>(malloc(*out_size));
  if (*out == nullptr) {
    snprintf(msg, JMSG_LENGTH_MAX, "out of memory");
    jpegli_destroy_decompress(&cinfo);
    return false;
  }
  const size_t stride = static_cast<size_t>(*width) * 3;
  while (cinfo.output_scanline < cinfo.output_height) {
    JSAMPROW row = *out + cinfo.output_scanline * stride;
    if (jpegli_read_scanlines(&cinfo, &row, 1) != 1) {
      snprintf(msg, JMSG_LENGTH_MAX, "truncated JPEG data");
      jpegli_destroy_decompress(&cinfo);
      free(*out);
      *out = nullptr;
      return false;
    }
  }
  if (err.base.num_warnings > 0) {
    snprintf(msg, JMSG_LENGTH_MAX, "corrupt JPEG data (%ld decode warnings)",
             err.base.num_warnings);
    jpegli_destroy_decompress(&cinfo);
    free(*out);
    *out = nullptr;
    return false;
  }
  jpegli_finish_decompress(&cinfo);
  jpegli_destroy_decompress(&cinfo);
  return true;
}

// Rejects non-uint8 or strided buffers; we index the memory linearly.
size_t FlatBytes(const py::buffer_info& info) {
  if (info.itemsize != 1 ||
      (!info.format.empty() && info.format != "B" && info.format != "c")) {
    throw py::value_error("expected a buffer of unsigned 8-bit values, got '" +
                          info.format + "'");
  }
  size_t expected = 1;
  for (ssize_t i = info.ndim - 1; i >= 0; --i) {
    if (info.strides[i] != static_cast<ssize_t>(expected)) {
      throw py::value_error("expected a C-contiguous buffer");
    }
    expected *= static_cast<size_t>(info.shape[i]);
  }
  return static_cast<size_t>(info.size);
}

py::bytes Encode(py::buffer data, int width, int height, int quality) {
  if (width <= 0 || height <= 0) {
    throw py::value_error("width and height must be positive");
  }
  if (quality < 1 || quality > 100) {
    throw py::value_error("quality must be in 1..100");
  }
  py::buffer_info info = data.request();
  const size_t got = FlatBytes(info);
  const size_t need =
      static_cast<size_t>(width) * static_cast<size_t>(height) * 3;
  if (got != need) {
    throw py::value_error("data size " + std::to_string(got) +
                          " does not match width*height*3 = " +
                          std::to_string(need));
  }

  unsigned char* out = nullptr;
  unsigned long out_size = 0;
  char msg[JMSG_LENGTH_MAX] = {0};
  bool ok;
  {
    py::gil_scoped_release release;
    ok = EncodeRaw(static_cast<const unsigned char*>(info.ptr), width, height,
                   quality, &out, &out_size, msg);
  }
  std::unique_ptr<unsigned char, void (*)(void*)> owner(out, free);
  if (!ok) throw std::runtime_error(msg);
  return py::bytes(reinterpret_cast<const char*>(out), out_size);
}

py::tuple Decode(py::buffer data, std::optional<size_t> max_pixels) {
  py::buffer_info info = data.request();
  const size_t size = FlatBytes(info);

  unsigned char* out = nullptr;
  size_t out_size = 0;
  int width = 0, height = 0;
  char msg[JMSG_LENGTH_MAX] = {0};
  bool ok;
  {
    py::gil_scoped_release release;
    ok = DecodeRaw(static_cast<const unsigned char*>(info.ptr),
                   static_cast<unsigned long>(size), max_pixels.value_or(0),
                   &out, &out_size, &width, &height, msg);
  }
  std::unique_ptr<unsigned char, void (*)(void*)> owner(out, free);
  if (!ok) throw std::runtime_error(msg);
  return py::make_tuple(py::bytes(reinterpret_cast<const char*>(out), out_size),
                        width, height);
}

}  // namespace

PYBIND11_MODULE(pyjpegli, m) {
  m.doc() = "Python bindings for google/jpegli";
  m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);

  m.def("encode", &Encode, py::arg("data"), py::arg("width"), py::arg("height"),
        py::arg("quality") = 75,
        "Encode packed RGB bytes (width*height*3) into a JPEG.");

  // Same default ceiling as Pillow's MAX_IMAGE_PIXELS; None disables it.
  m.def("decode", &Decode, py::arg("data"),
        py::arg("max_pixels") = std::optional<size_t>(178956970),
        "Decode a JPEG into (rgb_bytes, width, height). Rejects corrupt data "
        "and images larger than max_pixels (None = unlimited).");
}
