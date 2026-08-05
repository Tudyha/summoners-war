"""Load pure project modules without importing the AScript-dependent facade."""

import importlib
import pathlib
import sys
import types


PACKAGE = "summoners_war_test_package"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def project_module(name):
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(ROOT)]
        package.__package__ = PACKAGE
        sys.modules[PACKAGE] = package
    return importlib.import_module("{}.{}".format(PACKAGE, name))
