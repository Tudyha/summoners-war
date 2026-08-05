"""Lazy compatibility facade for domain-specific visual detectors."""

import importlib


_COMPATIBILITY_MODULES = (
    "core",
    "map",
    "overlay",
    "startup",
    "friend",
    "tutorial",
    "battle",
)


def __getattr__(name):
    """Resolve legacy ``vision.<detector>`` access without eager imports."""
    if name == "load_tests" or name.startswith("__"):
        raise AttributeError(name)
    for module_name in _COMPATIBILITY_MODULES:
        module = importlib.import_module(
            ".{}".format(module_name),
            __name__,
        )
        if hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
