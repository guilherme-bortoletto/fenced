"""The command line, which builds the adapters and hands them to the core.

    fenced run                     read the inbox and show the plan, writing nothing
    fenced run --write             the same, and then write it and journal it as a run
    fenced undo N                  show what undoing run N would change
    fenced undo N --write          undo it

A run reads every message in the inbox, asks the extractor for the fields, and builds a
lead with the text the person wrote as its message. A message the boundary refuses is
handed back by its id with the reason, and the rest go on. For each lead the run prints the
next step the playbook names and the moment it is due, counted from when the message
arrived and read against the clock. Then it plans the write, prints the diff, and applies it
only when `--write` is passed. The id of a run is the number of the journal entry it wrote,
and `undo` takes that number.

The extractor is the fake one unless `--extractor model` is passed, so the default run needs
no key and no network. The store and the journal are files under `--store`, which is
`.fenced` unless told otherwise and which git leaves out.

This module opens no file and no socket itself. It reads the arguments, the environment and
the two streams it is handed, and everything else goes through an adapter.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import TextIO

from fenced.adapters.clock import ClockError, FixedClock, SystemClock
from fenced.adapters.fake_extractor import FakeExtractor
from fenced.adapters.json_crm import JsonCrm
from fenced.adapters.json_files import FileError
from fenced.adapters.json_inbox import JsonInbox
from fenced.adapters.json_journal import JsonJournal
from fenced.adapters.llm_extractor import LlmError, LlmExtractor, MissingKey
from fenced.domain.lead import Lead, LeadError
from fenced.domain.playbook import next_step
from fenced.ports.clock import Clock
from fenced.ports.extractor import Extractor
from fenced.ports.inbox import Message
from fenced.writes.executor import Outcome, WriteError, apply
from fenced.writes.journal import JournalError
from fenced.writes.plan import PlanError, key_of, plan
from fenced.writes.undo import undo

STORE = Path(".fenced")
INBOX = Path("examples/messages.json")
RECORDS = "store.json"
ENTRIES = "journal.jsonl"
EXTRACTORS: Mapping[str, Callable[[Mapping[str, str]], Extractor]] = {
    "fake": lambda environ: FakeExtractor(),
    "model": lambda environ: LlmExtractor(environ),
}
# The exit codes. A refusal is the core saying no, and a usage error is the command line
# being called wrongly, which is also what `argparse` exits with.
DONE, REFUSED, USAGE = 0, 1, 2


def parser() -> argparse.ArgumentParser:
    """The arguments both commands take."""
    top = argparse.ArgumentParser(prog="fenced", description="Read leads, plan the write, undo it.")
    commands = top.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="read the inbox and plan the write")
    run.add_argument("--inbox", type=Path, default=INBOX, help="the JSON file of messages")
    run.add_argument("--extractor", choices=sorted(EXTRACTORS), default="fake")
    run.add_argument("--now", help="the moment to read the windows against, as ISO 8601")
    back = commands.add_parser("undo", help="put back what one run changed")
    back.add_argument("run_id", type=int, metavar="RUN", help="the number a run was written as")
    for command in (run, back):
        command.add_argument("--store", type=Path, default=STORE, help="the folder of the store")
        command.add_argument("--write", action="store_true", help="write instead of simulating")
    return top


def _moment(text: str) -> datetime:
    """A moment out of ISO 8601 text. The adapters have already refused one with no offset."""
    return datetime.fromisoformat(text)


def _step_line(lead: Lead, message: Message, now: datetime) -> str:
    """The next step for one lead, when it is due, and whether that moment has passed."""
    step = next_step(lead.awareness)
    due = _moment(message["received_at"]) + timedelta(hours=step.window_hours)
    state = "late" if now > due else "open"
    return (
        f"  {lead.awareness.value}, next {step.action.value} within {step.window_hours} hours, "
        f"due {due.isoformat(timespec='seconds')}, {state}"
    )


def _show(outcome: Outcome, out: TextIO) -> None:
    """The diff an apply returned, indented under the plan."""
    for line in outcome.diff:
        print(f"  {line}" if line else "", file=out)


def _read(
    messages: Sequence[Message], extractor: Extractor, now: datetime, out: TextIO
) -> list[Lead]:
    """The leads among the messages, each one printed with its next step or its refusal."""
    leads = []
    for message in messages:
        fields = dict(extractor.extract(message["text"]))
        # What the person wrote is the message itself, whatever the extractor returned for it.
        fields["message"] = message["text"]
        try:
            lead = Lead.from_fields(fields)
        except LeadError as refused:
            print(f"message {message['id']} handed back, {refused}", file=out)
            continue
        print(f"message {message['id']} from {lead.name} <{lead.email}>", file=out)
        print(_step_line(lead, message, now), file=out)
        leads.append(lead)
    return leads


def _run(arguments: argparse.Namespace, environ: Mapping[str, str], out: TextIO) -> int:
    """Read the inbox, show every lead and its next step, then plan and maybe write."""
    extractor = EXTRACTORS[arguments.extractor](environ)
    clock: Clock = FixedClock(arguments.now) if arguments.now else SystemClock()
    now = _moment(clock.now())
    crm = JsonCrm(arguments.store / RECORDS)
    journal = JsonJournal(arguments.store / ENTRIES)
    leads = _read(JsonInbox(arguments.inbox).messages(), extractor, now, out)
    planned = plan(crm, leads)
    print("", file=out)
    if not planned.changes:
        print("nothing to write, the store holds every lead as it stands", file=out)
        return DONE
    print(f"plan for {len(planned.changes)} of {len(leads)} leads", file=out)
    outcome = apply(planned, crm, journal, really=arguments.write)
    _show(outcome, out)
    if outcome.simulated:
        print("simulated, nothing was written. Run it again with --write to write it.", file=out)
    else:
        print(f"written as run {outcome.entry}. Undo it with: fenced undo {outcome.entry}", file=out)
    return DONE


def _undo(arguments: argparse.Namespace, out: TextIO) -> int:
    """Show or carry out the undo of one run."""
    crm = JsonCrm(arguments.store / RECORDS)
    journal = JsonJournal(arguments.store / ENTRIES)
    outcome = undo(arguments.run_id, crm, journal, really=arguments.write)
    print(f"undo of run {arguments.run_id}", file=out)
    _show(outcome, out)
    if outcome.simulated:
        print("simulated, nothing was written. Run it again with --write to undo it.", file=out)
    elif outcome.entry is None:
        print("nothing to put back, the store already holds it", file=out)
    else:
        print(f"undone as run {outcome.entry}", file=out)
    return DONE


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Run one command and return its exit code.

    The arguments, the environment and the two streams are parameters, so a test hands in
    its own and the process is read only when they are left out.
    """
    environ = os.environ if environ is None else environ
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "run":
            return _run(arguments, environ, out)
        return _undo(arguments, out)
    except (MissingKey, ClockError) as stopped:
        print(stopped, file=err)
        return USAGE
    except (FileError, LlmError, PlanError, WriteError, JournalError) as refused:
        print(f"refused, {refused}", file=err)
        return REFUSED
