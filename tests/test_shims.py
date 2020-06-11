from datetime import timedelta

import hypothesis
import hypothesis.strategies as hst
import pytest
import pytz

import pytz_deprecation_shim as pds

from . import _zoneinfo_data
from ._common import (
    MAX_DATETIME,
    MIN_DATETIME,
    assert_dt_equivalent,
    assert_dt_offset,
    dt_strategy,
    round_normalized,
    valid_zone_strategy,
)


def test_fixed_offset_utc():
    """Tests that fixed_offset_timezone(0) always returns UTC."""
    assert pds.fixed_offset_timezone(0) is pds.UTC


@pytest.mark.parametrize("key", ["utc", "UTC"])
def test_timezone_utc_singleton(key):
    assert pds.timezone(key) is pds.UTC


@hypothesis.given(key=valid_zone_strategy)
def test_timezone_repr(key):
    zone = pds.timezone(key)

    assert key in repr(zone)


@hypothesis.given(dt=dt_strategy, key=valid_zone_strategy)
def test_localize_default_is_dst(dt, key):
    """Tests localize when is_dst is not specified.

    With pytz, is_dst defaults to False, but with the shims, if is_dst is
    unspecified we will assume that the user is indifferent about what to do
    and do whatever the underlying behavior of the time zone we're shimming
    around does.
    """

    shim_zone = pds.timezone(key)

    with pytest.warns(pds.PytzUsageWarning):
        dt_localized = shim_zone.localize(dt)

    dt_replaced = dt.replace(tzinfo=shim_zone)
    assert_dt_equivalent(dt_localized, dt_replaced)


@hypothesis.given(
    dt=dt_strategy,
    delta=hst.timedeltas(
        min_value=timedelta(days=-730), max_value=timedelta(days=730)
    ),
    key=valid_zone_strategy,
)
def test_normalize_pytz_zone(dt, delta, key):
    """Test that pds.normalize works on pytz-zoned datetimes.

    This allows you to take a zone you've normalized via pytz and convert
    it to the shim zone.
    """
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    dt_pytz = pytz_zone.localize(dt) + delta
    dt_pytz_normalized = pytz_zone.normalize(dt_pytz)

    with pytest.warns(pds.PytzUsageWarning):
        dt_shim = shim_zone.normalize(dt_pytz)

    rounded_shim = round_normalized(dt_shim)
    rounded_pytz = round_normalized(dt_pytz_normalized)

    rounded_shim_naive = rounded_shim.replace(tzinfo=None)
    rounded_pytz_naive = rounded_pytz.replace(tzinfo=None)

    hypothesis.assume(MIN_DATETIME <= rounded_shim_naive <= MAX_DATETIME)
    assert rounded_shim_naive == rounded_pytz_naive


@pytest.mark.parametrize(
    "key, dt, offset", _zoneinfo_data.get_unambiguous_cases()
)
def test_localize_unambiguous_build_tzinfo(key, dt, offset):
    zone = pds.build_tzinfo(key, _zoneinfo_data.get_zone_file_obj(key))

    with pytest.warns(pds.PytzUsageWarning):
        dt_localized = zone.localize(dt)

    assert_dt_offset(dt_localized, offset)
