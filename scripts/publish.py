"""Publish a pull request body to GitHub through a plain REST call.

A body is public text. It leaves this machine once, exactly as it was written, and it
is never edited afterwards. Editing is what writes the version before the edit into the
history of the body, where it stays for good, so a line appended by a publishing tool
and then removed is a line this repository published and kept.

This script is the one way out. It reads the title and the body from files, runs the
text gate over both, and posts them with `urllib.request`. Nothing sits between the
file and the wire, so nothing can append to it.

    python scripts/publish.py --owner OWNER --repo REPO --head BRANCH --base main \
        --title-file TITLE --body-file BODY

It runs on a workflow runner and not on the machine a night run works in. Nothing in
here can tell the difference, and that is the point. The path out of that machine
appends a line of its own after the gate has read the file, so the file travels to
GitHub as a commit on a branch and the call is made from the other end.

Before it posts it reads the issue number twice, once off the head branch name and once
off the first line of the body. The two files live on `main`, so every branch inherits
the text of the run before it at the moment it is cut, and the first push of a run finds
a body written for another issue. That body passes the text gate, because it was written
to pass it. The number is what tells them apart.

When the two numbers differ this publishes nothing, says which issue each one names, and
exits zero. That is the first push of every run, and a red that fires on the ordinary
case is a red a reader learns to walk past. Two things stay loud, because neither one
happens on an ordinary push. A body that does not open with `Closes #N` at all, and a
head branch that names no issue.

A number that agrees is not enough on its own. A run may continue a branch that already
wrote its own body, and the first push of that run carries a body naming the right issue
that the run has not touched yet. So before it posts this also asks GitHub whether the push
it runs for changed the body file, comparing the commit before the push with the commit after
it. A push that left the body as it was publishes nothing, says so and exits zero. A push
that creates the branch is compared against the base branch instead, because there is no
commit before it. That decision is docs/adr/0023-a-body-is-published-by-the-push-that-wrote-it.md

Before it posts it asks GitHub whether the branch already has a pull request. A branch
is pushed many times in one run and the workflow runs on each push. The push that
carries this run's own body opens the pull request. Every push after it publishes
nothing, which is what writing a body once means when the trigger repeats.

The token arrives in GITHUB_TOKEN or in GH_TOKEN and is never written down here. Which
account is behind it is not written down either, so this asks GitHub and prints the login
it gets back. A squash merge takes the author of the pull request, so the account that
opened one is the account a commit on `main` ends up carrying. A workflow token has no
person behind it and GitHub names no account for it, and that answer is printed as well.
A run that fell back to the workflow token says so on the line it prints.

That line narrates. What is checked is the author GitHub stored on the pull request, read
off the answer this already reads, against the account named in PR_ACCOUNT. When the two
differ the pull request stays open and the run exits nonzero, so the work reaches review
and the red job is what a person sees. When PR_ACCOUNT is empty nothing is compared and the
run says so, because a clone with no secret and no variable still has to publish. That
decision is docs/adr/0022-a-pull-request-that-carries-another-account-turns-the-job-red.md

After the call the script reads the pull request back and compares it to what it sent.
That read is a check and not a repair. When the two disagree it says so and stops, and
the body on GitHub stays as it is, because an edit would be the second version this is
here to prevent.

There is no route in here that changes a body that already exists. That absence is the
point of the file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gates  # noqa: E402  the gate lives next to this file, and scripts is not a package

API = "https://api.github.com"
TOKEN_NAMES = ("GITHUB_TOKEN", "GH_TOKEN")
# The account a pull request is meant to carry. A login is public, so it is a repository
# variable and not a secret, and a clone that never set it reads the empty string.
EXPECTED = "PR_ACCOUNT"
TIMEOUT = 30
API_VERSION = "2022-11-28"
AGENT = "fenced"
# The issue a head branch names and the issue a body closes. A run picks one issue, names
# its branch after it and writes `Closes #N` on the first line of the body from the same
# number. Two readings of one number, and they agree only on text written for this run.
BRANCH_ISSUE = re.compile(r"^claude/issue-(\d+)$")
BODY_ISSUE = re.compile(r"^Closes #(\d+)$")
# The file a run writes its body into, as a path in the repository. The workflow hands the
# publisher this file, and a push that did not change it did not write the body it holds.
BODY_PATH = ".github/pull-request/body.md"
# A commit as a push event names it. A push that creates a branch names no commit before it
# and sends forty zeros in its place.
COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
NO_COMMIT = re.compile(r"^0+$")
# Where the workflow hands the two commits over. The workflow comes from the branch and this
# file comes from main, so they travel in the environment, which an older copy reads past.
PUSHED_FROM = "PUSH_BEFORE"
PUSHED_TO = "PUSH_AFTER"


class Refused(Exception):
    """Something was wrong, so nothing was published, or what was published is not right."""


def token() -> str:
    """The token this call authenticates with, from the environment and nowhere else."""
    for name in TOKEN_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise Refused("no token in the environment, so nothing was published")


def send(method: str, url: str, payload: dict | None, key: str) -> dict | list:
    """One REST call, returning the answer as it came, a dictionary or a list."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": AGENT,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read().decode("utf-8"))
    except urllib.error.HTTPError as refused:
        detail = refused.read().decode("utf-8", errors="replace").strip()
        raise Refused(f"{method} {url} answered {refused.code}, {detail[:400]}") from refused
    except (urllib.error.URLError, OSError, ValueError) as broken:
        raise Refused(f"{method} {url} did not complete, {broken}") from broken


