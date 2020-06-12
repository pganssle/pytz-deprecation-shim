# -*- coding: utf-8 -*-
import sys
import threading

import pytest
import pytz

import pytz_deprecation_shim as pds
from pytz_deprecation_shim import helpers as pds_helpers

from ._common import UTC

get_timezone = pds._compat.get_timezone
get_fixed_timezone = pds._compat.get_fixed_offset_zone

SYS_MODULES_LOCK = threading.Lock()
HELPER_LOCK = threading.Lock()

ZONE_LIST = (
    "America/New_York",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Africa/Abidjan",
    "America/Santiago",
    "Europe/London",
    "Europe/Dublin",
)


def _timezones(tz_constructor):
    return tuple(map(tz_constructor, ZONE_LIST))


def _fixed_offsets(tz_constructor):
    return tuple(map(tz_constructor, OFFSET_MINUTES_LIST))


NON_PYTZ_ZONES = (
    (UTC, pds.timezone("UTC"))
    + _timezones(pds.timezone)
    + _timezones(get_timezone)
    + _fixed_offsets(pds.fixed_offset_timezone)
    + _fixed_offsets(get_fixed_timezone)
)

PYTZ_ZONES = (
    (pytz.UTC, pytz.timezone("UTC"))
    + _timezones(pytz.timezone)
    + _fixed_offsets(pytz.FixedOffset)
)


@pytest.fixture
def helper_lock():
    """Lock around anything using the helper module."""
    with HELPER_LOCK:
        yield


@pytest.fixture
def no_pytz(helper_lock):
    """Fixture to remove pytz from sys.modules for the duration of the test."""
    with SYS_MODULES_LOCK:
        pds._common._PYTZ_IMPORTED = False
        base_classes = pds_helpers._PYTZ_BASE_CLASSES
        pds_helpers._PYTZ_BASE_CLASSES = None
        pytz_modules = {}

        for modname in list(sys.modules):
            if modname.split(".", 1)[0] != "pytz":  # pragma: nocover
                continue

            pytz_modules[modname] = sys.modules.pop(modname)

        try:
            yield
        finally:
            sys.modules.update(pytz_modules)
            pds_helpers._PYTZ_BASE_CLASSES = base_classes


@pytest.mark.parametrize("tz", NON_PYTZ_ZONES)
def test_not_pytz_zones(tz, helper_lock):
    """Tests is_pytz_zone for non-pytz zones."""
    assert not pds_helpers.is_pytz_zone(tz)


@pytest.mark.parametrize("tz", NON_PYTZ_ZONES)
def test_not_pytz_no_pytz(tz, no_pytz):
    """Tests is_pytz_zone when pytz has not been imported."""
    assert not pds_helpers.is_pytz_zone(tz)

    # Ensure that the test didn't import `pytz`.
    assert "pytz" not in sys.modules


@pytest.mark.parametrize("tz", PYTZ_ZONES)
def test_pytz_zone(tz, helper_lock):
    assert pds_helpers.is_pytz_zone(tz)


@pytest.mark.parametrize("key", ("UTC",) + ZONE_LIST)
def test_pytz_zones_before_after(key, no_pytz):
    """Tests is_pytz_zone when pytz is imported after first use.

    We want to make sure that is_pytz_zone doesn't inappropriately cache the
    fact that pytz hasn't been imported, and just always return ``False``, even
    if pytz is imported after the first call to is_pytz_zone.
    """

    non_pytz_zone = pds.timezone(key)
    assert not pds_helpers.is_pytz_zone(non_pytz_zone)
    assert "pytz" not in sys.modules

    import pytz

    pytz_zone = pytz.timezone(key)
    assert pds_helpers.is_pytz_zone(pytz_zone)
