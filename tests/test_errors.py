import hypothesis
import pytest
import pytz

import pytz_deprecation_shim as pds

from ._common import invalid_zone_strategy


@hypothesis.given(key=invalid_zone_strategy)
@hypothesis.example(key="")
def test_invalid_zones(key):
    with pytest.raises(pds.UnknownTimeZoneError) as exc_info:
        pds.timezone(key)

    assert issubclass(exc_info.type, pytz.UnknownTimeZoneError)
