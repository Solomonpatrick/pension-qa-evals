# Notes

Surprises, failures and fixes, logged as they happen.

## Phase 0: project skeleton (2026-10-01)

- **Python wasn't really installed.** `python` on PATH was the Windows Store alias, which only prints
  "Python was not found". Installed 3.12.10 with `winget install -e --id Python.Python.3.12 --scope user`.
  The guide's commands are bash, so on Windows `source .venv/bin/activate` becomes `.venv\Scripts\Activate.ps1`.
- **First API key was rejected.** It returned a 400: "This API key is not scoped to a workspace, so this
  request must include the anthropic-workspace-id header". A second key, created inside a workspace, worked.
  Both keys started `sk-ant-usr-`, so the prefix doesn't tell you the scope. Checked each key with
  `client.models.list()`, which is free, before spending anything.
- **Corrupted global git email.** A pasted command had ended up inside `~/.gitconfig` as a second `user.email`
  value. Git uses the last value, so every commit would have had a broken author email. Removed the bad line.
- **pytest exits with code 5 when it collects no tests.** Fine locally, but a CI step treats any non-zero exit
  as a failure, so CI needs at least one real test before it can go green.
