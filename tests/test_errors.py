from datetime import datetime, timedelta

import hypothesis
import pytest
import pytz

import pytz_deprecation_shim as pds

from ._common import (
    invalid_offset_minute_strategy,
    invalid_zone_strategy,
    valid_zone_strategy,
)


# On Python 2.7 when running 5 test suites in parallel, this is reliably flaky
# without increasing the deadline. When running 1 or 2 in parallel it's only
# intermittently flaky.
@hypothesis.settings(deadline=timedelta(seconds=30))
@hypothesis.given(key=invalid_zone_strategy)
@hypothesis.example(key="")
def test_invalid_zones(key):
    with pytest.raises(pds.UnknownTimeZoneError) as exc_info:
        pds.timezone(key)

    assert issubclass(exc_info.type, pytz.UnknownTimeZoneError)


@hypothesis.given(key=valid_zone_strategy)
def test_localize_aware_datetime(key):
    zone = pds.timezone(key)
    dt = datetime(2020, 1, 1, tzinfo=pds.UTC)

    with pytest.warns(pds.PytzUsageWarning), pytest.raises(ValueError):
        zone.localize(dt)


@hypothesis.given(key=valid_zone_strategy)
def test_normalize_naive_datetime(key):
    zone = pds.timezone(key)
    dt = datetime(2020, 1, 1)

    with pytest.warns(pds.PytzUsageWarning), pytest.raises(ValueError):
        zone.normalize(dt)


@hypothesis.given(offset=invalid_offset_minute_strategy)
def test_invalid_fixed_offsets(offset):
    with pytest.raises(ValueError):
        pds.fixed_offset_timezone(offset)
