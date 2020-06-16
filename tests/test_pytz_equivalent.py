# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import hypothesis
import pytest
import pytz
from hypothesis import strategies as hst

import pytz_deprecation_shim as pds
from pytz_deprecation_shim import PytzUsageWarning

from ._common import (
    MAX_DATETIME,
    MIN_DATETIME,
    PY2,
    UTC,
    ZERO,
    assert_dt_equivalent,
    conditional_examples,
    dt_strategy,
    enfold,
    get_fold,
    offset_minute_strategy,
    round_timedelta,
    valid_zone_strategy,
)

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
    dt=enfold(datetime(2010, 11, 7, 1, 30), fold=1),
    key="America/New_York",
    is_dst=True,
)
@hypothesis.example(
    dt=enfold(datetime(2010, 11, 7, 1, 30), fold=1),
    key="America/New_York",
    is_dst=False,
)
@hypothesis.example(
    dt=datetime(2010, 11, 7, 1, 30), key="America/New_York", is_dst=True
)
@hypothesis.example(
    dt=datetime(2010, 11, 7, 1, 30), key="America/New_York", is_dst=False
)
@conditional_examples(
    not PY2,
    [
        hypothesis.example(
            dt=datetime(2009, 3, 29, 2), key="Europe/Amsterdam", is_dst=True
        ),
        hypothesis.example(
            dt=enfold(datetime(1933, 1, 1), fold=0),
            key="Asia/Kuching",
            is_dst=True,
        ),
        hypothesis.example(
            dt=enfold(datetime(1933, 1, 1), fold=1),
            key="Asia/Kuching",
            is_dst=True,
        ),
        hypothesis.example(
            dt=enfold(datetime(1933, 1, 1), fold=0),
            key="Asia/Kuching",
            is_dst=False,
        ),
        hypothesis.example(
            dt=enfold(datetime(1933, 1, 1), fold=1),
            key="Asia/Kuching",
            is_dst=False,
        ),
    ],
)
def test_localize_explicit_is_dst(dt, key, is_dst):
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    dt_pytz = pytz_zone.localize(dt, is_dst=is_dst)
    with pytest.warns(PytzUsageWarning):
        dt_shim = shim_zone.localize(dt, is_dst=is_dst)

    assume_no_dst_inconsistency_bug(dt, key)
    assert_dt_equivalent(dt_shim, dt_pytz)


@hypothesis.given(dt=dt_strategy, key=valid_zone_strategy)
@hypothesis.example(dt=datetime(2018, 3, 25, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2018, 10, 28, 1, 30), key="Europe/London")
@hypothesis.example(dt=datetime(2004, 4, 4, 2, 30), key="America/New_York")
@hypothesis.example(dt=datetime(2004, 10, 31, 1, 30), key="America/New_York")
@conditional_examples(
    not PY2,
    examples=[
        hypothesis.example(
            dt=datetime(2018, 3, 25, 1, 30), key="Europe/Dublin"
        ),
        hypothesis.example(
            dt=datetime(2018, 10, 28, 1, 30), key="Europe/Dublin"
        ),
    ],
)
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

    # This section is triggered rarely. It currently occurs in Python 3 when
    # key = "Africa/Abidjan" and dt is 1912-01-01.
    if (dt_pytz is None) != (dt_shim is None):  # pragma: nocover
        uz = pds._compat.get_timezone(key)

        utc_off = uz.utcoffset(dt)
        hypothesis.assume(utc_off == round_timedelta(utc_off))

        utc_off_folded = uz.utcoffset(enfold(dt, fold=not get_fold(dt)))
        hypothesis.assume(utc_off_folded == round_timedelta(utc_off_folded))

    if dt_pytz:
        assume_no_dst_inconsistency_bug(dt, key, is_dst=False)
        assert_dt_equivalent(dt_pytz, dt_shim)

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

    dt_pytz = pytz_zone.localize(dt, is_dst=not get_fold(dt))
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
    assume_no_dst_inconsistency_bug(dt + delta, key)
    assert_dt_equivalent(dt_pytz_after, dt_shim_after, round_dates=True)


