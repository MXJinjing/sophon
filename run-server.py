#!/usr/bin/env python3
"""Run using the Sophon server environment (uv run --project sophon-server)."""
from pathlib import Path
import runpy
import sys

SOURCE = Path(__file__).resolve().parent / 'sophon-server' / 'src'
sys.path.insert(0, str(SOURCE))

if __name__ == '__main__':
    runpy.run_path(str(SOURCE / 'server.py'), run_name='__main__')
