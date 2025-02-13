from cx_Freeze import setup, Executable
import sys

# Build options for all platforms
build_exe_options = {
    "packages": ["json", "pathlib"],
    "excludes": [],
}

# Platform-specific options
if sys.platform == "win32":
    base = "Win32GUI"
    build_exe_options.update(
        {
            "include_msvcr": True,  # Include Visual C++ runtime
        }
    )
    target_name = "Basic Memory Installer.exe"
else:  # darwin
    base = "gui"
    target_name = "Basic Memory Installer"

executables = [
    Executable(
        script="installer.py",
        target_name="Basic Memory Installer",
        base=base,
    )
]

setup(
    name="basic-memory",
    version=open("../pyproject.toml").read().split('version = "', 1)[1].split('"', 1)[0],
    description="Basic Memory - Local-first knowledge management",
    options={
        "build_exe": build_exe_options,
        "bdist_mac": {
            "bundle_name": "Basic Memory Installer",
        },
    },
    executables=executables,
)
