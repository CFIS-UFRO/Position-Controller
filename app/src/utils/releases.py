"""Release creation helpers and GitHub-based application updates."""

import hashlib
import html
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

from src.config import (
    RELEASE_ARCHIVE_PREFIX,
    RELEASE_HTTP_USER_AGENT,
    RELEASE_REPOSITORY_NAME,
)
from src.utils.logging import logger
from src.utils.paths import get_project_dir_path, get_pyproject_file_path
from src.utils.tmp import create_file, get_tmp_file_path

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------
GITHUB_LATEST_RELEASE_API_URL = (
    f"https://api.github.com/repos/{RELEASE_REPOSITORY_NAME}/releases/latest"
)
SEMANTIC_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PYPROJECT_VERSION_RE = re.compile(
    r'(?m)^(?P<prefix>version\s*=\s*")(?P<version>\d+\.\d+\.\d+)(?P<suffix>"\s*)$'
)
UV_LOCK_PROJECT_VERSION_RE = re.compile(
    r'(?ms)^(?P<prefix>\[\[package\]\]\nname\s*=\s*"position-controller"\nversion\s*=\s*")'
    r'(?P<version>\d+\.\d+\.\d+)'
    r'(?P<suffix>"\s*)$'
)

# --------------------------------------------------------------------------------------------------
# Data models
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ReleaseAsset:
    """GitHub release asset download information."""

    name: str
    download_url: str
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ReleaseUpdate:
    """Resolved update metadata for the latest published release."""

    current_version: str
    latest_version: str
    archive_sha256: str
    metadata_asset: ReleaseAsset
    archive_asset: ReleaseAsset
    releases: list[dict[str, object]]

    @property
    def is_update_available(self) -> bool:
        """Return whether the published release is newer than the installed version."""
        return is_version_newer(self.latest_version, self.current_version)

# --------------------------------------------------------------------------------------------------
# Update check worker
# --------------------------------------------------------------------------------------------------
class _ReleaseUpdateWorker(QObject):
    """Resolve the latest release without blocking the Qt event loop."""

    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    @Slot()
    def run(self) -> None:
        try:
            release_update = get_latest_release_update()
        except Exception as exc:
            logger.exception("Could not check for updates")
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(release_update)
        finally:
            self.finished.emit()
