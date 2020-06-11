# -*- coding: utf-8 -*-
import base64
import io
import json
import os
import zlib
from datetime import datetime, timedelta

import attr

from ._common import (
    MAX_DATETIME,
    MIN_DATETIME,
    PY2,
    UTC,
    ZERO,
    get_fold,
    lru_cache,
    round_timedelta,
)

ONE_H = timedelta(hours=1)
ZONEINFO_DATA = None
ZONEINFO_DATA_VERSION = None


def _decode_tzinfo(data):
    raw_data = b"".join((s.encode() for s in data))
    decoded = base64.b64decode(raw_data)

    return zlib.decompress(decoded)


def _load_zoneinfo_json():
    global ZONEINFO_DATA
    global ZONEINFO_DATA_VERSION

    here = os.path.split(__file__)[0]
    data_file = os.path.join(here, "data", "zoneinfo_data.json")
    with open(data_file, "rt") as f:
        zi = json.load(f)

    ZONEINFO_DATA_VERSION = zi["metadata"]["version"]
    ZONEINFO_DATA = {
        key: _decode_tzinfo(data) for key, data in zi["data"].items()
    }


def get_zone_file_obj(key):
    if ZONEINFO_DATA is None:
        _load_zoneinfo_json()

    return io.BytesIO(ZONEINFO_DATA[key])


@lru_cache(None)
def get_unambiguous_cases():
    """Returns a list of unambiguous test cases for parameterization.

    The list has the form "key,dt,offset", where each value for transition
    is a ZoneTransition object.
    """
    cases = []

    def _add_case(key, dt, offset):
        if not MIN_DATETIME < dt < MAX_DATETIME:
            return

        cases.append((key, dt, offset))

    for key in ZoneDumpData.transition_keys():
        for transition in ZoneDumpData.load_transition_examples(key):
            _add_case(
                key,
                transition.transition - timedelta(days=2),
                transition.offset_before,
            )

            _add_case(
                key,
                transition.transition + timedelta(days=2),
                transition.offset_after,
            )

    for key, offset in ZoneDumpData.fixed_offset_zones():
        fixed_offset_cases = [
            (key, datetime(2000, 1, 1), offset),
            (key, datetime(2020, 2, 29), offset),
            (key, datetime(1900, 1, 1), offset),
            (key, datetime(2040, 1, 1), offset),
        ]

        for case in fixed_offset_cases:
            _add_case(*case)

    return tuple(cases)


@lru_cache(None)
def _get_folds_and_gaps():
    fold_cases = []
    gap_cases = []

    for key in ZoneDumpData.transition_keys():
        for transition in ZoneDumpData.load_transition_examples(key):
            if not MIN_DATETIME < transition.transition < MAX_DATETIME:
                continue

            if transition.fold:
                cases = fold_cases
            elif transition.gap:
                cases = gap_cases
            else:  # pragma: nocover
                continue

            cases.append([key, transition])

    return tuple(map(tuple, (fold_cases, gap_cases)))


@lru_cache(None)
def get_fold_cases():
    """Returns a list of test cases that involve an ambiguous time."""
    return _get_folds_and_gaps()[0]


@lru_cache(None)
def get_gap_cases():
    """Returns a list of test cases that involve an imaginary time."""
    return _get_folds_and_gaps()[1]


