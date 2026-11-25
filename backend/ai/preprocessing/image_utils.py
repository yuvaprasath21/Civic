from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from ai.inference.base import AIProviderError

TARGET_MAX_DIMENSION = 640


@dataclass
class DecodedImage:
    image: Image.Image
    original_width: int
    original_height: int


def decode_and_normalize(image_bytes: bytes) -> DecodedImage:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise AIProviderError("Could not decode image for analysis.") from exc

    original_width, original_height = image.size
    longest_edge = max(original_width, original_height)

    if longest_edge > TARGET_MAX_DIMENSION:
        scale = TARGET_MAX_DIMENSION / longest_edge
        new_size = (max(1, int(original_width * scale)), max(1, int(original_height * scale)))
        image = image.convert("RGB").resize(new_size, Image.LANCZOS)
    else:
        image = image.convert("RGB")

    return DecodedImage(image=image, original_width=original_width, original_height=original_height)
