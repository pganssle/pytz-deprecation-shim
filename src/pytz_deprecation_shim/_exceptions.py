from ._common import pytz_imported


class PytzUsageWarning(RuntimeWarning):
    pass


class InvalidTimeError(Exception):
    pass


class AmbiguousTimeError(InvalidTimeError):
    pass


class NonExistentTimeError(InvalidTimeError):
    pass


PYTZ_BASE_ERROR_MAPPING = {}


def _make_pytz_derived_errors(
    InvalidTimeError_=InvalidTimeError,
    AmbiguousTimeError_=AmbiguousTimeError,
    NonExistentTimeError_=NonExistentTimeError,
):
    if PYTZ_BASE_ERROR_MAPPING or not pytz_imported():
        return

    import pytz

    class InvalidTimeError(InvalidTimeError_, pytz.InvalidTimeError):
        pass

    class AmbiguousTimeError(AmbiguousTimeError_, pytz.AmbiguousTimeError):
        pass

    class NonExistentTimeError(
        NonExistentTimeError_, pytz.NonExistentTimeError
    ):
        pass

    PYTZ_BASE_ERROR_MAPPING.update(
        {
            InvalidTimeError_: InvalidTimeError,
            AmbiguousTimeError_: AmbiguousTimeError,
            NonExistentTimeError_: NonExistentTimeError,
        }
    )


def get_exception(exc_type, msg):
    _make_pytz_derived_errors()

    out_exc_type = PYTZ_BASE_ERROR_MAPPING.get(exc_type, exc_type)

    return out_exc_type(msg)
