import os

import hypothesis

hypothesis.settings.register_profile("long", max_examples=5000)

hypothesis.settings.load_profile(os.getenv(u"HYPOTHESIS_PROFILE", "default"))
