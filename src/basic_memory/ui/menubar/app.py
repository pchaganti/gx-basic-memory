"""Basic Memory menubar app using PyQt."""
import sys
import asyncio
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from loguru import logger
import qasync

from basic_memory.config import config
from basic_memory.cli.commands.sync import get_sync_service
from basic_memory.sync.watch_service import WatchService

class BasicMemoryTray(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        
        # Set default icon
        self.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # Create menu
        menu = QMenu()
        self.status_item = menu.addAction("Status: Idle")
        self.status_item.setEnabled(False)
        
        menu.addSeparator()
        self.sync_action = menu.addAction("Start Sync")
        self.sync_action.triggered.connect(self.toggle_sync)
        
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)
        
        self.setContextMenu(menu)
        self.show()

        # Initialize sync state
        self.watch_service = None
        self.sync_task = None
        self.is_syncing = False

        # Update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

        logger.info("Basic Memory tray initialized")

    def toggle_sync(self):
        """Start or stop sync process."""
        if not self.is_syncing:
            logger.info("Starting sync")
            self.start_sync()
            self.sync_action.setText("Stop Sync")
            self.is_syncing = True
        else:
            logger.info("Stopping sync")
            self.stop_sync()
            self.sync_action.setText("Start Sync")
            self.is_syncing = False

    def start_sync(self):
        """Start the sync service."""
        async def run_sync():
            try:
                sync_service = await get_sync_service()
                self.watch_service = WatchService(
                    sync_service=sync_service,
                    file_service=sync_service.entity_service.file_service,
                    config=config
                )
                await self.watch_service.run(console_status=False)
            except Exception as e:
                logger.exception("Error in sync service")
                self.status_item.setText(f"Status: Error - {str(e)}")

        # Start sync using the event loop
        loop = asyncio.get_event_loop()
        self.sync_task = loop.create_task(run_sync())

    def stop_sync(self):
        """Stop the sync service."""
        if self.watch_service:
            self.watch_service.state.running = False
            self.watch_service = None
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()

    def update_status(self):
        """Update status display."""
        if self.watch_service:
            state = self.watch_service.state
            status = "Running" if state.running else "Stopped"
            last_scan = state.last_scan.strftime("%H:%M:%S") if state.last_scan else "-"
            self.status_item.setText(f"Status: {status} (Last scan: {last_scan})")
        else:
            self.status_item.setText("Status: Idle")

def main():
    """Run the menubar app."""
    app = QApplication(sys.argv)
    
    # Create event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create tray
    tray = BasicMemoryTray()
    
    # Run event loop
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
