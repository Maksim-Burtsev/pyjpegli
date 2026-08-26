import io

import numpy as np
import pytest
from PIL import Image

import pyjpegli

W, H = 256, 192


def gradient() -> np.ndarray:
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = x / W * 255
    g = y / H * 255
    b = (x / W + y / H) / 2 * 255
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def test_roundtrip():
    img = gradient()
    jpeg = pyjpegli.encode(img.tobytes(), W, H, quality=90)
    assert jpeg[:2] == b"\xff\xd8"

    raw, w, h = pyjpegli.decode(jpeg)
    assert (w, h) == (W, H)

    back = np.frombuffer(raw, dtype=np.uint8).reshape(H, W, 3)
    assert np.abs(back.astype(int) - img.astype(int)).mean() < 3


def test_accepts_numpy_and_bytes_alike():
    img = gradient()
    assert pyjpegli.encode(img, W, H) == pyjpegli.encode(img.tobytes(), W, H)


def test_decodable_by_pillow_and_smaller_than_pillow():
    img = gradient()
    ours = pyjpegli.encode(img.tobytes(), W, H, quality=75)

    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=75, subsampling=0)
    theirs = buf.getvalue()

    assert Image.open(io.BytesIO(ours)).size == (W, H)
    assert len(ours) < len(theirs)


def test_bad_size():
    with pytest.raises(ValueError):
        pyjpegli.encode(b"\x00" * 10, W, H)


def test_bad_quality():
    with pytest.raises(ValueError):
        pyjpegli.encode(gradient().tobytes(), W, H, quality=0)


def test_decode_garbage():
    with pytest.raises(RuntimeError):
        pyjpegli.decode(b"not a jpeg at all")
