---
name: swe-kit
description: Fast code navigation for fixing an issue in /workspace. Ranks the relevant files and functions from the issue text in one call, prints a function's source by name, and lists the existing tests that use a name.
---

# swe-kit

Three scripts. Call them with `run_skill_script`, skill_name `swe-kit`, and `args` as a list of strings.
Each one answers in under a second and replaces several grep and read_file calls.

1. `scripts/locate.py` — args: the key words of the issue (identifiers, error messages, feature names).
   Prints the most relevant source files, the most relevant functions with `file:start-end`, and exact matches.
   Example: `{"skill_name": "swe-kit", "file_path": "scripts/locate.py", "args": ["TTY_COMPATIBLE environment variable is_terminal"]}`

2. `scripts/show.py` — args: one or more function, method or class names (`name` or `Class.method`).
   Prints their full source with line numbers, ready for `edit_file`.
   Example: `{"skill_name": "swe-kit", "file_path": "scripts/show.py", "args": ["Console.is_terminal"]}`

3. `scripts/tests_for.py` — args: one or more names.
   Lists the existing tests that use them, with the matching lines and the pytest command to run them.
   Read those tests to copy the conventions (exception types, messages, edge cases).
   Example: `{"skill_name": "swe-kit", "file_path": "scripts/tests_for.py", "args": ["include_router"]}`
