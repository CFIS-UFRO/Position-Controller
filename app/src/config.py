"""Application-wide metadata and release configuration."""

# --------------------------------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------------------------------
APP_NAME = "Position Controller"
APP_SLUG = "position_controller"
APP_DESCRIPTION = "GUI to control a positioner using G-code"
ORGANIZATION_NAME = "CFIS-UFRO"
RESTART_EXIT_CODE = 42

# --------------------------------------------------------------------------------------------------
# Releases
# --------------------------------------------------------------------------------------------------
RELEASE_REPOSITORY_NAME = "CFIS-UFRO/Position-Controller"
RELEASE_REPOSITORY_URL = f"https://github.com/{RELEASE_REPOSITORY_NAME}"
RELEASE_ARCHIVE_PREFIX = APP_SLUG
RELEASE_HTTP_USER_AGENT = "Position-Controller-Updater"
