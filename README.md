# Position Controller

PySide6 GUI to control a positioner using G-code.

## Run the application

The launchers install `uv`, Python 3.12, and the project dependencies into the repository on first use. Internet access is required for the initial setup.

### Linux

```bash
cd /path/to/Position-Controller
bash Linux_Position_Controller.sh
# Or
./Linux_Position_Controller.sh
```

### macOS

```bash
cd /path/to/Position-Controller
bash Mac_Position_Controller.command
# Or
./Mac_Position_Controller.command
```

If macOS blocks a downloaded launcher, enable it with:

```bash
cd /path/to/Position-Controller
xattr -dr com.apple.quarantine .
chmod +x Mac_Position_Controller.command
```

### Windows

Double-click `Windows_Position_Controller.bat`, or run it from Command Prompt (CMD):

```bat
cd /d "C:\path\to\Position-Controller"
Windows_Position_Controller.bat
```

## Developers

### Developer execution

With `uv` already installed:

```bash
cd /path/to/Position-Controller/app
uv run python main.py
```

### Fake serial port

This development helper simulates a serial device so you can test port discovery and communication
without connecting physical hardware. On macOS and Linux, start it from another terminal with the
platform launcher:

```bash
cd /path/to/Position-Controller
./Linux_Position_Controller.sh fake-serial-port
./Mac_Position_Controller.command fake-serial-port
```

The port appears in the device selector within five seconds. Bytes sent to it are printed by the
helper and echoed unchanged. Run the command in additional terminals to create multiple fake ports,
and press `Ctrl+C` in a helper terminal to disconnect that port.

The helper uses Python's standard-library pseudo-terminal support, so it requires no additional
dependency. Windows is not supported.

### Releases and updates

Updates are published through [GitHub Releases](https://github.com/CFIS-UFRO/Position-Controller/releases).

The release workflow requires Git, push access to the repository, and the GitHub CLI (`gh`).

Run the platform launcher with the `release` argument:

```bash
cd /path/to/Position-Controller
./Linux_Position_Controller.sh release
./Mac_Position_Controller.command release
```

On Windows:

```bat
cd /d "C:\path\to\Position-Controller"
Windows_Position_Controller.bat release
```
