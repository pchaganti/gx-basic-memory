from cx_Freeze import setup, Executable

executables = [
    Executable(
        "installer.py",
        target_name="Basic Memory Installer",
        base="gui"
    )
]

setup(
    name="basic-memory",
    version=open("../pyproject.toml").read().split('version = "', 1)[1].split('"', 1)[0],
    description="Basic Memory",
    executables=executables,
)
