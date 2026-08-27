# pyjpegli benchmark — Kodak corpus

Date: 2026-08-27. pyjpegli 0.1.1, Pillow 12.3.0 (libjpeg-turbo), SSIMULACRA2: /opt/homebrew/Cellar/jpeg-xl/0.12.0/bin/ssimulacra2.

Corpus: Kodak True Color Suite, 24 photos, 768x512 (https://r0k.us/graphics/kodak/). Encoders: Pillow `save(quality=q)` with default subsampling; `pyjpegli.encode(..., quality=q)` with jpegli defaults. Metric computed between the original PNG and the JPEG decoded by Pillow (independent decoder for both codecs).

## Same quality knob (mode A)

| quality | libjpeg-turbo (mean B) | jpegli (mean B) | delta |
|---|---|---|---|
| 60 | 50,950 | 42,474 | -16.6% |
| 70 | 60,887 | 51,150 | -16.0% |
| 75 | 67,220 | 57,134 | -15.0% |
| 80 | 77,181 | 65,151 | -15.6% |
| 85 | 91,252 | 77,150 | -15.5% |
| 90 | 115,326 | 99,052 | -14.1% |
| 95 | 166,720 | 149,555 | -10.3% |

## Equal visual quality (mode B, SSIMULACRA2-matched)

For each image and jpegli quality, libjpeg-turbo's quality knob is binary-searched to the smallest q reaching the same SSIMULACRA2 score (conservative: favors turbo). Savings = size reduction at equal score.

| jpegli q | median SSIMULACRA2 | median savings | p25 | p75 | excluded |
|---|---|---|---|---|---|
| 60 | 64.5 | 13.3% | 10.0% | 17.5% | 0 |
| 70 | 69.8 | 12.5% | 8.5% | 17.1% | 0 |
| 75 | 72.5 | 11.4% | 7.8% | 16.2% | 0 |
| 80 | 75.6 | 9.5% | 6.6% | 14.9% | 0 |
| 85 | 78.9 | 13.1% | 8.3% | 15.5% | 0 |
| 90 | 83.2 | 12.4% | 9.7% | 18.9% | 0 |
| 95 | 88.2 | 15.2% | 10.2% | 20.9% | 0 |

Excluded = images where turbo at q=100 still scored below jpegli's score (no fair size comparison possible).

## Encode speed (q=75, median over corpus)

- libjpeg-turbo: 1.5 ms/megapixel
- jpegli: 3.2 ms/megapixel (2.2x slower)

Reproduce (from a clone): init the submodules (`git submodule update --init --depth 1 third_party/jpegli && git -C third_party/jpegli submodule update --init --depth 1 third_party/highway third_party/skcms third_party/libjpeg-turbo`), `pip install -e '.[bench]'` (needs CMake and a C++17 toolchain), install `ssimulacra2` (ships with Homebrew/apt `jpeg-xl` / `libjxl` tools), then `python benchmarks/bench.py`. Note: the run overwrites results.md and quality_size.svg in place.
