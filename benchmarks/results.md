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
| 60 | 64.5 | 12.7% | 8.9% | 16.9% | 0 |
| 70 | 69.8 | 11.7% | 8.3% | 16.9% | 0 |
| 75 | 72.5 | 10.5% | 7.3% | 15.7% | 0 |
| 80 | 75.6 | 9.5% | 6.1% | 14.4% | 0 |
| 85 | 78.9 | 9.6% | 7.8% | 14.8% | 0 |
| 90 | 83.2 | 12.4% | 7.9% | 15.5% | 0 |
| 95 | 88.2 | 10.4% | 7.7% | 14.7% | 0 |

Excluded = images where turbo at q=100 still scored below jpegli's score (no fair size comparison possible).

## Encode speed (q=75, median over corpus)

- libjpeg-turbo: 2.1 ms/megapixel
- jpegli: 3.3 ms/megapixel (1.6x slower)

Reproduce: `pip install 'pyjpegli[bench]'` (or `pip install -e '.[bench]'`), install `ssimulacra2` (ships with Homebrew/apt `jpeg-xl` / `libjxl` tools), then `python benchmarks/bench.py`.
