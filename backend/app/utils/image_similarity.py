import io
from typing import Optional
from PIL import Image


def compute_image_dhash(image_bytes: bytes, hash_size: int = 8) -> Optional[int]:
    """
    Compute difference hash (dHash) for an image.
    Resizes image to (hash_size + 1, hash_size) in grayscale,
    and compares adjacent pixels.
    Returns an integer representing the 64-bit hash.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(img.getdata())
        diff = 0
        for row in range(hash_size):
            row_start = row * (hash_size + 1)
            for col in range(hash_size):
                left = pixels[row_start + col]
                right = pixels[row_start + col + 1]
                diff = (diff << 1) | (1 if left > right else 0)
        return diff
    except Exception:
        return None


def calculate_dhash_similarity(hash1: Optional[int], hash2: Optional[int], hash_size: int = 8) -> Optional[float]:
    """
    Calculate similarity between two dHashes as a float between 0.0 and 1.0.
    1.0 means identical visual layout.
    """
    if hash1 is None or hash2 is None:
        return None
    total_bits = hash_size * hash_size
    xor_val = hash1 ^ hash2
    hamming_dist = bin(xor_val).count("1")
    similarity = 1.0 - (hamming_dist / float(total_bits))
    return max(0.0, min(1.0, round(similarity, 4)))
