import warnings
from datetime import tzinfo

from . import _compat
from ._exceptions import (
    AmbiguousTimeError,
    NonExistentTimeError,
    PytzUsageWarning,
    UnknownTimeZoneError,
    get_exception,
)

IS_DST_SENTINEL = object()


def timezone(key, _cache={}):
    instance = _cache.get(key, None)
    if instance is None:
        instance = _cache.setdefault(key, _PytzShimTimezone(key))

    return instance


def fixed_offset_timezone(offset, _cache={}):
    if not (-1440 < offset < 1440):
        raise ValueError("absolute offset is too large", offset)

    instance = _cache.get(offset, None)
    if instance is None:
        if offset == 0:
            instance = _cache.setdefault(offset, UTC)
        else:
            instance = _cache.setdefault(offset, _FixedOffsetShim(offset))

    return instance


class _BasePytzShimTimezone(tzinfo):
    def __init__(self, zone, key):
        self._key = key
        self._zone = zone

    def utcoffset(self, dt):
        return self._zone.utcoffset(dt)

    def dst(self, dt):
        return self._zone.dst(dt)

    def tzname(self, dt):
        return self._zone.tzname(dt)

    def fromutc(self, dt):
        # The default fromutc implementation only works if tzinfo is "self"
        dt_base = dt.replace(tzinfo=self._zone)
        dt_out = self._zone.fromutc(dt_base)

        return dt_out.replace(tzinfo=self)

    def __str__(self):
        return str(self._key)

    def __repr__(self):
        return "%s(%s, %s)" % (
            self.__class__.__name__,
            repr(self._zone),
            repr(self._key),
        )

    @property
    def zone(self):
        warnings.warn(
            "The zone attribute is specific to pytz's interface; "
            + "please migrate to a new time zone provider. "
            + "For more details on how to do so, see %s"
            % PYTZ_MIGRATION_GUIDE_URL,
            PytzUsageWarning,
        )

        return self._key

    def localize(self, dt, is_dst=IS_DST_SENTINEL):
        warnings.warn(
            "The localize method is no longer necessary, as this "
            + "time zone supports the fold attribute(PEP 495). "
            + "For more details on migrating to a PEP 495-compliant "
            + "implementation, see %s" % PYTZ_MIGRATION_GUIDE_URL,
            PytzUsageWarning,
        )

        if dt.tzinfo is not None:
            raise ValueError("Not naive datetime (tzinfo is already set)")

        dt_out = dt.replace(tzinfo=self)

        if is_dst is IS_DST_SENTINEL:
            return dt_out

        dt_ambiguous = _compat.is_ambiguous(dt_out)
        dt_imaginary = (
            _compat.is_imaginary(dt_out) if not dt_ambiguous else False
        )

        if is_dst is None:
            if dt_imaginary:
                raise get_exception(
                    NonExistentTimeError, dt.replace(tzinfo=None)
                )

            if dt_ambiguous:
                raise get_exception(AmbiguousTimeError, dt.replace(tzinfo=None))

        elif dt_ambiguous or dt_imaginary:
            dst_side = dt_out.dst()

            if not _compat.get_fold(dt_out):
                dst_side = not dst_side
            else:
                # If dt_out.fold is set to 1, the fold value that
                # corresponds to dst is the opposite of the dt_out.dst()
                dst_side = bool(dst_side)

            if is_dst:
                fold = dst_side
            else:
                fold = not dst_side

            dt_out = _compat.enfold(dt_out, fold=int(fold))

        return dt_out

    def normalize(self, dt):
        warnings.warn(
            "The normalize method is no longer necessary, as this "
            + "time zone supports the fold attribute(PEP 495). "
            + "For more details on migrating to a PEP 495-compliant "
            + "implementation, see %s" % PYTZ_MIGRATION_GUIDE_URL,
            PytzUsageWarning,
        )

        if dt.tzinfo is None:
            raise ValueError("Naive time - no tzinfo set")

        if dt.tzinfo is self:
            return dt

        return dt.astimezone(self)


class _PytzShimTimezone(_BasePytzShimTimezone):
    def __init__(self, key):
        try:
            zone = _compat.get_timezone(key)
        except KeyError:
            raise get_exception(UnknownTimeZoneError, key)

        super(_PytzShimTimezone, self).__init__(zone=zone, key=key)


class _FixedOffsetShim(_BasePytzShimTimezone):
    def __init__(self, offset):
        zone = _compat.get_fixed_offset_zone(offset)
        super(_FixedOffsetShim, self).__init__(zone=zone, key=None)


UTC = _BasePytzShimTimezone(_compat.UTC, "UTC")
PYTZ_MIGRATION_GUIDE_URL = "<TBD>"
