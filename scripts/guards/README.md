# ZDoc Guarded PR Workflow Checks

`zdoc_guard.py` automates repeated ZDoc PR checks while keeping high-risk
decisions manual.

It only checks state and runs explicitly configured test commands. It does not:

- merge pull requests
- create tags
- start frontend or backend services
- connect to Ollama
- run real generation
- create or update jobs
- write build, output, result bundle, DOCX, or XLSX artifacts
- run `git clean`
- run `git reset --hard`
- delete or move files

## Task Spec

The guard reads a JSON task spec with fields such as:

- `allowed_files`: paths or glob patterns that may be changed
- `forbidden_files`: paths or glob patterns that must not be changed
- `test_commands`: explicit commands to run during `verify`
- `count_paths`: paths whose file counts must stay unchanged
- `pr_title`: title used in `pr-summary`
- `tag_name`: tag used by `tag-check`

Use JSON so the guard stays standard-library only.

## Commands

```bash
python3 scripts/guards/zdoc_guard.py preflight --task tasks/zdoc_guard_example.json
python3 scripts/guards/zdoc_guard.py scope --task tasks/zdoc_guard_example.json
python3 scripts/guards/zdoc_guard.py verify --task tasks/zdoc_guard_example.json
python3 scripts/guards/zdoc_guard.py pr-summary --task tasks/zdoc_guard_example.json
python3 scripts/guards/zdoc_guard.py tag-check --task tasks/zdoc_guard_example.json
```

## Boundaries

This guard does not replace review judgment. A human must still decide whether
to create a PR, merge a PR, create a tag, run real Ollama validation, or allow
any job/build/output/export write path.

If a task needs a broader file scope, update the task spec intentionally and
review the expanded scope before running `verify`.
