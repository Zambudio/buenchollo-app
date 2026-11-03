from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, features

from app.modules.submissions.domain.exceptions import InvalidImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_SIDE = 1600
WEBP_QUALITY = 82

# Backstop: Pillow solo lanza error por encima de 2x este valor; el límite real
# se comprueba explícitamente en process_image.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int


def _allowed_formats() -> set[str]:
    formats = {"JPEG", "PNG", "WEBP", "GIF"}
    if features.check("avif"):
        formats.add("AVIF")
    return formats


def process_image(data: bytes) -> ProcessedImage:
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in _allowed_formats():
                raise InvalidImageError()
            if probe.width * probe.height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("La imagen es demasiado grande")
            probe.verify()
        with Image.open(BytesIO(data)) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            image.load()
            has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            out = BytesIO()
            image.save(out, format="WEBP", quality=WEBP_QUALITY)
            return ProcessedImage(out.getvalue(), image.width, image.height)
    except InvalidImageError:
        raise
    except Image.DecompressionBombError as exc:
        raise InvalidImageError("La imagen es demasiado grande") from exc
    except Exception as exc:
        raise InvalidImageError() from exc
