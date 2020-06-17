import copy
import pickle
from datetime import datetime, timedelta, tzinfo

import hypothesis
import hypothesis.strategies as hst
import pytest
import pytz

import pytz_deprecation_shim as pds

from . import _zoneinfo_data
from ._common import (
    MAX_DATETIME,
    MIN_DATETIME,
    PY2,
    assert_dt_equivalent,
    assert_dt_offset,
    conditional_examples,
    datetime_unambiguous,
    dt_strategy,
    enfold,
    get_fold,
    offset_minute_strategy,
    round_normalized,
    valid_zone_strategy,
)

ONE_SECOND = timedelta(seconds=1)
ARBITRARY_KEY_STRATEGY = hst.from_regex("[a-zA-Z][a-zA-Z_]+(/[a-zA-Z_]+)+")


def _make_no_cache_timezone():
    if PY2:
        import dateutil.tz

        def no_cache_timezone(key, tz=dateutil.tz):
            return pds.wrap_zone(tz.gettz.nocache(key), key)

    else:
        try:
            import zoneinfo
        except ImportError:
            from backports import zoneinfo

        def no_cache_timezone(key, zoneinfo=zoneinfo):
            return pds.wrap_zone(zoneinfo.ZoneInfo.no_cache(key), key)

    return no_cache_timezone


no_cache_timezone = _make_no_cache_timezone()
del _make_no_cache_timezone


def test_fixed_offset_utc():
    """Tests that fixed_offset_timezone(0) always returns UTC."""
    assert pds.fixed_offset_timezone(0) is pds.UTC


@pytest.mark.parametrize("key", ["utc", "UTC"])
def test_timezone_utc_singleton(key):
    assert pds.timezone(key) is pds.UTC


@hypothesis.given(minutes=offset_minute_strategy.filter(lambda m: m != 0))
def test_str_fixed_offset(minutes):
    shim_zone = pds.fixed_offset_timezone(minutes)
    assert str(shim_zone) == repr(shim_zone)


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


def _skip_transition(key, zt):
    if not PY2:
        return False

    if key == "Europe/Dublin" and (
        zt.transition > datetime(1968, 1, 1)
        or zt.transition < datetime(1917, 1, 1)
    ):
        return True

    if key == "Africa/Casablanca" and zt.transition > datetime(2019, 1, 1):
        return True

    if key == "America/Santiago" and zt.transition < datetime(1912, 1, 1):
        return True

    return False


def _localize_fold_cases():
    cases = []

    def _add_case(key, dt, fold, offset, skip=False):
        case = (key, dt, fold, offset)

        if skip:
            case = pytest.param(*case, marks=pytest.mark.skip)

        cases.append(case)

    for key, zt in _zoneinfo_data.get_fold_cases():
        dt = zt.anomaly_start
        skip = _skip_transition(key, zt)
        _add_case(key, dt, 0, zt.offset_before, skip=skip)
        _add_case(key, dt, 1, zt.offset_after, skip=skip)

        dt = zt.anomaly_end - ONE_SECOND
        _add_case(key, dt, 0, zt.offset_before, skip=skip)
        _add_case(key, dt, 1, zt.offset_after, skip=skip)

    return tuple(cases)


@pytest.mark.parametrize("key, dt, fold, offset", _localize_fold_cases())
def test_localize_folds(key, dt, fold, offset):
    zone = pds.build_tzinfo(key, _zoneinfo_data.get_zone_file_obj(key))

    with pytest.warns(pds.PytzUsageWarning):
        dt_localized = zone.localize(enfold(dt, fold=fold))

    assert_dt_offset(dt_localized, offset)


def _localize_gap_cases():
    cases = []
    for key, zt in _zoneinfo_data.get_gap_cases():
        dt = zt.anomaly_start
        cases.append((key, dt, 0, zt.offset_before))
        cases.append((key, dt, 1, zt.offset_after))

        dt = zt.anomaly_end - ONE_SECOND
        cases.append((key, dt, 0, zt.offset_before))
        cases.append((key, dt, 1, zt.offset_after))

    return tuple(cases)


@pytest.mark.parametrize("key, dt, fold, offset", _localize_gap_cases())
@pytest.mark.skipif(
    PY2, reason="dateutil.tz doesn't properly support fold during gaps"
)
def test_localize_gap(key, dt, fold, offset):
    zone = pds.build_tzinfo(key, _zoneinfo_data.get_zone_file_obj(key))

    with pytest.warns(pds.PytzUsageWarning):
        dt_localized = zone.localize(enfold(dt, fold=fold))

    assert_dt_offset(dt_localized, offset)


def _folds_from_utc_cases():
    cases = []

    def _add_case(key, dt_utc, expected_fold, skip=False):
        case = (key, dt_utc, expected_fold)

        if skip:
            case = pytest.param(*case, marks=pytest.mark.skip)

        cases.append(case)

    for key, zt in _zoneinfo_data.get_fold_cases():
        dt_utc = zt.transition_utc
        dt_before_utc = dt_utc - ONE_SECOND
        dt_after_utc = dt_utc + ONE_SECOND

        skip = _skip_transition(key, zt)

        _add_case(key, dt_before_utc, 0, skip=skip)
        _add_case(key, dt_after_utc, 1, skip=skip)

    return tuple(cases)


