"""Every ops migration is one `datapilot migrate` applies: a file the migration pattern does not
match would be skipped without a word, in the integration job and on every learner's machine."""

from __future__ import annotations

from datapilot import db


def test_every_sql_file_in_the_migrations_folder_is_applied_in_order():
    on_disk = sorted(path.name for path in db.MIGRATIONS.iterdir() if path.is_file())
    applied = [path.name for path in db.migration_files()]
    skipped = sorted(set(on_disk) - set(applied))
    assert on_disk == applied, f"not matched by the migration pattern: {skipped}"
    numbers = [name[:3] for name in applied]
    assert len(numbers) == len(set(numbers)), f"two migrations share a number: {numbers}"
