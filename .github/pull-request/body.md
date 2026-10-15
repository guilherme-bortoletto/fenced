Closes #54

## What

The command line now prints the reply for each lead a seller takes, as a draft for a person to send.

`src/fenced/domain/reply.py` gains `draft`. It takes the level of awareness, the products the lead named, the catalog and the seller the match picked. It builds only the fields the template for that level names, each one through its own builder, and renders the reply through `reply`. The product and the price are the first product the lead named. The quantity counts all of them. A lead with no product, a product the catalog does not carry, a seller that is not a `Seller` and a sixth level are all refused.

`src/fenced/app/cli.py` prints two more lines under each lead the match takes.

```
  ticket 950, taken by Ada Fenwick
  draft for Ada Fenwick to send, nothing was sent
    Thanks for writing. Before we talk about Stock Counter, Ada Fenwick will ask what you have already tried, and will write back within 48 hours.
```

A lead that scoring refuses or that nobody takes prints `no draft, a reply names the seller who takes the lead and this lead has none` instead. A `ReplyError` stops the run with exit code 1, the way a table scoring or matching will not read does.

Record 0026 decides that a draft is printed and kept nowhere. Not in the store, not in the journal and not in a file of its own. The index lists it.

The README no longer says the command line does not call the reply. The opening paragraph, tour step 19 and the example under Run it say the command line drafts and sends nothing. The tour gains record 0026 as step 25. The table of what the model does not decide gains two rows, what the reply says and whether it is sent, and the sentence under it says where the reply comes from.

## Why

The reply was domain code with its own tests that nothing on the command line called. A reader who ran `fenced run` saw a score and a seller and never saw the sentence the person would get back. Now the run ends where the domain ends, with text a person reads and decides to send.

## Tests

`python -m pytest` passes 788 tests under Python 3.13 after the rework. `python scripts/gates.py` is clean apart from the term rules, which had no list to read on this machine.

New tests plant these cases.

- `tests/test_reply.py`. A draft is the reply its template asks for, at every level. It names the first product the lead named and counts all of them. A product written twice counts once. A lead with no product, a single string, `None` and a mapping are refused. A product the catalog does not carry is refused, first or later in the list. A seller given as a name is refused. A sixth level is refused.
- `tests/test_cli.py`. Three drafts over the examples are read back word for word. Every lead with a seller prints a draft, every lead without one prints why, and a message handed back prints neither. Each printed draft is checked against `reply.draft` called over the same examples, the level, the products and the seller read off the printed lines. After a run with `--write` neither the store nor the journal carries any draft, and the folder holds those two files and nothing else. `python -m fenced` as a process prints a draft too.

All of it runs with the fake extractor and a fixture that refuses any socket. `fenced run` over the examples was run by hand and printed what the tests assert.

## Decisions I made

- A draft is kept nowhere. It is computed again from what is already kept, and a kept draft would go stale the day a price moves. Record 0026 says why.
- `draft` lives in `reply.py` and not in the command line, so the command line builds no field itself and the choice of fields is tested in the domain.
- The product and the price in a draft are the first product the lead named. The templates name one product, and the first one is the one the person wrote first.
- A lead that scoring refuses has no seller, so it gets the same line as a lead nobody takes. The refusal above it already says which way it failed.
- A refusal of the reply stops the run instead of printing under the lead. Scoring has already refused any lead whose products the reply would refuse, so a reply refusal left over means a table is broken.
- The draft is printed indented under the line that says it is a draft, so a person reading the run sees the warning before the text.
- After the review, `draft` takes the language of the lead as its second argument and reads it with `Language.parse`, the way the boundary does. It refuses the wrong language before it builds any field, so a lead in Portuguese is refused as `WrongLanguage` even when its products would be refused too.
- The line that replaces a refused draft keeps the `ticket ... taken by` line above it, so a person still sees who takes the lead and can write the reply in the right language.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

The `gh` command on this machine had a token GitHub refused, so every read of GitHub went through the REST tools of the session instead. Nothing was written to GitHub except the pushes.

The stall check found nothing. The last merge was pull request 56 today, and no `claude/` pull request was open. The brake counted zero and no issue carried `stuck`. No pull request carried `needs-work`. Issue 54 was the only open issue labelled `night`, and it had no branch, so `claude/issue-54` was cut from `main`.

The first commit was blocked by the hook, because the global git config of this machine carried an address that is not a GitHub noreply one. The command that set the noreply identity in the clone was the same command that committed, and the hook read the config before the command ran. I set the identity in a command of its own and the commit went through. Pytest was also missing for the interpreter and I installed it. No hook was skipped.

The first two pushes carried the code and the docs and left the body file as the run before me wrote it, so they published nothing.

I did not add any way to send a reply, and I did not keep a draft anywhere. I did not run the term rules, because no list was on this machine. I wrote no comment anywhere.

The gates took between 2.6 and 3.1 seconds a run, over three runs.

### Rework after the review

This section was written by the run that addressed the review. The body above was published before it, and nothing published is edited, so this text lives in the file on the branch and not in the pull request on GitHub.

The stall check found nothing. The last merge was pull request 56 today. Pull request 57 carried `needs-work`, so it did not count toward the stall or the brake. No issue carried `stuck`. Pull request 57 had one review by the owner, read through the reviews endpoint.

The review asked for one thing. A lead in a language the templates are not written in gets a draft in English. I put the rule in the domain. `WRITTEN_IN` sits beside the templates in `reply.py`, `draft` takes the language of the lead and raises `WrongLanguage` for any other, and the command line prints `no draft, WrongLanguage, the replies are written in en and this lead wrote in pt` where the draft would be. The Portuguese lead from the review is planted in `tests/test_cli.py`, and Bram Holt, who speaks Portuguese, still takes it. `tests/test_reply.py` refuses each of the five other languages, refuses the wrong language before any field is built, and reads the language the way the boundary does. Record 0026 gains a paragraph that points at 0024. The README says what a lead in another language prints.

`origin/main` was merged in and had nothing new. `gh` had a token GitHub refused, so reads and the label went through the REST tools of the session. Pytest was missing for the interpreter and I installed it. The global git config carried an address that is not a GitHub noreply one, so I set the noreply identity in the clone before any commit.

I did not translate the templates and I did not add a template in another language. I did not run the term rules, because no list was on this machine. I wrote no comment anywhere.

The gates took about 2.7 seconds a run.
