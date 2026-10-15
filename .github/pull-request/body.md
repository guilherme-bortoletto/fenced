Closes #52

## What

A lead now carries a segment, a language and the products the person named, on top of the name, the address and the awareness.

`src/fenced/domain/lead.py` gains two closed sets, written the way `Awareness` is. `Segment` has `food`, `retail`, `wholesale`, `manufacturing` and `health`. `Language` has `en`, `pt`, `es`, `fr`, `de` and `it`. Both forgive case and spacing and refuse anything else, with `UnknownSegment` and `UnknownLanguage`. The products are a tuple of names as the person wrote them, trimmed and kept once in the order named. An empty list is a lead like any other. A string, a null, a number or a blank name is refused with `InvalidProducts`. All three are `LeadError`. `Lead.from_fields` refuses a mapping that lacks any of the seven fields, and the three awareness helpers now share one parser.

`src/fenced/adapters/llm_extractor.py` asks the model for six fields. The schema adds `products` as an array of strings and `language` and `segment` as enums of the domain values plus the empty string. The prompt writes each language and each segment out by hand.

`src/fenced/adapters/fake_extractor.py` reads the three new fields by rules written at its top. A segment is the first row of a table of words. A language is the row of a table of short common words with the most hits. A product is a run of two or more capitalised words off the signature lines. A field the rules cannot find is left out, so the boundary refuses it.

The command line prints a third line for each lead, such as `retail, it, products 'Shelf Scanner'`.

`examples/messages.json` names three invented products across the messages. Two messages are new. One comes from a dental clinic in the `health` segment and one is written in Italian. Seven of the eight messages are leads and the one with no address is handed back as before.

Record 0024 says what each new field costs when the model gets it wrong. Record 0020 gains one line at its end that points at it, and its decision is left as it was. The index lists the record and the README tour visits it as step 22.

## Why

Matching needs a segment, a ticket and a language, and scoring needs the products. None of them was on a lead, so the command line stopped after the next step. Record 0020 said each one is a property in the schema, a type the boundary checks and a decision about what a wrong value costs. This pull request is those three things for each field.

## Tests

`python -m pytest` passes 744 tests, under Python 3.13 and under 3.11. `python scripts/gates.py` is clean apart from the term rules, which had no list to read on this machine.

New tests plant these cases.

- `tests/test_lead.py`. A lead carries the three fields. The two sets are pinned member by member. Case and spacing are forgiven. An empty value, an unknown segment, a language written as a word, a regional code and a list of two segments are refused. A value that is not text is refused. A missing segment, language or list of products is refused by name. An empty list of products is a lead. Products are trimmed and kept once in order. A string, a null, a mapping, a set, a null or a number in the list and a blank or invisible name are refused. The new fields cannot change after the lead is built.
- `tests/test_adapters.py`. The fake extractor reads each segment row, refuses `workshop` as a shop, reads four languages and leaves out one it cannot find, and reads two products off the body while skipping the signature. Every example message is read into all six fields except the one with no address. The schema asks for exactly six fields, allows no other, and lets the model answer with an empty string for a language or a segment. The prompt names every language and every segment. An answer of six fields crosses the boundary.
- `tests/test_cli.py`. A run prints the segment, the language and the products of each lead, and seven leads are planned.

`fenced run` over the examples was run by hand and printed what the tests assert.

## Decisions I made

- The two sets are my choice. Five segments that fit the invented messages, and six languages as two letter codes. Each is an enum, so a change is a red test.
- The `health` segment and Italian are the two the sellers of issue 53 can leave uncovered. Both are in the sets, so those messages cross the boundary today and matching has something to refuse.
- The schema allows the empty string for a language and a segment. With a strict enum the model would have to pick the nearest member for a message in Dutch, which is a guess. The empty string is then refused at the boundary like any other value outside the set.
- An empty list of products is a lead. Scoring already refuses an empty list as nothing to score, so that refusal belongs to the scoring step and not to the boundary.
- Products are deduplicated by exact text after trimming, the same way `scoring.py` does it. `Starter Kit` and `starter kit` stay two names, and the catalog decides in issue 53.
- The store keeps the same record. The three fields are printed and not written, because nothing reads them back yet. Record 0024 says so.
- The test that record 0020 names, `test_the_model_extractor_refuses_an_answer_that_is_not_three_fields`, keeps its name, so the record still points at a test that exists.
- The fake extractor knows no product names. It reads capitalised runs, so it carries nothing of a catalog, and the invented products are written in capitals in the messages.

## Run notes

> No dash used as punctuation and no semicolon, in Markdown or in a docstring. Short sentences. Describe what is there instead of selling it.

Stall check found nothing. The last merge was pull request 51 yesterday, and no `claude/` pull request was open. The brake counted zero and no issue carried `stuck`. No pull request carried `needs-work`. Issues 52, 53 and 54 were open with `night`, and 52 was the lowest with no branch, so `claude/issue-52` was cut from `main`.

The default interpreter here is Python 3.11 and the package needs 3.12, so I made a 3.13 virtual environment to run the suite. The first commit was blocked by the commit hook, because the interpreter it uses had no pytest. I installed pytest for that interpreter and committed again. The suite passes under both. No hook was skipped.

The first two pushes carried the code and the record. They left the body file as the run before me wrote it, so they published nothing.

I did not wire scoring or matching into the command line. That is issue 53. I did not keep the three fields in the store. I did not run the term rules, because no list was on this machine. I wrote no comment anywhere.

The gates took between 2.5 and 2.8 seconds a run, over three runs.