def read_one(path: Path) -> str:
    """The text of one file, refusing rather than guessing when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as unreadable:
        raise Refused(f"{path} could not be read, {unreadable}")


def gate(name: str, text: str, terms: list[str]) -> None:
    """The text rules over one piece of text, raising with every line that broke one."""
    found = gates.text_problems(name, text, terms)
    if found:
        raise Refused("\n".join(found))


def issue_of_the_branch(head: str) -> str:
    """The issue number the head branch names, refusing a branch that names none.

    A branch that names no issue leaves nothing to read the body against, and a publish
    with nothing to check is the publish this check exists to stop.
    """
    named = BRANCH_ISSUE.match(head.strip())
    if named is None:
        raise Refused(
            f"the head branch {head} does not name an issue, so there is nothing to read "
            f"the body against and nothing was published"
        )
    return named.group(1)


def issue_of_the_body(body: str) -> str:
    """The issue number the body closes, read off its first line and nowhere else.

    A body says `Closes #N` on the line it opens with. Reading further would find the
    number of an issue the text merely mentions, which is not the issue it closes.
    """
    first = next((line.strip() for line in body.splitlines() if line.strip()), "")
    closing = BODY_ISSUE.match(first)
    if closing is None:
        raise Refused(
            f"the body opens with {first!r} and not with `Closes #N`, so which issue it "
            f"closes cannot be read and nothing was published"
        )
    return closing.group(1)


def nothing_published(
    reason: str, number: int | None = None, url: str = "", account: str = "", author: str = ""
) -> dict:
    """An answer that published nothing and carries the reason, for a run that is not wrong.

    Three pushes reach here on an ordinary run. The one before this run wrote its own body,
    which still carries the body of the run before it. The first push of a run that continues
    a branch, which carries a body the run has not written yet. And every push after the one
    that opened the pull request. None of them is a mistake, so none of them is an error.

    The account is carried when one was read. The push that finds a body written for another
    issue reads none, because it asks GitHub nothing at all, and the field is empty there.
    The author is the one the standing pull request carries, and it is empty on that push too.
    """
    return {
        "number": number,
        "url": url,
        "published": False,
        "reason": reason,
        "account": account,
        "author": author,
    }


def commit(name: str, value: str) -> str:
    """One commit the push event named, refusing anything that is not a commit.

    Both ends of the push go into a URL, so a value of any other shape is refused rather
    than sent, and a missing one is refused rather than read as no change at all.
    """
    value = value.strip()
    if not COMMIT.match(value):
        raise Refused(
            f"the commit {name} the push is {value!r}, which is not a commit, so which files "
            f"the push changed cannot be read and nothing was published"
        )
    return value


def wrote_the_body(
    owner: str, repo: str, base: str, before: str, after: str, key: str, transport
) -> bool:
    """Whether the push this runs for changed the body file.

    A push moves a branch from one commit to another, and GitHub names both. When the body
    file differs between the two, the push carries a body somebody wrote in it. When it
    does not, the body was there before the push and the push is not the one that wrote it.

    A push that creates a branch names forty zeros as the commit before it. That branch is
    compared against the base it was cut from, so a body written before the first push
    still counts as written by it.
    """
    after = commit("after", after)
    start = base if NO_COMMIT.match(before.strip()) else commit("before", before)
    span = f"{urllib.parse.quote(start, safe='')}...{after}"
    compared = transport("GET", f"{API}/repos/{owner}/{repo}/compare/{span}", None, key)
    files = compared.get("files") if isinstance(compared, dict) else None
    if not isinstance(files, list):
        raise Refused(f"the comparison {span} came back without a list of files, {compared}")
    return any(isinstance(one, dict) and one.get("filename") == BODY_PATH for one in files)


def as_sent(text: str) -> str:
    """A body with the line endings GitHub stores it with folded back, for comparing."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def already_there(owner: str, repo: str, head: str, key: str, transport) -> dict | None:
    """The pull request this branch already has, or nothing when it has none.

    Open and closed both count. A closed pull request is a decision somebody made, and
    a push that opened a second one would take that decision back without saying so.
    """
    query = urllib.parse.urlencode({"head": f"{owner}:{head}", "state": "all", "per_page": 1})
    listed = transport("GET", f"{API}/repos/{owner}/{repo}/pulls?{query}", None, key)
    if isinstance(listed, list) and listed and isinstance(listed[0], dict):
        return listed[0]
    return None


