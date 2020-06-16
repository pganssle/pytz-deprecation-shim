# -*- coding: utf-8 -*-
import sys
from datetime import datetime, timedelta

import pytz
from hypothesis import strategies as hst

import pytz_deprecation_shim as pds

# Opportunistically bring in lru_cache, with a no-op if it's unavailable
# available
try:
    from functools import lru_cache
except ImportError:

    def lru_cache(maxsize):
        del maxsize

        def _(f):
            return f

        return _


PY2 = sys.version_info[0] == 2
ZERO = timedelta(0)
UTC = pds._compat.UTC

VALID_ZONES = sorted(pytz.all_timezones)
VALID_ZONE_SET = set(VALID_ZONES)

# There will be known inconsistencies between pytz and the other libraries
# right around the EPOCHALYPSE, because V1 files use 32-bit integers, and
# pytz does not support V2+ files.
NEGATIVE_EPOCHALYPSE = datetime(1901, 12, 13, 15, 45, 52)
EPOCHALYPSE = datetime(2038, 1, 18, 22, 14, 8)

MIN_DATETIME = NEGATIVE_EPOCHALYPSE + timedelta(days=365)
MAX_DATETIME = EPOCHALYPSE - timedelta(days=365)

MAX_OFFSET_MINUTES = 24 * 60 - 1  # pytz's range is (-1 day, 1 day)

valid_zone_strategy = hst.sampled_from(VALID_ZONES)
invalid_zone_strategy = hst.text().filter(lambda t: t not in VALID_ZONE_SET)
dt_strategy = hst.datetimes(min_value=MIN_DATETIME, max_value=MAX_DATETIME)
offset_minute_strategy = hst.integers(
    min_value=-MAX_OFFSET_MINUTES, max_value=MAX_OFFSET_MINUTES
)
invalid_offset_minute_strategy = hst.one_of(
    [
        hst.integers(max_value=-(MAX_OFFSET_MINUTES + 1)),
        hst.integers(min_value=(MAX_OFFSET_MINUTES + 1)),
    ]
)

# Helper functions
enfold = pds._compat.enfold
get_fold = pds._compat.get_fold


def datetime_unambiguous(dt):
    return dt.utcoffset() == enfold(dt, fold=not get_fold(dt)).utcoffset()


@lru_cache(128)
def round_timedelta(td):
    """Truncates a timedelta to the nearest minute."""
    if td == ZERO:
        return td

    tds = td.total_seconds()
    rounded = int((tds + 30) // 60) * 60
    return timedelta(seconds=rounded)


def round_normalized(dt):
    offset = dt.utcoffset()

    rounded_offset = round_timedelta(offset)
    if offset != rounded_offset:
        new_dt = dt + (rounded_offset - offset)
    else:
        new_dt = dt
    return enfold(new_dt, fold=pds._compat.get_fold(dt))


def assert_rounded_equal(actual, expected, **kwargs):
    actual_rounded = round_timedelta(actual, **kwargs)
    expected_rounded = round_timedelta(expected, **kwargs)

    assert actual_rounded == expected_rounded


def assert_dt_equivalent(actual, expected, round_dates=False):
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
    if round_dates:
        actual_naive = round_normalized(actual).replace(tzinfo=None)
        expected_naive = round_normalized(expected).replace(tzinfo=None)
    else:
        actual_naive = actual.replace(tzinfo=None)
        expected_naive = expected.replace(tzinfo=None)

    assert actual_naive == expected_naive


def assert_dt_offset(dt, offset):
    assert dt.tzname() == offset.tzname
    assert dt.utcoffset() == offset.utcoffset
    assert dt.dst() == offset.dst


def conditional_examples(cond, examples):
    if not cond:

        def _(f):
            return f

    else:

        def _(f):
            f_out = f
            for example in examples:
                f_out = example(f_out)
            return f_out

    return _
