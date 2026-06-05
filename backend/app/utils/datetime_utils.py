"""Datetime helpers for the application.

All DB columns in this project use ``DateTime(timezone=False)`` (naive
datetimes stored in UTC).  Use :func:`utcnow_naive` whenever you need
the current UTC time for a database column so that SQLAlchemy / the
database driver does not raise a timezone-mismatch error.

For JWT claims and other contexts that accept timezone-aware datetimes,
you can continue to use ``datetime.now(timezone.utc)`` directly.
"""

from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Return the current UTC time as a **naive** datetime (no tzinfo).

    This is the correct replacement for the deprecated
    ``datetime.utcnow()`` when the target column is
    ``DateTime(timezone=False)``.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
