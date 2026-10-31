"""PyInstaller entry point: keystone/__main__.py uses relative imports, so it must not run as a script."""
import sys

from keystone.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
