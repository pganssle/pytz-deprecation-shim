"""
This module contains helper functions to ease the transition from ``pytz`` to
another :pep:`495`-compatible library.
"""

from . import _common

_PYTZ_BASE_CLASSES = None


def is_pytz_zone(tz):
    """Check if a time zone is a ``pytz`` time zone.

    This will only import ``pytz`` if it has already been imported, and does
    not rely on the existence of the ``localize`` or ``normalize`` methods
    (since the shim classes also have these methods, but are not ``pytz``
    zones).
    """

    # If pytz is not in sys.modules, then we will assume the time zone is not a
    # pytz zone. It is possible that someone has manipulated sys.modules to
    # remove pytz, but that's the kind of thing that causes all kinds of other
    # problems anyway, so we'll call that an unsupported configuration.
    if not _common.pytz_imported():
        return False

    if _PYTZ_BASE_CLASSES is None:
        _populate_pytz_base_classes()

    return isinstance(tz, _PYTZ_BASE_CLASSES)


def _populate_pytz_base_classes():
    import pytz
    from pytz.tzinfo import BaseTzInfo

    base_classes = (BaseTzInfo, pytz._FixedOffset)

    # In releases prior to 2018.4, pytz.UTC was not a subclass of BaseTzInfo
    if not isinstance(pytz.UTC, BaseTzInfo):  # pragma: nocover
        base_classes = base_classes + (type(pytz.UTC),)

    global _PYTZ_BASE_CLASSES
    _PYTZ_BASE_CLASSES = base_classes
