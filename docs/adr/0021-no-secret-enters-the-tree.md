# 21. No secret enters the tree, and what the fence on it does not see

Status: accepted
Date: 2026-10-14

## Context

The repository is public, and a key that reaches a commit is published with it. Two keys are
involved. The model extractor reads one from `FENCED_LLM_API_KEY`, as record 0019 says. The
publisher reads a token from the repository secret `PR_TOKEN`, as record 0017 says. The README
promises that nothing shaped like a credential is in the tree, and the sixth fence is the test
behind that row.

A fence on secrets is easy to overstate. A reader who sees a list of patterns will assume it
covers every key, and a reader who sees it pass will assume the tree is clean. Neither is true of
any check that reads text. So this record says what the fence catches and what it misses only as
far as a test in this repository proves it, and it names each test. Anything a test does not
prove is not claimed here in either direction.

## Decision

The fence is `secrets_in_the_tree` in `tests/test_fences.py`. It reads every file git tracks or
is about to add, and it refuses a file that matches one of the shapes in `SECRET_PATTERNS`, and
any environment file under version control.

What a test proves it catches.

- `test_no_secret_lives_in_this_tree` runs the fence over this repository, on every push.
- `test_the_secret_fence_rejects_assembled_credentials` plants three shapes and reads back a
  refusal for each. A model provider key, the same with a longer prefix, and a fine grained
  GitHub token.
- `test_the_secret_fence_rejects_a_versioned_environment_file` plants a `.env` and reads back a
  refusal that names it.

The other shapes in the table, such as a cloud key id or a private key block, are written there
and no test plants them. They are not claimed.

What a test proves it misses, or lets through on purpose.

- `test_the_secret_fence_misses_a_credential_assembled_at_run_time` plants a key built from
  pieces joined by the code and reads back that the fence accepts it. The fence reads the shape of
  text and not the value a program builds. The planting tests above rely on that to exist at all.
- `test_the_secret_fence_still_admits_an_example_environment_file` plants a `.env.example` and
  reads back that it is accepted, because an example names a variable and holds no value.
- `test_the_secret_fence_still_admits_a_pinned_action_in_a_workflow` plants a workflow that pins
  an action by commit and reads back that it is accepted, because a commit id is a long run of hex
  and a workflow is made of them.

The code that reads a key keeps it out of what it writes. These tests prove that much.

- `test_the_model_extractor_is_never_built_without_a_key` refuses an absent or blank key before
  any request.
- `test_the_model_extractor_sends_the_key_the_prompt_and_the_schema` reads back that the key is
  in the header and not in the body of the request.
- `test_a_refused_request_does_not_carry_the_key_into_the_error` plants a refusal whose body is
  the key and reads back an error that names the status and nothing else.
- `test_nothing_is_sent_without_a_token` reads back that the publisher makes no call when no
  token is in its environment.

The second layer is what runs outside the tree, because a fence inside it can only read what is
written there.

The first part is a private list of terms. It is a file on the machine that writes the code, and
`FENCED_TERMS_FILE` points at it. The `pre-commit` hook in that clone runs `scripts/gates.py`,
which refuses a term on the list in the files and the message of a commit. The list never
enters the tree, so this record names no term and says nothing about how many there are.
`test_a_term_arrives_from_a_list_that_is_not_in_this_repository` proves the route from a list
outside the tree to a refusal, and `test_a_private_term_in_a_body_is_never_sent` proves the
publisher refuses a term before any call. Where no list is, the gate says so, as record 0009
decides, and `test_a_run_without_a_list_says_the_term_rules_did_not_run` reads that line back.

The second part is the repository secret the publisher reads. It is a setting on the repository
and not a file in it. The workflow hands it to `scripts/publish.py` through the environment of the
step that publishes, and nothing in the tree holds its value. Record 0017 says what it is scoped to and what
happens when it is absent.

## Consequences

A green run of the sixth fence means no file in the tree matches a shape a test planted. It does
not mean the tree holds no secret. A key written in a shape the table does not carry, or built from
pieces, passes it, and one of those is planted so the limit is written where somebody meets it.

A key that never enters a file cannot be committed. That is why both keys arrive through the
environment, why `.env` is ignored and refused when tracked, and why the second layer lives where
the tree cannot see it.

The second layer is only as present as the machine it runs on. A clone with no list runs no term
rule, and it says so. Proving a change to how a term is matched belongs on the machine that holds a
list, as `AGENTS.md` says.

Adding a shape to the table is one line and one planted string. The string has to be assembled at
run time in the test, for the reason the planting test already gives in its comment.