@pytest.mark.parametrize("key, dt_utc, expected_fold", _folds_from_utc_cases())
def test_folds_from_utc(key, dt_utc, expected_fold):
    zone = pds.build_tzinfo(key, _zoneinfo_data.get_zone_file_obj(key))

    dt = dt_utc.astimezone(zone)
    assert get_fold(dt) == expected_fold


SHIM_ZONE_STRATEGY = hst.one_of(
    [
        valid_zone_strategy.map(pds.timezone),
        valid_zone_strategy.map(no_cache_timezone),
        offset_minute_strategy.map(pds.fixed_offset_timezone),
        hst.just(pds.UTC),
    ]
)


@hypothesis.given(shim_zone=SHIM_ZONE_STRATEGY)
def test_unwrap_shim(shim_zone):
    """Tests that .unwrap(_shim) always does the same as upgrade_tzinfo()."""
    assert shim_zone.unwrap_shim() is pds.helpers.upgrade_tzinfo(shim_zone)


@pytest.mark.skipif(
    PY2, reason="Currently dateutil does not have a .key attribute"
)
def test_wrap_zone_default_key():
    key = "America/New_York"
    zone = pds._compat.get_timezone(key)

    wrapped_zone = pds.wrap_zone(zone)

    assert str(wrapped_zone) == key


def test_wrap_zone_no_key():
    class TzInfo(tzinfo):
        def __init__(self):
            pass

    zone = TzInfo()

    with pytest.raises(TypeError):
        pds.wrap_zone(zone)


@hypothesis.given(shim_zone=SHIM_ZONE_STRATEGY)
def test_wrap_zone_same_object(shim_zone):
    """Tests unwrapping and rewrapping a shim zone.

    This should return the original shim object.
    """
    unwrapped = shim_zone.unwrap_shim()

    with pytest.warns(pds.PytzUsageWarning):
        key = shim_zone.zone

    rewrapped = pds.wrap_zone(unwrapped, key=key)

    assert rewrapped is shim_zone


@hypothesis.given(shim_zone=SHIM_ZONE_STRATEGY, key=ARBITRARY_KEY_STRATEGY)
def test_wrap_zone_new_key(shim_zone, key):
    """Test that wrap_zone can set arbitrary keys.

    There are a bunch of layers of caching here, so we want to make sure that
    if we wrap a zone that may already live in a cache with a new shim that has
    a different key, the new wrapper will reflect that, and the existing shim
    class won't be affected.
    """
    original_key = str(shim_zone)
    unwrapped = shim_zone.unwrap_shim()

    new_shim = pds.wrap_zone(unwrapped, key=key)

    assert str(new_shim) == key
    assert str(shim_zone) == original_key


@hypothesis.given(shim_zone=SHIM_ZONE_STRATEGY)
@pytest.mark.parametrize("copy_func", [copy.copy, copy.deepcopy,])
def test_copy(copy_func, shim_zone):
    shim_copy = copy_func(shim_zone)

    assert shim_copy is shim_zone


@hypothesis.given(shim_zone=SHIM_ZONE_STRATEGY, dt=dt_strategy)
@hypothesis.example(
    shim_zone=pds.timezone("America/New_York"), dt=datetime(2020, 11, 1, 1, 30)
)
@hypothesis.example(
    shim_zone=no_cache_timezone("America/New_York"),
    dt=datetime(2020, 11, 1, 1, 30),
)
@hypothesis.example(
    shim_zone=pds.timezone("America/New_York"),
    dt=enfold(datetime(2020, 11, 1, 1, 30), fold=1),
)
@conditional_examples(
    not PY2,
    examples=[
        hypothesis.example(
            shim_zone=no_cache_timezone("America/New_York"),
            dt=datetime(2020, 3, 8, 2, 30),
        ),
        hypothesis.example(
            shim_zone=no_cache_timezone("America/New_York"),
            dt=enfold(datetime(2020, 3, 8, 2, 30), fold=1),
        ),
    ],
)
def test_pickle_round_trip(shim_zone, dt):
    """Test that the results of a pickle round trip are identical to inputs.

    Ideally we would want some metric of equality on the pickled objects
    themselves, but with time zones object equality is usually equivalent to
    object identity, and that is not universally preserved in pickle round
    tripping on all Python versions and for all zones.
    """
    shim_copy = pickle.loads(pickle.dumps(shim_zone))

    dt = dt.replace(tzinfo=shim_zone)
    dt_rt = dt.replace(tzinfo=shim_copy)

    # PEP 495 says that the result of an inter-zone comparison between
    # datetimes where the offset depends on the fold is always False.
    if shim_zone is not shim_copy and dt != dt_rt:
        assert dt.dst() == dt_rt.dst()
        assert dt.utcoffset() == dt_rt.utcoffset()
        assert not datetime_unambiguous(dt)
        assert not datetime_unambiguous(dt_rt)
        return

    assert_dt_equivalent(dt, dt_rt)


@hypothesis.given(key=valid_zone_strategy)
@pytest.mark.skipif(PY2, reason="Singleton behavior is different in Python 2")
def test_pickle_returns_same_object(key):
    shim_zone = pds.timezone(key)

    shim_copy = pickle.loads(pickle.dumps(shim_zone))

    assert shim_zone is shim_copy


def test_utc_alias():
    assert pds.utc is pds.UTC
