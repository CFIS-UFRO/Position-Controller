"""Interactive release publisher used by the platform launchers."""

import shutil
import subprocess
import sys
from pathlib import Path

from src.config import APP_NAME, RELEASE_REPOSITORY_NAME
from src.utils.logging import init_logging, logger
from src.utils.paths import (
    get_project_dir_path,
    get_pyproject_file_path,
    get_releases_file_path,
    get_uv_lock_file_path,
)
from src.utils.releases import (
    append_release_entry,
    calculate_file_sha256,
    compress_paths,
    get_git_managed_file_paths,
    get_pyproject_version,
    get_release_entries,
    get_release_file_stem,
    update_pyproject_version,
    write_release_metadata,
)
from src.utils.tmp import get_tmp_file_path

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------
UPDATE_TYPE_ALIASES = {
    "1": "major",
    "2": "minor",
    "3": "bugfix",
}

# --------------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------------
def main() -> int:
    """Run the interactive release workflow."""
    init_logging()
    logger.info("Starting release process...")
    validate_release_requirements()
    validate_clean_worktree(get_project_dir_path())
    validate_github_authentication()
    validate_release_repository()
    update_type = ask_update_type()
    release_changes = ask_release_changes()
    project_dir_path = get_project_dir_path()
    pyproject_file_path = get_pyproject_file_path()
    uv_lock_file_path = get_uv_lock_file_path()
    releases_file_path = get_releases_file_path()
    previous_version = get_pyproject_version(pyproject_file_path)
    new_version = update_pyproject_version(pyproject_file_path, uv_lock_file_path, update_type)
    logger.info(f"Updated project version: {previous_version} -> {new_version}")
    append_release_entry(releases_file_path, new_version, release_changes)
    release_file_stem = get_release_file_stem(new_version)
    archive_file_path = get_tmp_file_path(f"{release_file_stem}.zip")
    metadata_file_path = get_tmp_file_path(f"{release_file_stem}.json")
    release_file_paths = get_git_managed_file_paths(project_dir_path)
    compress_paths(project_dir_path, release_file_paths, archive_file_path)
    archive_sha256 = calculate_file_sha256(archive_file_path)
    write_release_metadata(
        metadata_file_path.name,
        new_version,
        archive_sha256,
        get_release_entries(releases_file_path),
    )
    logger.info(f"Created release archive: {archive_file_path}")
    logger.info(f"Created release metadata: {metadata_file_path}")
    commit_and_push_release_changes(
        project_dir_path,
        previous_version,
        new_version,
        [pyproject_file_path, uv_lock_file_path, releases_file_path],
    )
    create_github_release(new_version, [archive_file_path, metadata_file_path])
    logger.info(f"Release {new_version} completed")
    return 0
# --------------------------------------------------------------------------------------------------
def validate_release_requirements() -> None:
    """Require the Git and authenticated GitHub command-line tools."""
    missing_commands = [command for command in ("git", "gh") if shutil.which(command) is None]
    if missing_commands:
        raise RuntimeError(f"Missing required command(s): {', '.join(missing_commands)}")
# --------------------------------------------------------------------------------------------------
def validate_clean_worktree(project_dir_path: Path) -> None:
    """Prevent release packaging from including unrelated working-tree changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_dir_path,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise RuntimeError("Commit or discard all working-tree changes before creating a release.")
# --------------------------------------------------------------------------------------------------
def validate_github_authentication() -> None:
    """Ensure the GitHub CLI has an authenticated account."""
    logger.info("Checking GitHub CLI authentication...")
    if subprocess.run(["gh", "auth", "status"], check=False).returncode == 0:
        return
    logger.info("GitHub CLI is not authenticated. Starting interactive login...")
    subprocess.run(["gh", "auth", "login"], check=True)
    subprocess.run(["gh", "auth", "status"], check=True)
# --------------------------------------------------------------------------------------------------
def validate_release_repository() -> None:
    """Require the configured GitHub release repository to exist and be accessible."""
    result = subprocess.run(
        ["gh", "repo", "view", RELEASE_REPOSITORY_NAME],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Release repository {RELEASE_REPOSITORY_NAME} is unavailable. "
            "Create it or update src/config.py before publishing."
        )
# --------------------------------------------------------------------------------------------------
def ask_update_type() -> str:
    """Ask which semantic-version component should be incremented."""
    while True:
        answer = ask_console_input("Update type [1 major, 2 minor, 3 bugfix]: ").strip().lower()
        update_type = UPDATE_TYPE_ALIASES.get(answer)
        if update_type is not None:
            return update_type
        print("Please choose 1 for major, 2 for minor, or 3 for bugfix.")
# --------------------------------------------------------------------------------------------------
def ask_release_changes() -> list[str]:
    """Collect one or more human-readable release notes."""
    print("Release description. Enter one change per line and use an empty line to finish.")
    changes = []
    while True:
        change = normalize_release_change(input())
        if change:
            changes.append(change)
            continue
        if changes:
            return changes
        print("Add at least one release change.")
# --------------------------------------------------------------------------------------------------
def ask_console_input(prompt: str) -> str:
    """Display a prompt through the original terminal stream."""
    print(prompt, end="", flush=True, file=sys.__stdout__)
    return input()
# --------------------------------------------------------------------------------------------------
def normalize_release_change(change: str) -> str:
    """Remove common pasted list prefixes from a release note."""
    normalized_change = change.strip()
    for prefix in ("- ", "* ", "• "):
        if normalized_change.startswith(prefix):
            return normalized_change[len(prefix):].strip()
    return normalized_change

# --------------------------------------------------------------------------------------------------
# GitHub release
# --------------------------------------------------------------------------------------------------
def create_github_release(version: str, asset_file_paths: list[Path]) -> None:
    """Publish the archive and metadata as a GitHub release."""
    run_command(
        [
            "gh",
            "release",
            "create",
            f"v{version}",
            *[str(path) for path in asset_file_paths],
            "--repo",
            RELEASE_REPOSITORY_NAME,
            "--title",
            f"{APP_NAME} {version}",
            "--notes",
            f"Application update for {APP_NAME} {version}.",
        ],
        cwd=get_project_dir_path(),
    )
# --------------------------------------------------------------------------------------------------
def run_command(command: list[str], cwd: Path) -> None:
    """Run a release command and fail on non-zero exit status."""
    logger.info(f"Running command in {cwd}: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)

# --------------------------------------------------------------------------------------------------
# Source repository update
# --------------------------------------------------------------------------------------------------
def commit_and_push_release_changes(
    project_dir_path: Path,
    previous_version: str,
    new_version: str,
    changed_file_paths: list[Path],
) -> None:
    """Commit and push the version and release-history changes."""
    run_command(
        [
            "git",
            "add",
            "--",
            *[str(path.relative_to(project_dir_path)) for path in changed_file_paths],
        ],
        cwd=project_dir_path,
    )
    if not has_staged_changes(project_dir_path):
        raise RuntimeError("No release changes were staged for commit.")
    commit_message = f"Upgrade version from {previous_version} to {new_version}"
    run_command(["git", "commit", "-m", commit_message], cwd=project_dir_path)
    run_command(["git", "push"], cwd=project_dir_path)
# --------------------------------------------------------------------------------------------------
def has_staged_changes(project_dir_path: Path) -> bool:
    """Return whether the Git index contains changes."""
    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"],
        cwd=project_dir_path,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError("Could not check staged release changes.")
    return result.returncode == 1

# --------------------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    raise SystemExit(main())
