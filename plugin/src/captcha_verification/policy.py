from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from captcha_verification.contracts import AssetRef, AuthorizationRecord


def resolve_local_asset(asset: AssetRef, *, roots: tuple[Path, ...]) -> Path:
    """Resolve a raster only inside an explicitly owned fixture root."""
    parsed = urlparse(asset.uri)
    if parsed.scheme not in {"", "file"} or parsed.netloc:
        raise PermissionError("only local file assets are allowed")
    candidate = Path(unquote(parsed.path) if parsed.scheme == "file" else asset.uri)
    path = candidate.resolve(strict=True)
    allowed = [root.resolve(strict=True) for root in roots]
    if not any(path.is_relative_to(root) for root in allowed):
        raise PermissionError("asset is outside approved fixture roots")
    if path.suffix.lower() in {".json", ".svg", ".xml", ".html", ".htm"}:
        raise PermissionError("metadata and markup are not raster inputs")
    if any(part.lower() in {"labels", "server-labels", "answers", "metadata"} for part in path.parts):
        raise PermissionError("label and metadata paths are not solver inputs")
    return path


def require_authorization(
    authorization: AuthorizationRecord,
    *,
    host: str,
    route: str,
    method: str,
    action: str,
) -> None:
    if not authorization.allows(host=host, route=route, method=method, action=action):
        raise PermissionError("authorization scope does not allow this operation")
    if authorization.production_allowed:
        raise PermissionError("reference runtime cannot execute production targets")
