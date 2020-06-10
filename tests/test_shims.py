import hypothesis
import pytest

import pytz_deprecation_shim as pds

from ._common import assert_dt_equivalent, dt_strategy, valid_zone_strategy


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