class ZoneDumpData(object):
    @classmethod
    def transition_keys(cls):
        return cls._get_zonedump().keys()

    @classmethod
    def load_transition_examples(cls, key):
        return cls._get_zonedump()[key]

    @classmethod
    def fixed_offset_zones(cls):
        if not cls._FIXED_OFFSET_ZONES:
            cls._populate_fixed_offsets()

        return cls._FIXED_OFFSET_ZONES.items()

    @classmethod
    def _get_zonedump(cls):
        if not cls._ZONEDUMP_DATA:
            cls._populate_zonedump_data()
        return cls._ZONEDUMP_DATA

    @classmethod
    def _populate_fixed_offsets(cls):
        cls._FIXED_OFFSET_ZONES = {
            "UTC": ZoneOffset("UTC", ZERO, ZERO),
        }

    @classmethod
    def _populate_zonedump_data(cls):
        def _Africa_Abidjan():
            LMT = ZoneOffset("LMT", timedelta(seconds=-968))
            GMT = ZoneOffset("GMT", ZERO)

            return [
                ZoneTransition(datetime(1912, 1, 1), LMT, GMT),
            ]

        def _Africa_Casablanca():
            P00_s = ZoneOffset("+00", ZERO, ZERO)
            P01_d = ZoneOffset("+01", ONE_H, ONE_H)
            P00_d = ZoneOffset("+00", ZERO, -ONE_H)
            P01_s = ZoneOffset("+01", ONE_H, ZERO)

            return [
                # Morocco sometimes pauses DST during Ramadan
                ZoneTransition(datetime(2018, 3, 25, 2), P00_s, P01_d),
                ZoneTransition(datetime(2018, 5, 13, 3), P01_d, P00_s),
                ZoneTransition(datetime(2018, 6, 17, 2), P00_s, P01_d),
                # On October 28th Morocco set standard time to +01,
                # with negative DST only during Ramadan
                ZoneTransition(datetime(2018, 10, 28, 3), P01_d, P01_s),
                ZoneTransition(datetime(2019, 5, 5, 3), P01_s, P00_d),
                ZoneTransition(datetime(2019, 6, 9, 2), P00_d, P01_s),
            ]

        def _America_Los_Angeles():
            LMT = ZoneOffset("LMT", timedelta(seconds=-28378), ZERO)
            PST = ZoneOffset("PST", timedelta(hours=-8), ZERO)
            PDT = ZoneOffset("PDT", timedelta(hours=-7), ONE_H)
            PWT = ZoneOffset("PWT", timedelta(hours=-7), ONE_H)
            PPT = ZoneOffset("PPT", timedelta(hours=-7), ONE_H)

            return [
                ZoneTransition(datetime(1883, 11, 18, 12, 7, 2), LMT, PST),
                ZoneTransition(datetime(1918, 3, 31, 2), PST, PDT),
                ZoneTransition(datetime(1918, 3, 31, 2), PST, PDT),
                ZoneTransition(datetime(1918, 10, 27, 2), PDT, PST),
                # Transition to Pacific War Time
                ZoneTransition(datetime(1942, 2, 9, 2), PST, PWT),
                # Transition from Pacific War Time to Pacific Peace Time
                ZoneTransition(datetime(1945, 8, 14, 16), PWT, PPT),
                ZoneTransition(datetime(1945, 9, 30, 2), PPT, PST),
                ZoneTransition(datetime(2015, 3, 8, 2), PST, PDT),
                ZoneTransition(datetime(2015, 11, 1, 2), PDT, PST),
                # After 2038: Rules continue indefinitely
                ZoneTransition(datetime(2450, 3, 13, 2), PST, PDT),
                ZoneTransition(datetime(2450, 11, 6, 2), PDT, PST),
            ]

        def _America_Santiago():
            LMT = ZoneOffset("LMT", timedelta(seconds=-16966), ZERO)
            SMT = ZoneOffset("SMT", timedelta(seconds=-16966), ZERO)
            N05 = ZoneOffset("-05", timedelta(seconds=-18000), ZERO)
            N04 = ZoneOffset("-04", timedelta(seconds=-14400), ZERO)
            N03 = ZoneOffset("-03", timedelta(seconds=-10800), ONE_H)

            return [
                ZoneTransition(datetime(1890, 1, 1), LMT, SMT),
                ZoneTransition(datetime(1910, 1, 10), SMT, N05),
                ZoneTransition(datetime(1916, 7, 1), N05, SMT),
                ZoneTransition(datetime(2008, 3, 30), N03, N04),
                ZoneTransition(datetime(2008, 10, 12), N04, N03),
                ZoneTransition(datetime(2040, 4, 8), N03, N04),
                ZoneTransition(datetime(2040, 9, 2), N04, N03),
            ]

        def _Asia_Tokyo():
            JST = ZoneOffset("JST", timedelta(seconds=32400), ZERO)
            JDT = ZoneOffset("JDT", timedelta(seconds=36000), ONE_H)

            # Japan had DST from 1948 to 1951, and it was unusual in that
            # the transition from DST to STD occurred at 25:00, and is
            # denominated as such in the time zone database
            return [
                ZoneTransition(datetime(1948, 5, 2), JST, JDT),
                ZoneTransition(datetime(1948, 9, 12, 1), JDT, JST),
                ZoneTransition(datetime(1951, 9, 9, 1), JDT, JST),
            ]

        def _Australia_Sydney():
            LMT = ZoneOffset("LMT", timedelta(seconds=36292), ZERO)
            AEST = ZoneOffset("AEST", timedelta(seconds=36000), ZERO)
            AEDT = ZoneOffset("AEDT", timedelta(seconds=39600), ONE_H)

            return [
                ZoneTransition(datetime(1895, 2, 1), LMT, AEST),
                ZoneTransition(datetime(1917, 1, 1, 0, 1), AEST, AEDT),
                ZoneTransition(datetime(1917, 3, 25, 2), AEDT, AEST),
                ZoneTransition(datetime(2012, 4, 1, 3), AEDT, AEST),
                ZoneTransition(datetime(2012, 10, 7, 2), AEST, AEDT),
                ZoneTransition(datetime(2040, 4, 1, 3), AEDT, AEST),
                ZoneTransition(datetime(2040, 10, 7, 2), AEST, AEDT),
            ]

        def _Europe_Dublin():
            LMT = ZoneOffset("LMT", timedelta(seconds=-1500), ZERO)
            DMT = ZoneOffset("DMT", timedelta(seconds=-1521), ZERO)
            IST_0 = ZoneOffset("IST", timedelta(seconds=2079), ONE_H)
            GMT_0 = ZoneOffset("GMT", ZERO, ZERO)
            BST = ZoneOffset("BST", ONE_H, ONE_H)
            GMT_1 = ZoneOffset("GMT", ZERO, -ONE_H)
            IST_1 = ZoneOffset("IST", ONE_H, ZERO)

            return [
                ZoneTransition(datetime(1880, 8, 2, 0), LMT, DMT),
                ZoneTransition(datetime(1916, 5, 21, 2), DMT, IST_0),
                ZoneTransition(datetime(1916, 10, 1, 3), IST_0, GMT_0),
                ZoneTransition(datetime(1917, 4, 8, 2), GMT_0, BST),
                ZoneTransition(datetime(2016, 3, 27, 1), GMT_1, IST_1),
                ZoneTransition(datetime(2016, 10, 30, 2), IST_1, GMT_1),
                ZoneTransition(datetime(2487, 3, 30, 1), GMT_1, IST_1),
                ZoneTransition(datetime(2487, 10, 26, 2), IST_1, GMT_1),
            ]

        def _Europe_Lisbon():
            WET = ZoneOffset("WET", ZERO, ZERO)
            WEST = ZoneOffset("WEST", ONE_H, ONE_H)
            CET = ZoneOffset("CET", ONE_H, ZERO)
            CEST = ZoneOffset("CEST", timedelta(seconds=7200), ONE_H)

            return [
                ZoneTransition(datetime(1992, 3, 29, 1), WET, WEST),
                ZoneTransition(datetime(1992, 9, 27, 2), WEST, CET),
                ZoneTransition(datetime(1993, 3, 28, 2), CET, CEST),
                ZoneTransition(datetime(1993, 9, 26, 3), CEST, CET),
                ZoneTransition(datetime(1996, 3, 31, 2), CET, WEST),
                ZoneTransition(datetime(1996, 10, 27, 2), WEST, WET),
            ]

        def _Europe_London():
            LMT = ZoneOffset("LMT", timedelta(seconds=-75), ZERO)
            GMT = ZoneOffset("GMT", ZERO, ZERO)
            BST = ZoneOffset("BST", ONE_H, ONE_H)

            return [
                ZoneTransition(datetime(1847, 12, 1), LMT, GMT),
                ZoneTransition(datetime(2005, 3, 27, 1), GMT, BST),
                ZoneTransition(datetime(2005, 10, 30, 2), BST, GMT),
                ZoneTransition(datetime(2043, 3, 29, 1), GMT, BST),
                ZoneTransition(datetime(2043, 10, 25, 2), BST, GMT),
            ]

        def _Pacific_Kiritimati():
            LMT = ZoneOffset("LMT", timedelta(seconds=-37760), ZERO)
            N1040 = ZoneOffset("-1040", timedelta(seconds=-38400), ZERO)
            N10 = ZoneOffset("-10", timedelta(seconds=-36000), ZERO)
            P14 = ZoneOffset("+14", timedelta(seconds=50400), ZERO)

            # This is literally every transition in Christmas Island history
            return [
                ZoneTransition(datetime(1901, 1, 1), LMT, N1040),
                ZoneTransition(datetime(1979, 10, 1), N1040, N10),
                # They skipped December 31, 1994
                ZoneTransition(datetime(1994, 12, 31), N10, P14),
            ]

        cls._ZONEDUMP_DATA = {
            "Africa/Abidjan": _Africa_Abidjan(),
            "Africa/Casablanca": _Africa_Casablanca(),
            "America/Los_Angeles": _America_Los_Angeles(),
            "America/Santiago": _America_Santiago(),
            "Australia/Sydney": _Australia_Sydney(),
            "Asia/Tokyo": _Asia_Tokyo(),
            "Europe/Dublin": _Europe_Dublin(),
            "Europe/Lisbon": _Europe_Lisbon(),
            "Europe/London": _Europe_London(),
            "Pacific/Kiritimati": _Pacific_Kiritimati(),
        }

    _ZONEDUMP_DATA = None
    _FIXED_OFFSET_ZONES = None


