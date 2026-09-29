#!/usr/bin/env python3
"""Build portable Python sdist/wheel for the standard-library CLI."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', default=str(ROOT / 'dist'))
    args = parser.parse_args()
    subprocess.run(['uv', 'build', '--project', str(ROOT / 'sophon-client'),
                    '--out-dir', str(Path(args.out_dir).expanduser().resolve())], cwd=ROOT, check=True)
