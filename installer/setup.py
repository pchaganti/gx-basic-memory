from cx_Freeze import setup, Executable
import sys

# Base configuration for macOS
base = "gui" if sys.platform == "darwin" else None

# Mac specific options
mac_options = {
    'bundle_name': 'Basic Memory Installer',
    'plist_items': [
        # Convert dict to list of tuples for plist items
        ('CFBundleName', 'Basic Memory Installer'),
        ('CFBundleDisplayName', 'Basic Memory Installer'),
        ('CFBundleIdentifier', 'com.basicmemory.installer'),
        ('CFBundleVersion', '1.0.0'),
        ('CFBundlePackageType', 'APPL'),
        ('LSMinimumSystemVersion', '10.13.0'),
    ]
}

executables = [
    Executable(
        "installer.py",
        target_name="Basic Memory Installer",
        base=base,
    )
]

setup(
    name="basic-memory-installer",
    version="1.0.0",
    description="Installer for Basic Memory",
    executables=executables,
    options={
        "build_exe": {
            "include_files": [],
        },
        "bdist_mac": mac_options,
    }
)
