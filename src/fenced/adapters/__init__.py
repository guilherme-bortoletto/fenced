"""The outside world. The only package that opens a file, reads a clock or reaches a network.

Each module here answers one port. `json_crm` and `json_journal` keep the record store and the
journal as files, `json_inbox` reads the messages, `clock` says what time it is, and the two
extractors read a message. `llm_extractor` is the only file that names a model provider.
"""
