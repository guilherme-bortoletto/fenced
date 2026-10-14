"""The only package that persists a record.

A write is planned in `plan`, carried out or simulated in `executor`, kept in `journal`,
and put back by `undo`. Simulating is the default everywhere a write can happen.
"""
