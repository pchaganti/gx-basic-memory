"""Basic Memory menubar app using rumps."""
import rumps
from loguru import logger

class BasicMemoryApp(rumps.App):
    def __init__(self):
        super().__init__("Basic Memory", "✓")
        
        # Initialize menu structure
        self.menu = [
            rumps.MenuItem("Status: Idle"),
            None,  # separator
            rumps.MenuItem("Recent Events"),
            None,
            ["Settings",
                "Choose Home Directory...",
                "Start at Login"
            ],
            None,
            "Start Sync",
        ]

    @rumps.clicked("Start Sync")
    def toggle_sync(self, _):
        """Toggle sync on/off."""
        sender = self.menu["Start Sync"]
        if sender.title == "Start Sync":
            sender.title = "Stop Sync"
            self.icon = "↻"
            # TODO: Start sync process
        else:
            sender.title = "Start Sync"
            self.icon = "✓"
            # TODO: Stop sync process

    @rumps.clicked("Settings", "Choose Home Directory...")
    def choose_home_dir(self, _):
        """Open dialog to choose home directory."""
        # TODO: Implement directory chooser
        logger.info("Choose home directory clicked")

def main():
    """Run the menubar app."""
    BasicMemoryApp().run()

if __name__ == "__main__":
    main()