# --------------------------------------------------------------------------------------------------
class ReleaseUpdateChecker(QObject):
    """Manage asynchronous release checks and their worker-thread lifecycle."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _ReleaseUpdateWorker | None = None

    @property
    def is_running(self) -> bool:
        """Return whether a release check is currently running."""
        return self._thread is not None

    def start(self) -> bool:
        """Start a release check and return whether it was started."""
        if self.is_running:
            return False
        thread = QThread(self)
        worker = _ReleaseUpdateWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(
            self._handle_success,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.failed.connect(
            self._handle_failure,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.destroyed.connect(self._finish)
        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    @Slot(object)
    def _handle_success(self, release_update: object) -> None:
        self.succeeded.emit(release_update)

    @Slot(str)
    def _handle_failure(self, error_message: str) -> None:
        self.failed.emit(error_message)

    @Slot()
    def _finish(self) -> None:
        self._thread = None
        self._worker = None

# --------------------------------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------------------------------
def increment_version(version: str, update_type: str) -> str:
    """Increment a semantic version using major, minor, or bugfix update types."""
    normalized_update_type = update_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_update_type not in {"major", "minor", "bugfix"}:
        raise ValueError("Update type must be major, minor, or bugfix.")
    major, minor, bugfix = parse_semantic_version(version)
    if normalized_update_type == "major":
        return f"{major + 1}.0.0"
    if normalized_update_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{bugfix + 1}"
# --------------------------------------------------------------------------------------------------
def parse_semantic_version(version: str) -> tuple[int, int, int]:
    """Parse a three-part semantic version into a comparable tuple."""
    if SEMANTIC_VERSION_RE.fullmatch(version) is None:
        raise ValueError(f"Invalid semantic version: {version}")
    major, minor, bugfix = version.split(".")
    return int(major), int(minor), int(bugfix)
# --------------------------------------------------------------------------------------------------
def is_version_newer(candidate_version: str, current_version: str) -> bool:
    """Return whether the candidate version is newer than the current version."""
    return parse_semantic_version(candidate_version) > parse_semantic_version(current_version)
# --------------------------------------------------------------------------------------------------
def get_pyproject_version(pyproject_file_path: Path) -> str:
    """Read the project version from pyproject.toml."""
    content = pyproject_file_path.read_text(encoding="utf-8")
    match = PYPROJECT_VERSION_RE.search(content)
    if match is None:
        raise ValueError(f"Could not find a semantic version in {pyproject_file_path}.")
    return match.group("version")
# --------------------------------------------------------------------------------------------------
def update_pyproject_version(pyproject_file_path: Path, uv_lock_file_path: Path, update_type: str) -> str:
    """Increment and write the project version in pyproject.toml and uv.lock."""
    current_version = get_pyproject_version(pyproject_file_path)
    new_version = increment_version(current_version, update_type)
    file_updates = []
    for file_path, version_re in (
        (pyproject_file_path, PYPROJECT_VERSION_RE),
        (uv_lock_file_path, UV_LOCK_PROJECT_VERSION_RE),
    ):
        file_updates.append((file_path, _get_updated_version_content(file_path, version_re, new_version)))
    for file_path, updated_content in file_updates:
        file_path.write_text(updated_content, encoding="utf-8")
    return new_version
# --------------------------------------------------------------------------------------------------
def _get_updated_version_content(
    file_path: Path,
    version_re: re.Pattern[str],
    new_version: str,
) -> str:
    content = file_path.read_text(encoding="utf-8")
    if version_re.search(content) is None:
        raise ValueError(f"Could not find a semantic version in {file_path}.")
    return version_re.sub(rf"\g<prefix>{new_version}\g<suffix>", content, count=1)

# --------------------------------------------------------------------------------------------------
# Release files
# --------------------------------------------------------------------------------------------------
def get_release_file_stem(version: str) -> str:
    """Return the release file name without an extension."""
    parse_semantic_version(version)
    return f"{RELEASE_ARCHIVE_PREFIX}_{version}"
# --------------------------------------------------------------------------------------------------
def get_git_managed_file_paths(project_dir_path: Path) -> list[Path]:
    """Return tracked and untracked non-ignored project files using Git exclude rules."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=project_dir_path,
        check=True,
        capture_output=True,
        text=True,
    )
    file_paths = []
    for line in result.stdout.splitlines():
        relative_file_path = Path(line)
        if _is_hidden_path(relative_file_path):
            continue
        absolute_file_path = project_dir_path / relative_file_path
        if absolute_file_path.is_file():
            file_paths.append(absolute_file_path)
    return sorted(file_paths, key=lambda path: path.as_posix())
# --------------------------------------------------------------------------------------------------
def compress_paths(source_dir_path: Path, file_paths: list[Path], output_file_path: Path) -> Path:
    """Create a maximum-compression zip archive from project-relative paths."""
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_file_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for file_path in file_paths:
            archive.write(file_path, arcname=file_path.relative_to(source_dir_path).as_posix())
    return output_file_path
