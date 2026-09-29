#!/usr/bin/env python3
"""Run the src-layout client without installing third-party dependencies."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'sophon-client' / 'src'))
from sophon_client.package_cli import main

if __name__ == '__main__':
    raise SystemExit(main())