if PY2:
    td_converter = round_timedelta
else:
    td_converter = lambda x: x


@attr.s
class ZoneOffset(object):
    tzname = attr.ib(type=str)
    utcoffset = attr.ib(type=timedelta, converter=td_converter)
    dst = attr.ib(type=timedelta, default=ZERO, converter=td_converter)


@attr.s
class ZoneTransition(object):
    transition = attr.ib(type=datetime)
    offset_before = attr.ib(type=ZoneOffset)
    offset_after = attr.ib(type=ZoneOffset)

    @property
    def transition_utc(self):
        return (self.transition - self.offset_before.utcoffset).replace(
            tzinfo=UTC
        )

    @property
    def fold(self):
        """Whether this introduces a fold"""
        return self.offset_before.utcoffset > self.offset_after.utcoffset

    @property
    def gap(self):
        """Whether this introduces a gap"""
        return self.offset_before.utcoffset < self.offset_after.utcoffset

    @property
    def delta(self):
        return self.offset_after.utcoffset - self.offset_before.utcoffset

    @property
    def anomaly_start(self):
        if get_fold(self):
            return self.transition + self.delta
        else:
            return self.transition

    @property
    def anomaly_end(self):
        if not get_fold(self):
            return self.transition + self.delta
        else:
            return self.transition
