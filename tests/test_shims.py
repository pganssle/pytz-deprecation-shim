import hypothesis

import pytz_deprecation_shim as pds

from ._common import valid_zone_strategy


@hypothesis.given(key=valid_zone_strategy)
def test_timezone_repr(key):
    zone = pds.timezone(key)

    assert key in repr(zone)
