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

    pillow_pixels = np.asarray(Image.open(io.BytesIO(ours)).convert("RGB"))
    assert pillow_pixels.shape == (H, W, 3)
    assert np.abs(pillow_pixels.astype(int) - img.astype(int)).mean() < 3
    assert len(ours) < len(theirs)


def test_bad_size():
    with pytest.raises(ValueError):
        pyjpegli.encode(b"\x00" * 10, W, H)


@pytest.mark.parametrize("quality", [0, 101])
def test_bad_quality(quality):
    with pytest.raises(ValueError):
        pyjpegli.encode(gradient().tobytes(), W, H, quality=quality)


def test_signed_or_bool_buffer_rejected():
    with pytest.raises(ValueError):
        pyjpegli.encode(np.zeros((H, W, 3), dtype=np.int8), W, H)
    with pytest.raises(ValueError):
        pyjpegli.encode(np.zeros((H, W, 3), dtype=np.bool_), W, H)


def test_grayscale_decodes_to_rgb():
    buf = io.BytesIO()
    Image.new("L", (10, 20), 128).save(buf, format="JPEG")
    raw, w, h = pyjpegli.decode(buf.getvalue())
    assert (w, h) == (10, 20)
    assert len(raw) == w * h * 3
    assert abs(raw[0] - 128) < 3


def test_truncated_jpeg_raises():
    jpeg = pyjpegli.encode(gradient().tobytes(), W, H, quality=90)
    with pytest.raises(RuntimeError, match="corrupt"):
        pyjpegli.decode(jpeg[: len(jpeg) // 2])


def test_max_pixels():
    jpeg = pyjpegli.encode(gradient().tobytes(), W, H)
    with pytest.raises(RuntimeError, match="max_pixels"):
        pyjpegli.decode(jpeg, max_pixels=W * H - 1)
    _, w, h = pyjpegli.decode(jpeg, max_pixels=None)
    assert (w, h) == (W, H)


def test_decode_garbage():
    with pytest.raises(RuntimeError):
        pyjpegli.decode(b"not a jpeg at all")
