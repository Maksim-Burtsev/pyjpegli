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

Wheels: Linux (x86_64, aarch64), macOS (arm64, x86_64) and Windows (AMD64),
CPython 3.9–3.14. No system dependencies — jpegli is compiled into the wheel.
An sdist is published too; building from it needs CMake and a C++17 compiler.

## Usage

```python
import pyjpegli

# encode: packed RGB bytes (width * height * 3) -> JPEG bytes
jpeg = pyjpegli.encode(rgb_bytes, width, height, quality=75)

# decode: JPEG bytes -> (packed RGB bytes, width, height)
rgb, width, height = pyjpegli.decode(jpeg)
```

`decode` raises `RuntimeError` on corrupt or truncated data, and refuses
images over `max_pixels` (default ~179 M, same as Pillow; pass
`max_pixels=None` to disable the ceiling).

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

Real photos (Kodak corpus, 24 images), visual quality matched by
[SSIMULACRA2](https://github.com/cloudinary/ssimulacra2), both codecs decoded
by Pillow:

![Same visual quality, fewer bits](https://raw.githubusercontent.com/Maksim-Burtsev/pyjpegli/713bab1/benchmarks/quality_size.svg)

| jpegli `quality` | visual quality (SSIMULACRA2) | size at equal visual quality |
|---|---|---|
| 75 | 72.5 | **−11.4%** |
| 85 | 78.9 | **−13.1%** |
| 95 | 88.2 | **−15.2%** |

- **9–15% smaller files at identical visual quality** (median per quality
  level, SSIMULACRA2-matched, ties resolved in libjpeg-turbo's favor)
- 10–17% smaller at the same `quality` setting
- 2.2× slower to encode than libjpeg-turbo (3.2 vs 1.5 ms/megapixel)

Methodology and full tables: [benchmarks/results.md](benchmarks/results.md).

## Limitations

Deliberately minimal for now: RGB only (no grayscale/CMYK), no control over
subsampling, progressive mode, or jpegli's distance-based quality. No
free-threaded (`cp314t`), musllinux or PyPy wheels. Open an issue if you need
any of these.

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
(highway, skcms, libjpeg-turbo headers) are BSD-style licensed; their license
texts ship inside every wheel (`pyjpegli-*.dist-info/licenses/`).