@hypothesis.given(dt=dt_strategy, offset=offset_minute_strategy)
@hypothesis.example(dt=datetime(2020, 1, 1), offset=0)
@hypothesis.example(dt=datetime(2020, 2, 29), offset=0)
@hypothesis.example(dt=datetime(2020, 2, 29), offset=-1439)
@hypothesis.example(dt=datetime(2020, 2, 29), offset=1439)
def test_localize_fixed_offset(dt, offset):
    pytz_zone = pytz.FixedOffset(offset)
    shim_zone = pds.fixed_offset_timezone(offset)

    dt_pytz = pytz_zone.localize(dt)
    with pytest.warns(pds.PytzUsageWarning):
        dt_shim = shim_zone.localize(dt)

    assert dt_pytz == dt_shim
    assert dt_pytz.utcoffset() == dt_shim.utcoffset()


@hypothesis.given(key=valid_zone_strategy)
def test_zone_attribute(key):
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    pytz_zone_value = pytz_zone.zone
    with pytest.warns(PytzUsageWarning):
        shim_zone_value = shim_zone.zone

    assert pytz_zone_value == shim_zone_value


@hypothesis.given(key=valid_zone_strategy)
def test_str(key):
    pytz_zone = pytz.timezone(key)
    shim_zone = pds.timezone(key)

    assert str(pytz_zone) == str(shim_zone)


def assume_no_dst_inconsistency_bug(dt, key, is_dst=False):  # prama: nocover
    # pytz and zoneinfo have bugs around the correct value for dst(), see, e.g.
    # Until those are fixed, we'll try to avoid these "sore spots" with a
    # combination of one-offs and rough heuristics.

    if len(key) == 3 and key.lower() == "utc":
        uz = pds._compat.UTC
    else:
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

        # Possibly another manifestation of dateutil/dateutil#1050
        hypothesis.assume(
            not (
                (key == "MET" or key == "CET")
                and datetime(1916, 5, 1) <= dt <= datetime(1916, 10, 2)
            )
        )

        # dateutil isn't currently up to PEP 495's spec during ambiguous times,
        # which means occasionally it's an ambiguous time and neither side is
        # DST.
        from dateutil import tz

        hypothesis.assume(tz.datetime_exists(dt, uz))

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
            (
                key == "America/Louisville"
                or key == "America/Kentucky/Louisville"
                or key == "America/Indiana/Marengo"
            )
            and datetime(1974, 1, 6) <= dt <= datetime(1974, 10, 28)
        )
    )

    # Same deal with the RussiaAsia rule in 1991, a transition to DST with no
    # corresponding change in the offset, then a transition bac
    hypothesis.assume(
        not (
            key == "Asia/Qyzylorda"
            and datetime(1991, 3, 31) <= dt <= datetime(1991, 9, 30)
        )
    )

    # Issue with pytz: Europe/Paris went from CEST (+2, STD) → CEST (+2, DST) →
    # WEMT (+2, DST) → WEST (+1, DST) → WEMT (+2, DST) → CET (+1, STD) between
    # 3 April 1944 and 16 September 1945. pytz doesn't detect that WEMT is a
    # DST zone, though.
    hypothesis.assume(
        not (
            key == "Europe/Paris"
            and datetime(1944, 10, 8) <= dt <= datetime(1945, 4, 3)
        )
    )

    ###########
    # Bugs around incorrect double DST
    # https://github.com/stub42/pytz/issues/44
    # bpo-40931: https://bugs.python.org/issue40931
    pz = pytz.timezone(key)
    dt_pytz = pz.localize(dt, is_dst=is_dst)
    dt_uz = dt.replace(tzinfo=uz)
    dt_uz = enfold(dt_uz, fold=not is_dst)
    if abs(dt_pytz.dst()) <= timedelta(hours=1) and abs(
        dt_uz.dst() or timedelta(0)
    ) <= timedelta(hours=1):
        return

    hypothesis.assume(dt_uz.dst() == dt_pytz.dst())
