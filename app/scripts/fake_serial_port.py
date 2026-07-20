"""Create a registered pseudo-terminal that echoes serial traffic."""

import json
import os
import signal
from pathlib import Path

from src.utils.logging import init_logging, logger
from src.utils.paths import get_fake_serial_ports_dir_path

# --------------------------------------------------------------------------------------------------
# Fake serial port
# --------------------------------------------------------------------------------------------------
def create_fake_serial_port() -> tuple[int, int, str]:
    """Create a raw pseudo-terminal and return its file descriptors and device path."""
    import pty
    import tty

    master_file_descriptor, slave_file_descriptor = pty.openpty()
    tty.setraw(slave_file_descriptor)
    device = os.ttyname(slave_file_descriptor)
    return master_file_descriptor, slave_file_descriptor, device
# --------------------------------------------------------------------------------------------------
def register_fake_serial_port(device: str) -> Path:
    """Register a fake serial port for discovery by the application."""
    registration_dir_path = get_fake_serial_ports_dir_path()
    registration_dir_path.mkdir(parents=True, exist_ok=True)
    registration_file_path = registration_dir_path / f"{os.getpid()}.json"
    registration = {
        "pid": os.getpid(),
        "device": device,
        "description": "Fake serial port",
    }
    registration_file_path.write_text(
        f"{json.dumps(registration, indent=2)}\n",
        encoding="utf-8",
        newline="\n",
    )
    return registration_file_path
# --------------------------------------------------------------------------------------------------
def echo_serial_traffic(master_file_descriptor: int) -> None:
    """Log bytes received through the slave endpoint and echo them unchanged."""
    while True:
        received_data = os.read(master_file_descriptor, 4_096)
        if not received_data:
            return
        logger.info(f"Received: {received_data!r}")
        remaining_data = memoryview(received_data)
        while remaining_data:
            written_byte_count = os.write(master_file_descriptor, remaining_data)
            remaining_data = remaining_data[written_byte_count:]
# --------------------------------------------------------------------------------------------------
def request_shutdown(_signal_number: int, _frame: object) -> None:
    """Convert termination requests into the normal cleanup path."""
    raise KeyboardInterrupt
# --------------------------------------------------------------------------------------------------
def main() -> int:
    """Run the fake serial-port helper until interrupted."""
    init_logging()
    if os.name != "posix":
        logger.error("Fake serial ports are supported only on macOS and Linux.")
        return 1
    master_file_descriptor = -1
    slave_file_descriptor = -1
    registration_file_path: Path | None = None
    try:
        master_file_descriptor, slave_file_descriptor, device = create_fake_serial_port()
        registration_file_path = register_fake_serial_port(device)
        signal.signal(signal.SIGTERM, request_shutdown)
        logger.info(f"Fake serial port connected: {device}")
        logger.info("Bytes received on this port will be logged and echoed unchanged.")
        logger.info("Press Ctrl+C to disconnect.")
        echo_serial_traffic(master_file_descriptor)
    except KeyboardInterrupt:
        logger.info("Disconnecting fake serial port...")
    finally:
        if registration_file_path is not None:
            registration_file_path.unlink(missing_ok=True)
        if slave_file_descriptor >= 0:
            os.close(slave_file_descriptor)
        if master_file_descriptor >= 0:
            os.close(master_file_descriptor)
    return 0

# --------------------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    raise SystemExit(main())
