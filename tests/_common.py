# -*- coding: utf-8 -*-
import sys
from datetime import datetime, timedelta

import pytz
from hypothesis import strategies as hst

PY2 = sys.version_info[0] == 2
VALID_ZONES = sorted(pytz.all_timezones)

# There will be known inconsistencies between pytz and the other libraries
# right around the EPOCHALYPSE, because V1 files use 32-bit integers, and
# pytz does not support V2+ files.
NEGATIVE_EPOCHALYPSE = datetime(1901, 12, 13, 15, 45, 52)
EPOCHALYPSE = datetime(2038, 1, 18, 22, 14, 8)

MIN_DATETIME = NEGATIVE_EPOCHALYPSE + timedelta(days=365)
MAX_DATETIME = EPOCHALYPSE - timedelta(days=365)

valid_zone_strategy = hst.sampled_from(VALID_ZONES)
dt_strategy = hst.datetimes(min_value=MIN_DATETIME, max_value=MAX_DATETIME)
