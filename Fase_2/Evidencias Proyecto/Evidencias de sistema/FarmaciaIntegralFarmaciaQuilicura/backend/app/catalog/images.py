"""Imagen principal local: limite de bytes/pixeles y salida JPEG sin metadatos."""

import logging
import os
import re
import warnings
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2] / "media" / "products"
logger = logging.getLogger(__name__)


class ProductImages:
    def __init__(self, directory: Path | None = None):
        self.directory = Path(
            directory or os.environ.get("SIGFQ_PRODUCT_MEDIA_DIR", DEFAULT_DIRECTORY)
        )

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}\.jpg", key):
            raise HTTPException(404, "Imagen no disponible.")
        return self.directory / key

    def save(self, data: bytes) -> str:
        if not data or len(data) > MAX_BYTES:
            raise HTTPException(413, "La imagen debe pesar entre 1 byte y 5 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(
                    BytesIO(data), formats=["JPEG", "PNG", "WEBP"]
                ) as source:
                    if source.width * source.height > MAX_PIXELS:
                        raise HTTPException(413, "La imagen supera los 20 megapixeles.")
                    if getattr(source, "n_frames", 1) != 1:
                        raise HTTPException(
                            415, "Selecciona una imagen fija, sin animacion."
                        )
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    oriented.thumbnail((1600, 1600))
                    rgba = oriented.convert("RGBA")
                    # Imagen nueva: no copia EXIF, comentarios ni datos del archivo original.
                    clean = Image.new("RGB", rgba.size, "white")
                    clean.paste(rgba, mask=rgba.getchannel("A"))
                    output = BytesIO()
                    clean.save(output, "JPEG", quality=85)
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise HTTPException(
                415, "Archivo no valido. Usa una imagen JPG, PNG o WebP."
            ) from exc
        self.directory.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex + ".jpg"
        path = self.path(key)
        try:
            with path.open("xb") as file:
                file.write(output.getvalue())
        except OSError:
            self.remove(key)
            raise
        return key

    def remove(self, key: str | None):
        if key:
            try:
                self.path(key).unlink(missing_ok=True)
            except OSError:
                logger.warning("No se pudo retirar una imagen anterior del catalogo.")

    def read(self, key: str | None) -> bytes:
        if not key:
            raise HTTPException(404, "El producto no tiene imagen.")
        try:
            return self.path(key).read_bytes()
        except FileNotFoundError as exc:
            raise HTTPException(404, "Imagen no disponible.") from exc
