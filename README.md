# Position Controller

PySide6 GUI to control a positioner using G-code.

## Run the application

The launchers install `uv`, Python 3.12, and dependencies. Internet access is required on the first run.

### Linux

```bash
./Position_Controller_Linux.sh
```

### macOS

```bash
./Position_Controller_Mac.command
```

If macOS blocks a downloaded launcher, enable it with:

```bash
xattr -dr com.apple.quarantine .
chmod +x Position_Controller_Mac.command
```

### Windows

Double-click `Position_Controller_Windows.bat`, or run it from Command Prompt.

### Developer execution

With `uv` already installed:

```bash
cd app
uv run python main.py
```

## Releases and updates

Updates are published through [GitHub Releases](https://github.com/CFIS-UFRO/Position-Controller/releases).

The release workflow requires Git, push access to the repository, and the GitHub CLI (`gh`).

Run the platform launcher with the `release` argument:

```bash
./Position_Controller_Linux.sh release
./Position_Controller_Mac.command release
```

On Windows:

```bat
Position_Controller_Windows.bat release
```
