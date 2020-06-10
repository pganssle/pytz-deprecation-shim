try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

import datetime

UTC = datetime.timezone.utc


def get_timezone(key):
    try:
        return zoneinfo.ZoneInfo(key)
    except ValueError as e:
        raise KeyError(key) from e


def get_timezone_path(fpath, key=None):
    try:
        with open(fpath, "rb") as f:
            return zoneinfo.ZoneInfo.from_file(f, key=key)
    except IOError:
        pass

    raise zoneinfo.ZoneInfoNotFoundError(f"Unknown time zone file: {fpath}")


def get_fixed_offset_zone(offset):
    return datetime.timezone(datetime.timedelta(minutes=offset))


def is_imaginary(dt):
    dt_rt = dt.astimezone(UTC).astimezone(dt.tzinfo)

    return not (dt == dt_rt)


def is_ambiguous(dt):
    if is_imaginary(dt):
        return False

    wall_0 = dt
    wall_1 = dt.replace(fold=not dt.fold)

    # Ambiguous datetimes can only exist if the offset changes, so we don't
    # actually have to check whether dst() or tzname() are different.
    same_offset = wall_0.utcoffset() == wall_1.utcoffset()

    return not same_offset


def enfold(dt, fold=1):
    if dt.fold != fold:
        return dt.replace(fold=fold)
    else:
        return dt


def get_fold(dt):
    return dt.fold
