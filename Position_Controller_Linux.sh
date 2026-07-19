#!/usr/bin/env bash
set -euo pipefail

# ##################################################################################################
# Launch Position Controller on Linux with a project-local uv installation and Python environment.
# ##################################################################################################

# --------------------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"
UV_DIR="$APP_DIR/.uv"
UV_BIN="$UV_DIR/uv"
UV_CACHE_DIR="$UV_DIR/cache"
UV_PYTHON_INSTALL_DIR="$UV_DIR/python"
UV_PROJECT_ENVIRONMENT="$UV_DIR/venv"
MAIN_FILE="$APP_DIR/main.py"
RELEASE_MODULE="scripts.create_release"
cd "$APP_DIR"

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------
RESTART_EXIT_CODE=42

# --------------------------------------------------------------------------------------------------
# uv installation
# --------------------------------------------------------------------------------------------------
if [ ! -x "$UV_BIN" ]; then
    mkdir -p "$UV_DIR"
    export UV_INSTALL_DIR="$UV_DIR"
    export INSTALLER_NO_MODIFY_PATH=1
    if command -v curl >/dev/null 2>&1; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        echo "Installing uv..."
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "curl or wget is required to install uv."
        exit 1
    fi
fi
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR
export UV_PROJECT_ENVIRONMENT

# --------------------------------------------------------------------------------------------------
# Developer release
# --------------------------------------------------------------------------------------------------
if [ "${1:-}" = "release" ]; then
    "$UV_BIN" run python -m "$RELEASE_MODULE"
    exit $?
fi

# --------------------------------------------------------------------------------------------------
# Application launch and restart
# --------------------------------------------------------------------------------------------------
while true; do
    if "$UV_BIN" run python "$MAIN_FILE"; then
        exit_code=0
    else
        exit_code=$?
    fi
    if [ "$exit_code" -ne "$RESTART_EXIT_CODE" ]; then
        exit "$exit_code"
    fi
    echo "Restarting Position Controller..."
done
