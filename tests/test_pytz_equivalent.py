from datetime import datetime, timedelta

import hypothesis
import pytest
import pytz
from hypothesis import strategies as hst

import pytz_deprecation_shim as pds
from pytz_deprecation_shim import PytzUsageWarning

VALID_ZONES = sorted(pytz.all_timezones)

NEGATIVE_EPOCHALYPSE = datetime(1901, 12, 13, 15, 45, 52)
NEGATIVE_EPOCHALYPSE = datetime(1912, 1, 1)
EPOCHALYPSE = datetime(2038, 1, 18, 22, 14, 8)

valid_zone_strategy = hst.sampled_from(VALID_ZONES)
dt_strategy = hst.datetimes(
    min_value=NEGATIVE_EPOCHALYPSE, max_value=EPOCHALYPSE
)
ZERO = timedelta(0)

_ARGENTINA_CITIES = [
    "Buenos_Aires",
    "Catamarca",
    "ComodRivadavia",
    "Cordoba",
    "Jujuy",
    "La_Rioja",
    "Mendoza",
    "Rio_Gallegos",
    "Rosario",
    "Salta",
    "San_Juan",
    "San_Luis",
    "Tucuman",
    "Ushuaia",
]

_ARGENTINA_ZONES = {"America/%s" % city for city in _ARGENTINA_CITIES}
_ARGENTINA_ZONES |= {
    "America/Argentina/%s" % city for city in _ARGENTINA_CITIES
}


@hypothesis.given(
    dt=dt_strategy, key=valid_zone_strategy, is_dst=hst.booleans()
)
@hypothesis.example(
    dt=datetime(2009, 3, 29, 2), key="Europe/Amsterdam", is_dst=True
)
def test_localize_explicit_is_dst(dt, key, is_dst):
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    dt_pytz = pytz_zone.localize(dt, is_dst=is_dst)
    with pytest.warns(PytzUsageWarning):
        dt_shim = shim_zone.localize(dt, is_dst=is_dst)

    assume_no_dst_inconsistency_bug(dt, key)
    assert_localized_equivalent(dt_shim, dt_pytz)


@hypothesis.given(dt=dt_strategy, key=valid_zone_strategy)
@hypothesis.example(dt=datetime(2018, 3, 25, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2018, 10, 28, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2018, 3, 25, 1, 30), key="Europe/Dublin")
@hypothesis.example(dt=datetime(2018, 10, 28, 1, 30), key="Europe/Dublin")
@hypothesis.example(dt=datetime(2004, 4, 4, 2, 30), key="America/New_York")
@hypothesis.example(dt=datetime(2004, 10, 31, 1, 30), key="America/New_York")
def test_localize_is_dst_none(dt, key):
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    pytz_exc = shim_exc = dt_pytz = dt_shim = None
    try:
        dt_pytz = pytz_zone.localize(dt, is_dst=None)
    except pytz.InvalidTimeError as e:
        pytz_exc = e

    with pytest.warns(PytzUsageWarning):
        try:
            dt_shim = shim_zone.localize(dt, is_dst=None)
        except pds.InvalidTimeError as e:
            shim_exc = e

    if dt_pytz:
        assume_no_dst_inconsistency_bug(dt, key, is_dst=False)
        assert_localized_equivalent(dt_pytz, dt_shim)

    if pytz_exc:
        assert repr(shim_exc) == repr(pytz_exc)
        assert str(shim_exc) == str(pytz_exc)
        assert isinstance(shim_exc, type(pytz_exc))


# Helper functions
def round_timedelta(td, nearest=timedelta(minutes=1)):
    """Truncates a timedelta to the nearest even multiple of `nearest`."""
    if td == ZERO:
        return td

    sign = td / abs(td)
    nearest *= sign
    return nearest * round(td / nearest)


def round_normalized(dt):
    offset = dt.utcoffset()
    if offset is None:
        return dt

    rounded_offset = round_timedelta(offset)
    if offset != rounded_offset:
        new_dt = dt + (rounded_offset - offset)
    else:
        new_dt = dt
    return pds._compat.enfold(new_dt, fold=dt.fold)


def assert_rounded_equal(actual, expected, **kwargs):
    actual_rounded = round_timedelta(actual, **kwargs)
    expected_rounded = round_timedelta(expected, **kwargs)

    assert actual_rounded == expected_rounded


def assert_localized_equivalent(actual, expected):
    actual_utc_offset = actual.utcoffset()
    actual_dst = actual.dst()

    expected_utc_offset = expected.utcoffset()
    expected_dst = expected.dst()

    assert_rounded_equal(actual_utc_offset, expected_utc_offset)
    assert_rounded_equal(actual_dst, expected_dst)
    assert actual.tzname() == expected.tzname()
    assert actual.replace(tzinfo=None) == expected.replace(tzinfo=None)


def assume_no_dst_inconsistency_bug(dt, key, is_dst=False):
    # pytz and zoneinfo have bugs around the correct value for dst(), see, e.g.
    # Until those are fixed, we'll use a rough heuristic to skip over these
    # "sore spots".

    uz = pds._compat.get_timezone(key)
    ###########
    # One-offs
    # bpo-40930: https://bugs.python.org/issue40930
    hypothesis.assume(
        not (
            key == "Pacific/Rarotonga"
            and datetime(1978, 11, 11) <= dt <= datetime(1991, 3, 2)
            and uz.dst(dt)
        )
    )
    hypothesis.assume(
        not (
            key == "America/Montevideo"
            and datetime(1923, 1, 1) <= dt <= datetime(1927, 1, 1)
            and uz.dst(dt)
        )
    )

    # Argentina switched from -03 (STD) to -03 (DST) to -03 (STD) during this
    # interval, for whatever reason. pytz calls this dst() == 0, zoneinfo calls
    # this dst() == 1:00.
    hypothesis.assume(
        not (
            key in _ARGENTINA_ZONES
            and datetime(1999, 10, 3) <= dt <= datetime(2000, 3, 3)
        )
    )

    # bpo-40933: https://bugs.python.org/issue40933
    hypothesis.assume(
        not (
            key == "Europe/Minsk"
            and datetime(1941, 6, 27) <= dt <= datetime(1943, 3, 30)
        )
    )

    ###########
    # Bugs around incorrect double DST
    # https://github.com/stub42/pytz/issues/44
    # bpo-40931: https://bugs.python.org/issue40931
    pz = pytz.timezone(key)
    dt_pytz = pz.localize(dt, is_dst=is_dst)
    dt_uz = dt.replace(fold=not is_dst, tzinfo=uz)
    if abs(dt_pytz.dst() <= timedelta(hours=1)) and abs(
        dt_uz.dst()
    ) <= timedelta(hours=1):
        return

    hypothesis.assume(dt_uz.dst() == dt_pytz.dst())