def account(key: str, transport) -> str:
    """The login this call authenticated as, asked of GitHub instead of read off the token.

    A squash merge takes the author of the pull request, so which account opens one is what
    the history of `main` ends up carrying. A token does not say whose it is, and a workflow
    token is nobody's, so the answer comes from GitHub or it says that it could not be had.

    This never refuses. The publishing call falls back to the workflow token where the secret
    holding the person's token is absent, and nothing further, and a read that only names an
    account must not be the thing that stops a publish.
    """
    try:
        who = transport("GET", f"{API}/user", None, key)
    except Refused as refused:
        return f"an account GitHub would not name, {refused}"
    login = who.get("login") if isinstance(who, dict) else None
    if isinstance(login, str) and login.strip():
        return login.strip()
    return "an account that came back without a login"


def author(pull: dict) -> str:
    """The login GitHub stored as the author of a pull request, or the empty string.

    This is what a squash merge takes, so it is read off the pull request itself and not
    off the token. An answer that carries no author reads as the empty string, which never
    matches an account a person named.
    """
    user = pull.get("user") if isinstance(pull, dict) else None
    login = user.get("login") if isinstance(user, dict) else None
    return login.strip() if isinstance(login, str) else ""


def expected_account() -> str:
    """The account a pull request is meant to carry, from the environment, or the empty string."""
    return os.environ.get(EXPECTED, "").strip()


def carried_by(opened: dict, expected: str) -> str:
    """Why the pull request carries the wrong account, or the empty string when it does not.

    Nothing is compared on a push that found no pull request, because there is no author to
    read, and nothing is compared when no account was named. Logins are compared without
    case, because GitHub treats them that way.
    """
    if opened.get("number") is None or not expected:
        return ""
    who = opened.get("author", "")
    if who.casefold() == expected.casefold():
        return ""
    carried = who or "no author GitHub would name"
    return (
        f"pull request {opened['number']} carries {carried} and not {expected}, the account "
        f"{EXPECTED} names. It was left open, because the work is fine and an edit cannot "
        f"change who opened it"
    )


