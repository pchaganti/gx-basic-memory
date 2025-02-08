# Basic Memory Installer

This directory contains the macOS installer for Basic Memory.

## Building the Installer

Build the installer:
```bash
cd installer
python setup.py build
```

The installer app will be created in `installer/build/Basic Memory Installer`

## Development

- `installer.py` - Main installation script
- `setup.py` - py2app configuration for building the macOS app
