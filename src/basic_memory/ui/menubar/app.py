"""Basic Memory menubar app - process manager for sync service."""

import os
import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle, QMainWindow, QTextEdit
from PyQt6.QtCore import QTimer
from loguru import logger

from basic_memory.config import config


class StatusWindow(QMainWindow):
    """Window to show sync process output."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Basic Memory Status")
        self.resize(800, 400)

        # Create terminal-like text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: Menlo, Monaco, 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.setCentralWidget(self.text_display)

        # Update timer for reading process output
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_output)
        self.update_timer.start(100)  # Check output every 100ms

    def set_process(self, process):
        """Set the process to monitor."""
        self.process = process
        self.text_display.clear()

    def update_output(self):
        """Read and display new output from process."""
        if hasattr(self, "process") and self.process:
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.text_display.append(line.strip())


class BasicMemoryTray(QSystemTrayIcon):
    """System tray icon for managing Basic Memory sync."""

    def __init__(self):
        super().__init__()

        # Set icon
        self.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        # Create menu
        menu = QMenu()
        self.status_item = menu.addAction("Status: Idle")
        self.status_item.setEnabled(False)

        menu.addSeparator()
        self.sync_action = menu.addAction("Start Sync")
        self.sync_action.triggered.connect(self.toggle_sync)

        menu.addAction("Show Status").triggered.connect(self.show_status)

        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(self.cleanup_and_quit)

        self.setContextMenu(menu)
        self.show()

        # Initialize state
        self.process = None
        self.status_window = None

        # Update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_process)
        self.status_timer.start(1000)  # Check every second

        logger.info("Basic Memory tray initialized")

    def show_status(self):
        """Show status window."""
        if not self.status_window:
            self.status_window = StatusWindow()
        if self.process:
            self.status_window.set_process(self.process)
        self.status_window.show()
        self.status_window.raise_()

    def toggle_sync(self):
        """Start or stop sync process."""
        if not self.process:
            self.start_sync()
        else:
            self.stop_sync()

    def start_sync(self):
        """Start the sync subprocess."""
        logger.info("Starting sync process")
        try:
            self.process = subprocess.Popen(
                [
                    "uvx",
                    "basic-memory",
                    "sync",
                    "--watch",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
            )
            self.sync_action.setText("Stop Sync")
            if self.status_window:
                self.status_window.set_process(self.process)
        except Exception as e:
            logger.exception("Failed to start sync process")
            self.status_item.setText(f"Status: Error - {str(e)}")

    def stop_sync(self):
        """Stop the sync subprocess."""
        logger.info("Stopping sync process")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)  # Wait up to 2 seconds
            except subprocess.TimeoutExpired:
                self.process.kill()  # Force kill if it doesn't terminate
            self.process = None
        self.sync_action.setText("Start Sync")

    def check_process(self):
        """Check sync process status."""
        if self.process:
            if self.process.poll() is not None:  # Process has ended
                self.process = None
                self.sync_action.setText("Start Sync")
                self.status_item.setText("Status: Idle")
            else:
                self.status_item.setText("Status: Running")
        else:
            self.status_item.setText("Status: Idle")

    def cleanup_and_quit(self):
        """Clean up before quitting."""
        logger.info("Cleaning up...")
        if self.status_window:
            self.status_window.close()
        self.stop_sync()
        QApplication.instance().quit()


def ensure_single_instance():
    """Ensure only one instance of the menubar app is running."""
    pid_file = config.home / ".basic-memory" / "menubar.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text())
            os.kill(pid, 0)  # Check if process exists
            logger.error(f"Basic Memory menubar is already running (PID: {pid})")
            sys.exit(1)
        except (OSError, ValueError):
            # Process not running or invalid PID
            pass

    # Write current PID
    pid = str(os.getpid())
    pid_file.write_text(pid)
    logger.debug(f"PID {pid} written to file {pid_file}")
    return pid_file


def main():
    """Run the menubar app."""
    # Ensure single instance
    pid_file = ensure_single_instance()

    try:
        app = QApplication(sys.argv)
        BasicMemoryTray()
        app.exec()
    finally:
        # Clean up PID file
        pid_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