def publish(
    owner: str,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
    terms: list[str],
    transport=send,
    *,
    before: str,
    after: str,
) -> dict:
    """Create the pull request, then read it back and check it word for word.

    The gate runs before the call, because text that breaks a rule must not reach
    GitHub at all. It runs again on what came back, because the only thing that
    proves nothing was appended is the stored body itself.

    A branch that already has a pull request gets nothing. That is what the workflow
    needs to run on every push to a branch and still write one body.

    The issue number runs first, because a body that names another issue is not this
    run's text at all, and no text rule can tell. Such a body publishes nothing and says
    why, the same answer a branch that already has a pull request gets. The gate then
    runs on what is left.

    A branch with no pull request then gets one only from the push that changed the body
    file. A push that left it alone is the first push of a run that continues a branch, and
    the body it finds is the one the run before it wrote. That publishes nothing and says why.

    The account is read once the token is in hand, so every answer that reached GitHub
    carries the login the call authenticated as, whether it published or not. The author is
    read off the pull request, the standing one or the one just stored, and asks GitHub
    nothing it was not already asked.
    """
    named = issue_of_the_branch(head)
    closing = issue_of_the_body(body)
    if named != closing:
        return nothing_published(
            f"the head branch names issue {named} and the body closes issue {closing}, so "
            f"the body was written for another run"
        )
    gate("the title", title, terms)
    gate("the body", body, terms)
    key = token()
    who = account(key, transport)
    standing = already_there(owner, repo, head, key, transport)
    if standing is not None:
        number = standing.get("number")
        return nothing_published(
            f"this branch already has pull request {number}",
            number=number,
            url=standing.get("html_url", ""),
            account=who,
            author=author(standing),
        )
    if not wrote_the_body(owner, repo, base, before, after, key, transport):
        return nothing_published(
            f"this push did not change {BODY_PATH}, so the body it holds was written by an "
            f"earlier push and is not published by this one",
            account=who,
        )
    made = transport(
        "POST",
        f"{API}/repos/{owner}/{repo}/pulls",
        {"title": title, "head": head, "base": base, "body": body},
        key,
    )
    number = made.get("number") if isinstance(made, dict) else None
    if not number:
        raise Refused(f"the answer carried no pull request number, {made}")
    stored = transport("GET", f"{API}/repos/{owner}/{repo}/pulls/{number}", None, key)
    if not isinstance(stored, dict):
        raise Refused(f"pull request {number} did not read back as a pull request, {stored}")
    kept = as_sent(stored.get("body") or "")
    gate(f"pull request {number} as it stands", kept, terms)
    if kept != as_sent(body):
        raise Refused(
            f"pull request {number} does not hold the body that was sent, and it was left "
            f"as it is, because an edit is what records the difference for good"
        )
    return {
        "number": number,
        "url": made.get("html_url", ""),
        "published": True,
        "reason": "",
        "account": who,
        "author": author(stored),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Publish a pull request body as it stands.")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--head", required=True, help="the branch the changes are on")
    parser.add_argument("--base", default="main")
    parser.add_argument("--title-file", required=True, metavar="FILE")
    parser.add_argument("--body-file", required=True, metavar="FILE")
    parser.add_argument(
        "--before",
        default=os.environ.get(PUSHED_FROM, ""),
        help=f"the commit the branch was at before the push, {PUSHED_FROM} when not given",
    )
    parser.add_argument(
        "--after",
        default=os.environ.get(PUSHED_TO, ""),
        help=f"the commit the push moved the branch to, {PUSHED_TO} when not given",
    )
    parser.add_argument("--terms-file", metavar="PATH", help="a private list of terms to refuse")
    args = parser.parse_args(argv)

    try:
        terms = gates.load_terms(args.terms_file)
        title = read_one(Path(args.title_file)).strip()
        body = read_one(Path(args.body_file))
        if not title:
            raise Refused("the title file is empty")
        opened = publish(
            args.owner,
            args.repo,
            args.head,
            args.base,
            title,
            body,
            terms,
            before=args.before,
            after=args.after,
        )
    except Refused as refused:
        sys.stderr.write(f"publish: refused\n{refused}\n")
        return 1
    except Exception as broken:
        sys.stderr.write(f"publish: the call itself broke, so nothing is assumed, {broken}\n")
        return 1
    who = opened.get("account", "")
    named = f", authenticated as {who}" if who else ""
    if not opened["published"]:
        print(f"publish: nothing was published, {opened['reason']}{named}")
    else:
        print(f"publish: pull request {opened['number']} {opened['url']}{named}")
    if opened.get("number") is None:
        return 0
    expected = expected_account()
    if not expected:
        print(
            f"publish: {EXPECTED} is empty, so the account pull request {opened['number']} "
            f"carries was not compared with anything"
        )
        return 0
    wrong = carried_by(opened, expected)
    if wrong:
        sys.stderr.write(f"publish: {wrong}\n")
        return 1
    print(
        f"publish: pull request {opened['number']} carries {expected}, the account "
        f"{EXPECTED} names"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
