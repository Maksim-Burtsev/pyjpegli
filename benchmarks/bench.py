#!/usr/bin/env python3
"""Benchmark pyjpegli vs Pillow/libjpeg-turbo on a real-photo corpus.

Mode A: same quality knob -> mean encoded size per q.
Mode B: equal visual quality (SSIMULACRA2) -> size savings at matched score.
Also measures encode speed (ms per megapixel) at q=75.

Usage: python benchmarks/bench.py [--corpus DIR] [--ssimulacra2 PATH] [--out DIR]
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import io
import shutil
import statistics
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

import pyjpegli

KODAK = [f"https://r0k.us/graphics/kodak/kodak/kodim{i:02d}.png" for i in range(1, 25)]
QUALITIES = [60, 70, 75, 80, 85, 90, 95]
BISECT_TOL = 0.25


def load_corpus(corpus_dir: str | None) -> list[tuple[str, Path, np.ndarray]]:
    if corpus_dir:
        paths = sorted(p for p in Path(corpus_dir).iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif"})
    else:
        cache = Path(__file__).parent / "corpus"
        cache.mkdir(exist_ok=True)
        for url in KODAK:
            dst = cache / url.rsplit("/", 1)[1]
            if not dst.exists():
                print(f"downloading {dst.name}...")
                urllib.request.urlretrieve(url, dst)
        paths = sorted(cache.glob("kodim*.png"))
    return [(p.name, p, np.asarray(Image.open(p).convert("RGB"))) for p in paths]


def turbo_bytes(img: np.ndarray, q: int) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=q)
    return buf.getvalue()


def jpegli_bytes(img: np.ndarray, q: int) -> bytes:
    h, w, _ = img.shape
    return pyjpegli.encode(np.ascontiguousarray(img), w, h, quality=q)


class Metric:
    """SSIMULACRA2 via the libjxl CLI tool; PNG on both sides (Pillow decode)."""

    def __init__(self, tool: str, tmp: Path):
        self.tool = tool
        self.tmp = tmp
        self.cache: dict[tuple[str, str, int], float] = {}

    def score(self, name: str, orig_png: Path, codec: str, q: int, jpg: bytes) -> float:
        key = (name, codec, q)
        if key not in self.cache:
            dist = self.tmp / f"{name}-{codec}-{q}.png"
            Image.open(io.BytesIO(jpg)).save(dist)  # independent decoder
            out = subprocess.run([self.tool, str(orig_png), str(dist)],
                                 capture_output=True, text=True, check=True, timeout=120)
            dist.unlink()
            self.cache[key] = float(out.stdout.strip())
        return self.cache[key]


def turbo_match(metric: Metric, name: str, orig_png: Path, img: np.ndarray,
                target: float) -> bytes | None:
    """Smallest turbo q whose SSIMULACRA2 >= target (conservative: favors turbo).

    Returns None when even q=100 cannot reach the target.
    """
    lo, hi = 30, 100
    best = None
    while lo <= hi:
        q = (lo + hi) // 2
        jpg = turbo_bytes(img, q)
        s = metric.score(name, orig_png, "turbo", q, jpg)
        if abs(s - target) <= BISECT_TOL:
            return jpg
        if s < target:
            lo = q + 1
        else:
            best = jpg
            hi = q - 1
    return best


def encode_speed_ms_per_mp(fn, img: np.ndarray, q: int = 75, repeats: int = 3) -> float:
    mp = img.shape[0] * img.shape[1] / 1e6
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(img, q)
        times.append(time.perf_counter() - t0)
    return min(times) * 1000 / mp


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--ssimulacra2", default=shutil.which("ssimulacra2"))
    ap.add_argument("--out", default=str(Path(__file__).parent))
    args = ap.parse_args()

    out_dir = Path(args.out)
    corpus = load_corpus(args.corpus)
    print(f"corpus: {len(corpus)} images")

    # Mode A: same quality knob.
    mode_a = []  # (q, mean_turbo, mean_jpegli)
    sizes: dict[tuple[str, str, int], int] = {}
    jpgs: dict[tuple[str, int], bytes] = {}
    for q in QUALITIES:
        t_sizes, j_sizes = [], []
        for name, _, img in corpus:
            t = turbo_bytes(img, q)
            j = jpegli_bytes(img, q)
            jpgs[(name, q)] = j
            sizes[(name, "turbo", q)] = len(t)
            sizes[(name, "jpegli", q)] = len(j)
            t_sizes.append(len(t))
            j_sizes.append(len(j))
        mode_a.append((q, statistics.mean(t_sizes), statistics.mean(j_sizes)))
        print(f"mode A q={q}: turbo {mode_a[-1][1]:.0f} B, jpegli {mode_a[-1][2]:.0f} B")

    # Speed at q=75.
    t_speed = statistics.median(encode_speed_ms_per_mp(turbo_bytes, img) for _, _, img in corpus)
    j_speed = statistics.median(encode_speed_ms_per_mp(jpegli_bytes, img) for _, _, img in corpus)
    print(f"speed: turbo {t_speed:.1f} ms/MP, jpegli {j_speed:.1f} ms/MP")

    # Mode B: equal visual quality.
    mode_b = []   # (q, median_score, median_saving, p25, p75, n_excluded)
    curves = {"jpegli": [], "libjpeg-turbo": []}
    if not args.ssimulacra2:
        print("WARNING: ssimulacra2 not found; mode B and the chart are skipped")
    else:
        with tempfile.TemporaryDirectory() as td:
            metric = Metric(args.ssimulacra2, Path(td))
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                for q in QUALITIES:
                    def one(item, q=q):
                        name, orig_png, img = item
                        j = jpgs[(name, q)]
                        target = metric.score(name, orig_png, "jpegli", q, j)
                        t = turbo_match(metric, name, orig_png, img, target)
                        return target, (1 - len(j) / len(t)) if t else None
                    results = list(pool.map(one, corpus))
                    scores = [s for s, _ in results]
                    savings = [sv for _, sv in results if sv is not None]
                    excluded = sum(1 for _, sv in results if sv is None)
                    qs = statistics.quantiles(savings, n=4)
                    mode_b.append((q, statistics.median(scores), statistics.median(savings),
                                   qs[0], qs[2], excluded))
                    print(f"mode B q={q}: score {mode_b[-1][1]:.1f}, "
                          f"median saving {mode_b[-1][2]:.1%} (excl {excluded})")
                # Curves for the chart: mean bpp vs mean score per q, both codecs.
                for q in QUALITIES:
                    for codec, curve in (("jpegli", curves["jpegli"]),
                                         ("turbo", curves["libjpeg-turbo"])):
                        bpps, scs = [], []
                        for name, orig_png, img in corpus:
                            jpg = (jpgs[(name, q)] if codec == "jpegli"
                                   else turbo_bytes(img, q))
                            bpps.append(len(jpg) * 8 / (img.shape[0] * img.shape[1]))
                            scs.append(metric.score(name, orig_png, codec, q, jpg))
                        curve.append((statistics.mean(bpps), statistics.mean(scs)))
        plot(curves, out_dir / "quality_size.svg")

    write_report(out_dir / "results.md", corpus, mode_a, mode_b,
                 t_speed, j_speed, args.ssimulacra2)
    print(f"wrote {out_dir}/results.md")


def plot(curves: dict, out_svg: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.2), facecolor="white")
    styles = {"jpegli": dict(color="#0b7285", lw=2.4, zorder=3),
              "libjpeg-turbo": dict(color="#adb5bd", lw=1.8, zorder=2)}
    for name, pts in curves.items():
        xs, ys = zip(*sorted(pts))
        ax.plot(xs, ys, marker="o", ms=4.5, label=name, **styles[name])
    ax.set_xlabel("bits per pixel (average, Kodak corpus)")
    ax.set_ylabel("SSIMULACRA2  (higher is better)")
    ax.set_title("Same visual quality, fewer bits", fontsize=13, pad=10)
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.25, lw=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_facecolor("white")
    fig.savefig(out_svg, bbox_inches="tight", facecolor="white")


def write_report(path: Path, corpus, mode_a, mode_b, t_speed, j_speed, tool) -> None:
    import PIL

    tool_src = Path(tool).resolve() if tool else None
    lines = [
        "# pyjpegli benchmark — Kodak corpus",
        "",
        f"Date: {datetime.date.today().isoformat()}. "
        f"pyjpegli {pyjpegli.__version__}, Pillow {PIL.__version__} (libjpeg-turbo), "
        f"SSIMULACRA2: {tool_src if tool_src else 'not available'}.",
        "",
        "Corpus: Kodak True Color Suite, 24 photos, 768x512 "
        "(https://r0k.us/graphics/kodak/). Encoders: Pillow `save(quality=q)` with "
        "default subsampling; `pyjpegli.encode(..., quality=q)` with jpegli defaults. "
        "Metric computed between the original PNG and the JPEG decoded by Pillow "
        "(independent decoder for both codecs).",
        "",
        "## Same quality knob (mode A)",
        "",
        "| quality | libjpeg-turbo (mean B) | jpegli (mean B) | delta |",
        "|---|---|---|---|",
    ]
    for q, t, j in mode_a:
        lines.append(f"| {q} | {t:,.0f} | {j:,.0f} | {(j - t) / t:+.1%} |")
    if mode_b:
        lines += [
            "",
            "## Equal visual quality (mode B, SSIMULACRA2-matched)",
            "",
            "For each image and jpegli quality, libjpeg-turbo's quality knob is "
            "binary-searched to the smallest q reaching the same SSIMULACRA2 score "
            "(conservative: favors turbo). Savings = size reduction at equal score.",
            "",
            "| jpegli q | median SSIMULACRA2 | median savings | p25 | p75 | excluded |",
            "|---|---|---|---|---|---|",
        ]
        for q, sc, med, p25, p75, ex in mode_b:
            lines.append(f"| {q} | {sc:.1f} | {med:.1%} | {p25:.1%} | {p75:.1%} | {ex} |")
        lines += [
            "",
            "Excluded = images where turbo at q=100 still scored below jpegli's "
            "score (no fair size comparison possible).",
        ]
    lines += [
        "",
        "## Encode speed (q=75, median over corpus)",
        "",
        f"- libjpeg-turbo: {t_speed:.1f} ms/megapixel",
        f"- jpegli: {j_speed:.1f} ms/megapixel ({j_speed / t_speed:.1f}x slower)",
        "",
        "Reproduce: `pip install 'pyjpegli[bench]'` (or `pip install -e '.[bench]'`), "
        "install `ssimulacra2` (ships with Homebrew/apt `jpeg-xl` / `libjxl` tools), "
        "then `python benchmarks/bench.py`.",
    ]
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
