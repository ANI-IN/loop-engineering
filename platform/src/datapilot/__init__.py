"""DataPilot: a production-safe, self-improving analytics agent built as four loops."""

__version__ = "0.1.0"

from datapilot import tests_database_guard as _tests_database_guard  # noqa: E402

# Under pytest no connection reaches any database but the tests' own (tests_database_guard.py).
if _tests_database_guard.under_pytest():
    _tests_database_guard.install()
