"""Compatibility exports for branches that still import ``message_utils``.

The canonical implementation now lives in ``message_serialization``.
"""

from code_puppy.api.db.message_serialization import *  # noqa: F403
