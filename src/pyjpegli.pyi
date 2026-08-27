from typing import Optional, Tuple, Union

__version__: str

# Anything supporting the buffer protocol with C-contiguous uint8 data.
_Buffer = Union[bytes, bytearray, memoryview]

def encode(
    data: _Buffer, width: int, height: int, quality: int = 75
) -> bytes:
    """Encode packed RGB bytes (width*height*3) into a JPEG."""

def decode(
    data: _Buffer, max_pixels: Optional[int] = 178956970
) -> Tuple[bytes, int, int]:
    """Decode a JPEG into (rgb_bytes, width, height)."""
