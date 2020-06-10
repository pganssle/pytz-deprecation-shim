# -*- coding: utf-8 -*-
import sys
from datetime import datetime, timedelta

import hypothesis
import pytest
import pytz
from hypothesis import strategies as hst

import pytz_deprecation_shim as pds
from pytz_deprecation_shim import PytzUsageWarning

PY2 = sys.version_info[0] == 2

VALID_ZONES = sorted(pytz.all_timezones)

NEGATIVE_EPOCHALYPSE = datetime(1901, 12, 13, 15, 45, 52)
EPOCHALYPSE = datetime(2038, 1, 18, 22, 14, 8)

# There will be known inconsistencies between pytz and the other libraries
# right around the EPOCHALYPSE, because V1 files use 32-bit integers, and
# pytz does not support V2+ files.
MIN_DATETIME = NEGATIVE_EPOCHALYPSE + timedelta(days=365)
MAX_DATETIME = EPOCHALYPSE - timedelta(days=365)

valid_zone_strategy = hst.sampled_from(VALID_ZONES)
dt_strategy = hst.datetimes(min_value=MIN_DATETIME, max_value=MAX_DATETIME)
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

UTC = pds._compat.UTC


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


def _dublin_examples():
    if PY2:

        def _(f):
            return f

    else:

        def _(f):
            examples = [
                hypothesis.example(
                    dt=datetime(2018, 3, 25, 1, 30), key="Europe/Dublin"
                ),
                hypothesis.example(
                    dt=datetime(2018, 10, 28, 1, 30), key="Europe/Dublin"
                ),
            ]

            f_out = f
            for example in examples:
                f_out = example(f_out)
            return f_out

    return _


@hypothesis.given(dt=dt_strategy, key=valid_zone_strategy)
@hypothesis.example(dt=datetime(2018, 3, 25, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2018, 10, 28, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2004, 4, 4, 2, 30), key="America/New_York")
@hypothesis.example(dt=datetime(2004, 10, 31, 1, 30), key="America/New_York")
@_dublin_examples()
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


@hypothesis.given(
    dt=dt_strategy,
    delta=hst.timedeltas(
        min_value=timedelta(days=-730), max_value=timedelta(days=730)
    ),
    key=valid_zone_strategy,
)
def test_normalize_same_zone(dt, delta, key):
    """Test normalization after arithmetic.

    NOTE: There is actually a difference in semantics here, because with pytz
    zones, adding a timedelta and normalizing gives you absolute time
    arithmetic, not wall-time arithmetic. To emulate this, we do the addition
    of the shimmed zone in UTC.
    """
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    dt_pytz = pytz_zone.localize(dt, is_dst=not pds._compat.get_fold(dt))
    dt_shim = dt.replace(tzinfo=shim_zone)

    hypothesis.assume(dt_pytz == dt_shim)

    dt_pytz_after_nn = dt_pytz + delta
    dt_shim_after_nn = (dt_shim.astimezone(UTC) + delta).astimezone(shim_zone)

    hypothesis.assume(
        MIN_DATETIME < dt_pytz_after_nn.replace(tzinfo=None) < MAX_DATETIME
    )

    dt_pytz_after = pytz_zone.normalize(dt_pytz_after_nn)

    with pytest.warns(PytzUsageWarning):
        dt_shim_after = shim_zone.normalize(dt_shim_after_nn)

    assert dt_shim_after_nn is dt_shim_after
    assume_no_dst_inconsistency_bug(dt, key)
    assert_localized_equivalent(dt_pytz_after, dt_shim_after)


# Helper functions
def round_timedelta(td, nearest=timedelta(minutes=1)):
    """Truncates a timedelta to the nearest even multiple of `nearest`."""
    if td == ZERO:
        return td

    tds = td.total_seconds()
    sign = tds / abs(tds)
    nearest *= int(sign)
    return nearest * int(round(tds / nearest.total_seconds()))


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
    # There are too many inconsistencies and bugs in the calculation of dst()
    # in all three time zone libraries, so for the purposes of the shim, we
    # will be satisfied as long as the truthiness of the dst() calls is the
    # same between the two.
    # TODO: Uncomment this line when we've ironed out the bugs:
    # assert_rounded_equal(actual_dst, expected_dst)
    assert bool(actual_dst) == bool(expected_dst)

    assert actual.tzname() == expected.tzname()
    assert actual.replace(tzinfo=None) == expected.replace(tzinfo=None)


def assume_no_dst_inconsistency_bug(dt, key, is_dst=False):
    # pytz and zoneinfo have bugs around the correct value for dst(), see, e.g.
    # Until those are fixed, we'll try to avoid these "sore spots" with a
    # combination of one-offs and rough heuristics.

    uz = pds._compat.get_timezone(key)
    ###########
    # One-offs
    if PY2:
        # https://github.com/dateutil/dateutil/issues/1048
        hypothesis.assume(
            uz.dst(dt)
            or not ((uz.dst(dt + timedelta(hours=24)) or ZERO) < ZERO)
        )

        # https://github.com/dateutil/dateutil/issues/1049
        hypothesis.assume(
            not (
                key == "Asia/Colombo"
                and datetime(1942, 1, 5) <= dt <= datetime(1945, 10, 17)
            )
        )

        # https://github.com/dateutil/dateutil/issues/1050
        hypothesis.assume(
            not (
                key == "America/Iqaluit"
                and datetime(1942, 7, 31) <= dt <= datetime(1945, 10, 1)
            )
        )

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
            and (
                datetime(1923, 1, 1) <= dt <= datetime(1927, 1, 1)
                or datetime(1942, 12, 14) <= dt <= datetime(1943, 3, 13)
            )
            and uz.dst(dt)
        )
    )

    # Argentina switched from -03 (STD) to -03 (DST) to -03 (STD) during this
    # interval, for whatever reason. pytz calls this dst() == 0, zoneinfo calls
    # this dst() == 1:00.
    hypothesis.assume(
        not (
            key in _ARGENTINA_ZONES
            and datetime(1999, 10, 3) <= dt <= datetime(2000, 3, 4)
        )
    )

    # bpo-40933: https://bugs.python.org/issue40933
    hypothesis.assume(
        not (
            key == "Europe/Minsk"
            and datetime(1941, 6, 27) <= dt <= datetime(1943, 3, 30)
        )
    )

    # Issue with pytz: America/Louisville transitioned from EST→CDT→EST in
    # 1974, but `pytz` returns timedelta(0) for CDT.
    hypothesis.assume(
        not (
            key == "America/Louisville"
            and datetime(1974, 1, 6) <= dt <= datetime(1974, 10, 28)
        )
    )

    ###########
    # Bugs around incorrect double DST
    # https://github.com/stub42/pytz/issues/44
    # bpo-40931: https://bugs.python.org/issue40931
    pz = pytz.timezone(key)
    dt_pytz = pz.localize(dt, is_dst=is_dst)
    dt_uz = dt.replace(tzinfo=uz)
    dt_uz = pds._compat.enfold(dt_uz, fold=not is_dst)
    if abs(dt_pytz.dst()) <= timedelta(hours=1) and abs(
        dt_uz.dst() or timedelta(0)
    ) <= timedelta(hours=1):
        return

    hypothesis.assume(dt_uz.dst() == dt_pytz.dst())
