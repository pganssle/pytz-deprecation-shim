.. module:: pytz_deprecation_shim

API Reference
=============

.. data:: UTC

    The UTC singleton (with an alias at ``utc``) is a shim class wrapping
    either ``datetime.timezone.utc`` or ``dateutil.tz.UTC``.

.. autofunction:: timezone(key)

.. autofunction:: fixed_offset_timezone(offset)

.. autofunction:: build_tzinfo(zone, fp)

.. autofunction:: wrap_zone(tz, key=...)


Exceptions
----------

.. autoexception:: PytzUsageWarning

``pytz`` shim exceptions
########################

These exceptions are intended to mirror at least some of ``pytz``'s exception
hierarchy. The shim classes are designed in such a way that the exception
classes they raise can be caught *either* by catching the value in
``pytz_deprecation_shim`` or the equivalent exception in ``pytz`` (the actual
exception type raised will depend on whether or not ``pytz`` has been imported,
but the value will either be one of the shim exceptions or a subclass of both
the shim exception and its ``pytz`` equivalent).

.. autoexception:: InvalidTimeError
.. autoexception:: AmbiguousTimeError
.. autoexception:: NonExistentTimeError
.. autoexception:: UnknownTimeZoneError
