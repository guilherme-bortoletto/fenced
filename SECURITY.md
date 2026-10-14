# Security

## Reporting a problem

Open an issue that says a security problem exists, and do not describe it there. The owner will
open a private security advisory on this repository and ask you to describe it in that advisory.

This repository promises no other channel and no response time.

## Secrets

No key is written in this repository. The two keys it uses arrive through the environment. The
model extractor reads `FENCED_LLM_API_KEY`, and the publisher reads a token from the repository
secret `PR_TOKEN`. A `.env` file is ignored by git, and the sixth fence refuses one that is
tracked.

Record `docs/adr/0021-no-secret-enters-the-tree.md` says what the fence on secrets catches and
what it misses, and names the test behind each claim. In short:

- The fence refuses a file that matches a shape a test plants, which today is a model provider
  key in two forms and a fine grained GitHub token, and it refuses a tracked `.env`.
- It does not see a key a program builds from pieces at run time. A test plants one and reads
  back that the fence accepts it.
- The model extractor refuses to start without a key, sends the key in a header and not in the
  body of a request, and leaves it out of the error when a request is refused.
- The publisher makes no call when no token is in its environment.

A green fence means no tracked file matches a shape a test planted. It does not mean the tree
holds no secret.

## Data

Every message, name and address in `examples/` is invented. The addresses use the domains
reserved for examples.

A run of the command line writes its store and its journal under `.fenced/`, which git ignores.
The command line reaches the network only when it is run with `--extractor model`. That run sends
the text of each message to the model provider named in `src/fenced/adapters/llm_extractor.py`.
