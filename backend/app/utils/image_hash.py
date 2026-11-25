"""
Perceptual image hashing (dHash) for the optional image-similarity
signal in duplicate detection.

dHash shrinks the image to 9x8 greyscale and records, for each pixel,
whether it is brighter than its right-hand neighbour: 64 bits. Two
photos of the same scene (even resized or recompressed) differ in few
bits; unrelated photos differ in roughly half of them.

This is a cheap similarity hint, not proof of identity: different
angles or lighting of the same pothole can score low, so the duplicate
service records the score but never uses it to veto a location match.
"""
from io import BytesIO
from typing import Optional

from PIL import Image, UnidentifiedImageError

HASH_BITS = 64


def dhash(image_bytes: bytes) -> Optional[str]:
    """Returns a 16-char hex hash, or None if the bytes aren't a decodable image."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("L").resize((9, 8), Image.LANCZOS)
    except (UnidentifiedImageError, OSError):
        return None

    pixels = list(image.getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            value = (value << 1) | (1 if left > right else 0)
    return f"{value:016x}"


def similarity(hash_a: Optional[str], hash_b: Optional[str]) -> Optional[float]:
    """0.0 (completely different) .. 1.0 (identical); None if either hash is missing."""
    if not hash_a or not hash_b:
        return None
    distance = bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")
    return round(1 - distance / HASH_BITS, 3)
