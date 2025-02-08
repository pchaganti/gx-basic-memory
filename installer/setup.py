from cx_Freeze import setup, Executable

executables = [
    Executable(
        "installer.py",
        target_name="Basic Memory Installer",
        base="gui"
    )
]

setup(
    name="basic-memory-installer",
    version="1.0.0",
    description="Installer for Basic Memory",
    executables=executables,
)
