#include <pybind11/pybind11.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;

PYBIND11_MODULE(pyjpegli, m) {
  m.doc() = "Python bindings for google/jpegli";
  m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
}
