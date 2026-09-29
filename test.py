#!/usr/bin/env python3
"""Explicit unittest runner for the separated source/test directories."""
import argparse
import inspect
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
for path in [ROOT / 'sophon-server' / 'src', ROOT / 'sophon-server' / 'tests',
             ROOT / 'sophon-client' / 'src', ROOT]:
    sys.path.insert(0, str(path))

class Loader(unittest.TestLoader):
    def loadTestsFromModule(self, module, *, pattern=None):
        suite = super().loadTestsFromModule(module, pattern=pattern)
        # Preserve existing plain assertion-based tests without a pytest dependency.
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_') and not inspect.signature(function).parameters:
                suite.addTest(unittest.FunctionTestCase(function))
        return suite


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', choices=['server', 'client'], required=True)
    parser.add_argument('--pattern', default='test_*.py')
    args = parser.parse_args()
    directory = ROOT / f'sophon-{args.component}' / 'tests'
    suite = Loader().discover(str(directory), pattern=args.pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