# --------------------------------------------------------------------------------------------------
def calculate_file_sha256(file_path: Path) -> str:
    """Return the lowercase SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
# --------------------------------------------------------------------------------------------------
def write_release_metadata(
    output_relative_path: str,
    version: str,
    archive_sha256: str,
    releases: list[dict[str, object]],
) -> Path:
    """Write updater metadata as JSON under the project temporary directory."""
    parse_semantic_version(version)
    if SHA256_RE.fullmatch(archive_sha256) is None:
        raise ValueError("Release archive SHA-256 is invalid.")
    metadata = {
        "version": version,
        "archive_sha256": archive_sha256,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "releases": releases,
    }
    return create_file(output_relative_path, json.dumps(metadata, indent=2) + "\n")
# --------------------------------------------------------------------------------------------------
def get_release_entries(releases_file_path: Path) -> list[dict[str, object]]:
    """Return release entries from the project release-history file."""
    return _read_releases_data(releases_file_path)["releases"]
# --------------------------------------------------------------------------------------------------
def append_release_entry(releases_file_path: Path, version: str, changes: list[str]) -> Path:
    """Append a release entry to the project release-history file."""
    parse_semantic_version(version)
    releases_data = _read_releases_data(releases_file_path)
    releases_data["releases"].append(
        {
            "version": version,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "changes": changes,
        }
    )
    releases_file_path.write_text(json.dumps(releases_data, indent=2) + "\n", encoding="utf-8")
    return releases_file_path

# --------------------------------------------------------------------------------------------------
# Application updates
# --------------------------------------------------------------------------------------------------
def get_latest_release_update() -> ReleaseUpdate:
    """Download the latest metadata asset and resolve available update information."""
    current_version = get_pyproject_version(get_pyproject_file_path())
    logger.info(f"Checking for updates. Current version: {current_version}")
    release_data = _read_json_url(GITHUB_LATEST_RELEASE_API_URL)
    metadata_asset = _get_release_asset(release_data, ".json")
    archive_asset = _get_release_asset(release_data, ".zip")
    metadata_file_path = download_release_asset(metadata_asset)
    metadata = _read_release_metadata(metadata_file_path)
    latest_version = _get_release_metadata_version(metadata)
    archive_sha256 = _get_release_metadata_archive_sha256(metadata)
    releases = _get_release_metadata_entries(metadata)
    logger.info(f"Latest published version: {latest_version}")
    return ReleaseUpdate(
        current_version=current_version,
        latest_version=latest_version,
        archive_sha256=archive_sha256,
        metadata_asset=metadata_asset,
        archive_asset=archive_asset,
        releases=releases,
    )
# --------------------------------------------------------------------------------------------------
def download_release_asset(asset: ReleaseAsset) -> Path:
    """Download a release asset into the application temporary directory."""
    output_file_path = get_tmp_file_path(asset.name)
    request = Request(
        asset.download_url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": RELEASE_HTTP_USER_AGENT,
        },
    )
    logger.info(f"Downloading release asset: {asset.name}")
    try:
        with urlopen(request, timeout=120) as response, output_file_path.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not download release asset: {asset.name}") from exc
    return output_file_path
# --------------------------------------------------------------------------------------------------
def install_release_update(release_update: ReleaseUpdate) -> Path:
    """Download, verify, and extract the selected update into the project root."""
    logger.info(
        f"Installing release update: {release_update.current_version} -> "
        f"{release_update.latest_version}"
    )
    archive_file_path = download_release_asset(release_update.archive_asset)
    actual_sha256 = calculate_file_sha256(archive_file_path)
    if actual_sha256 != release_update.archive_sha256:
        raise ValueError("Downloaded release archive failed SHA-256 verification.")
    extract_release_archive(archive_file_path, get_project_dir_path())
    logger.info(f"Installed release update: {release_update.latest_version}")
    return archive_file_path
# --------------------------------------------------------------------------------------------------
def extract_release_archive(archive_file_path: Path, destination_dir_path: Path) -> None:
    """Extract an update archive with path-traversal protection."""
    destination_dir_path.mkdir(parents=True, exist_ok=True)
    destination_root = destination_dir_path.resolve()
    logger.info(f"Extracting release archive: {archive_file_path} -> {destination_root}")
    try:
        with zipfile.ZipFile(archive_file_path, mode="r") as archive:
            for member in archive.infolist():
                target_path = (destination_root / member.filename).resolve()
                if target_path != destination_root and destination_root not in target_path.parents:
                    raise ValueError(f"Unsafe archive path: {member.filename}")
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, mode="r") as source_file, target_path.open("wb") as output_file:
                    shutil.copyfileobj(source_file, output_file)
                permissions = member.external_attr >> 16
                if permissions:
                    target_path.chmod(permissions)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid release archive: {archive_file_path}") from exc
# --------------------------------------------------------------------------------------------------
def format_release_entries_html(releases: list[dict[str, object]]) -> str:
    """Format release entries as a small HTML document."""
    if not releases:
        return "<!doctype html><html><body><p>No release notes available.</p></body></html>"
    parts = ["<!doctype html>", "<html>", "<body>"]
    for release in reversed(releases):
        version = html.escape(str(release.get("version", "Unknown")))
        created_at_local = html.escape(_format_release_datetime_local(release.get("created_at_utc")))
        changes = release.get("changes", [])
        parts.append(f"<h2>Version {version}</h2>")
        if created_at_local:
            parts.append(f"<p><code>{created_at_local}</code></p>")
        if isinstance(changes, list) and changes:
            parts.append("<ul>")
            parts.extend(f"<li>{html.escape(str(change))}</li>" for change in changes)
            parts.append("</ul>")
        else:
            parts.append("<p>No changes listed.</p>")
    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)

# --------------------------------------------------------------------------------------------------
# Internal parsing
# --------------------------------------------------------------------------------------------------
def _format_release_datetime_local(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        release_datetime = datetime.fromisoformat(value)
    except ValueError:
        return value
    if release_datetime.tzinfo is None:
        release_datetime = release_datetime.replace(tzinfo=UTC)
    return release_datetime.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
# --------------------------------------------------------------------------------------------------
def _read_json_url(url: str) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": RELEASE_HTTP_USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not fetch the latest release from {RELEASE_REPOSITORY_NAME}."
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("Latest release metadata must contain an object.")
    return data
# --------------------------------------------------------------------------------------------------
def _get_release_asset(release_data: dict[str, object], file_suffix: str) -> ReleaseAsset:
    assets = release_data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Latest GitHub release does not contain an assets list.")
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        download_url = asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(download_url, str) and name.endswith(file_suffix):
            return ReleaseAsset(name=name, download_url=download_url)
    raise ValueError(f"Latest GitHub release does not contain a {file_suffix} asset.")
# --------------------------------------------------------------------------------------------------
def _read_release_metadata(metadata_file_path: Path) -> dict[str, object]:
    try:
        metadata = json.loads(metadata_file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid release metadata JSON: {metadata_file_path}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"Release metadata must contain an object: {metadata_file_path}")
    return metadata
# --------------------------------------------------------------------------------------------------
def _get_release_metadata_version(metadata: dict[str, object]) -> str:
    version = metadata.get("version")
    if not isinstance(version, str):
        raise ValueError("Release metadata does not contain a version string.")
    parse_semantic_version(version)
    return version
# --------------------------------------------------------------------------------------------------
def _get_release_metadata_archive_sha256(metadata: dict[str, object]) -> str:
    archive_sha256 = metadata.get("archive_sha256")
    if not isinstance(archive_sha256, str) or SHA256_RE.fullmatch(archive_sha256) is None:
        raise ValueError("Release metadata does not contain a valid archive SHA-256.")
    return archive_sha256
# --------------------------------------------------------------------------------------------------
def _get_release_metadata_entries(metadata: dict[str, object]) -> list[dict[str, object]]:
    releases = metadata.get("releases")
    if not isinstance(releases, list) or not all(isinstance(release, dict) for release in releases):
        raise ValueError("Release metadata releases must be a list of objects.")
    return releases
# --------------------------------------------------------------------------------------------------
def _read_releases_data(releases_file_path: Path) -> dict[str, list[dict[str, object]]]:
    if not releases_file_path.exists():
        return {"releases": []}
    try:
        releases_data = json.loads(releases_file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid releases JSON: {releases_file_path}") from exc
    if not isinstance(releases_data, dict) or not isinstance(releases_data.get("releases"), list):
        raise ValueError(f"Releases JSON must contain a releases list: {releases_file_path}")
    return releases_data
# --------------------------------------------------------------------------------------------------
def _is_hidden_path(file_path: Path) -> bool:
    return any(part.startswith(".") for part in file_path.parts)
