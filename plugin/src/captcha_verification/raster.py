from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from captcha_verification.canonical import file_sha256
from captcha_verification.contracts import AssetRef


ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/x-portable-pixmap"}
MAX_PIXELS = 4_000_000


@dataclass(frozen=True)
class Component:
    pixels: tuple[tuple[int, int], ...]
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    @property
    def area(self) -> int:
        return len(self.pixels)

    @property
    def width(self) -> int:
        return self.max_x - self.min_x + 1

    @property
    def height(self) -> int:
        return self.max_y - self.min_y + 1

    @property
    def centroid(self) -> tuple[float, float]:
        return (
            sum(point[0] for point in self.pixels) / self.area,
            sum(point[1] for point in self.pixels) / self.area,
        )

    @property
    def fill_ratio(self) -> float:
        return self.area / (self.width * self.height)


@dataclass(frozen=True)
class Raster:
    image: object
    path: Path
    sha256: str
    width: int
    height: int
    media_type: str


def asset_path(asset: AssetRef) -> Path:
    parsed = urlparse(asset.uri)
    if parsed.scheme not in {"", "file"}:
        raise ValueError("reference runtime accepts file-backed local fixtures only")
    path = Path(unquote(parsed.path) if parsed.scheme == "file" else asset.uri).resolve()
    forbidden = {"labels", "server-labels", "answers", "metadata"}
    if forbidden.intersection(part.lower() for part in path.parts):
        raise ValueError("runtime cannot read label or answer paths")
    manifest_names = {"dataset-manifest.json", "fixture-manifest.json"}
    if path.suffix.lower() == ".json" or path.name.lower() in manifest_names:
        raise ValueError("runtime asset must resolve to raster bytes, not metadata")
    if path.suffix.lower() in {".svg", ".xml", ".html", ".htm"}:
        raise ValueError("raster input is required; SVG/XML/HTML is negative-eval-only")
    if not path.is_file():
        raise ValueError(f"fixture asset does not exist: {path}")
    return path


def load_raster(asset: AssetRef) -> Raster:
    if asset.media_type not in ALLOWED_MEDIA_TYPES:
        raise ValueError(f"unsupported raster media type: {asset.media_type}")
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[vision]") from exc
    path = asset_path(asset)
    observed_hash = file_sha256(path)
    if asset.sha256 not in {"auto", observed_hash}:
        raise ValueError("asset sha256 does not match file contents")
    with Image.open(path) as source:
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    if width * height > MAX_PIXELS:
        raise ValueError("raster exceeds reference runtime pixel limit")
    if width < 16 or height < 16:
        raise ValueError("raster has insufficient geometry")
    if asset.width_px and asset.width_px != width:
        raise ValueError("declared raster width does not match")
    if asset.height_px and asset.height_px != height:
        raise ValueError("declared raster height does not match")
    return Raster(image=image, path=path, sha256=observed_hash, width=width, height=height, media_type=asset.media_type)


def mask_components(mask: list[list[bool]], *, connectivity: int = 8) -> list[Component]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    visited: set[tuple[int, int]] = set()
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if connectivity == 8:
        neighbors += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    components: list[Component] = []
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or (x, y) in visited:
                continue
            queue = deque([(x, y)])
            visited.add((x, y))
            pixels: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                pixels.append((px, py))
                for dx, dy in neighbors:
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            components.append(
                Component(
                    pixels=tuple(pixels),
                    min_x=min(point[0] for point in pixels),
                    min_y=min(point[1] for point in pixels),
                    max_x=max(point[0] for point in pixels),
                    max_y=max(point[1] for point in pixels),
                )
            )
    return components


def red_mask(raster: Raster, threshold: int) -> list[list[bool]]:
    pixels = raster.image.load()
    return [
        [pixels[x, y][0] - max(pixels[x, y][1], pixels[x, y][2]) >= threshold for x in range(raster.width)]
        for y in range(raster.height)
    ]


def bright_mask(raster: Raster, threshold: int = 705) -> list[list[bool]]:
    pixels = raster.image.load()
    return [
        [sum(pixels[x, y]) >= threshold for x in range(raster.width)]
        for y in range(raster.height)
    ]
