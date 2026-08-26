# pyjpegli

[![PyPI](https://img.shields.io/pypi/v/pyjpegli.svg)](https://pypi.org/project/pyjpegli/)
[![CI](https://github.com/Maksim-Burtsev/pyjpegli/actions/workflows/wheels.yml/badge.svg)](https://github.com/Maksim-Burtsev/pyjpegli/actions/workflows/wheels.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/pyjpegli.svg)](https://pypi.org/project/pyjpegli/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)

Python bindings for [google/jpegli](https://github.com/google/jpegli) — a JPEG
encoder that produces noticeably smaller files than libjpeg-turbo at the same
visual quality, while staying 100% compatible with every JPEG decoder.

## Install

```bash
pip install pyjpegli
```

Wheels: Linux (x86_64, aarch64) and macOS (arm64, x86_64), CPython 3.9–3.13.
No system dependencies — jpegli is compiled into the wheel.

## Usage

```python
import pyjpegli

# encode: packed RGB bytes (width * height * 3) -> JPEG bytes
jpeg = pyjpegli.encode(rgb_bytes, width, height, quality=75)

# decode: JPEG bytes -> (packed RGB bytes, width, height)
rgb, width, height = pyjpegli.decode(jpeg)
```

`encode` accepts anything supporting the buffer protocol — `bytes`,
`bytearray`, `memoryview`, or a C-contiguous `uint8` NumPy array. NumPy is not
a dependency.

With Pillow:

```python
import numpy as np
from PIL import Image
import pyjpegli

img = np.asarray(Image.open("photo.png").convert("RGB"))
h, w, _ = img.shape
open("photo.jpg", "wb").write(pyjpegli.encode(img, w, h, quality=75))
```

## Why

Same input, same quality setting, encoded size (from the test suite's gradient
image, `quality=75`):

| Encoder | Size |
|---|---|
| Pillow / libjpeg-turbo | 3873 B |
| pyjpegli | 2980 B (−23%) |

Real-world photographic images typically shrink by 10–35%. Reproduce with your
own images before trusting any numbers — the gain depends heavily on content.

## Limitations

Deliberately minimal for 0.1: RGB only (no grayscale/CMYK), no control over
subsampling, progressive mode, or jpegli's distance-based quality. No Windows
wheels and no sdist yet (the sdist would not include the vendored submodules).
Open an issue if you need any of these.

## Contributing

Issues and PRs welcome. Build from a clone:

```bash
git submodule update --init --depth 1 third_party/jpegli
git -C third_party/jpegli submodule update --init --depth 1 \
  third_party/highway third_party/skcms third_party/libjpeg-turbo
pip install -e ".[test]" && pytest
```

## License

BSD-3-Clause (see [LICENSE](LICENSE)). Bundled jpegli and its dependencies
(highway, skcms, libjpeg-turbo headers) are BSD-style licensed; see
`third_party/jpegli/LICENSE`.
