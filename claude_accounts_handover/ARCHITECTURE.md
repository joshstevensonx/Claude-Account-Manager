# Architecture

## 1. Overview

```
Claude Manager.command (bash)  →  python3 manager.py  (ThreadingHTTPServer on 127.0.0.1:7788)
                                     ├─ serves index.html (inserts the session token in place of __TOKEN__)
                                     ├─ REST API /api/*          (see API_SPECIFICATION.md)
                                     ├─ launch(): open / osascript → Claude.app, Terminal/iTerm, Chrome
                                     └─ Watcher thread (every 3 s)  ── monitor.py
                                          ├─ SessionIndex.scan()   → incremental JSONL indexing
                                          ├─ classify(ps) + lsof   → which sessions have a live process
                                          ├─ plan_usage()          → plan-usage-history.json (every 30 s)
                                          ├─ Notifier              → osascript notifications
                                          └─ Runner                → `claude -p` subprocesses
Browser (index.html) polls /api/state, /api/sessions, /api/runs and /api/notifications every 3 s
```

## 2. Files

| File | Lines | Role |
|---|---|---|
| `manager.py` | 645 | HTTP server, profile registry, settings, process detection, launching, `Watcher`, routes |
| `monitor.py` | 726 | `SessionIndex`, `transcript()`, `plan_usage()`, `Notifier`, `Runner`, `process_cwds()`, pricing |
| `index.html` | 841 | Whole UI (inline CSS and JS, no libraries) |
| `Claude Manager.command` | 10 | `cd` to its own folder, check `python3`, `exec python3 manager.py` |
| `README.md` | 75 | User guide |

## 3. Data locations (`~/.claude-system/`, overridable with `CLAUDE_SYSTEM_HOME`)

| Path | Contents |
|---|---|
| `profiles.json` | `{"profiles":[{id,name,note,color,workdir,builtin,created,last_used,pinned?}]}`. Created on first run with the `default` profile |
| `settings.json` | Keys and defaults: `terminal:"Terminal"`, `desktop_app:"Claude"`, `browser_app:"Google Chrome"`, `claude_cli:"claude"`, `notify_done:true`, `notify_approval:true`, `notify_limits:true`, `alert_thresholds:[80,95]` |
| `aliases.zsh` | Generated shell aliases |
| `profiles/<id>/desktop` | Desktop app `--user-data-dir`; contains `plan-usage-history.json` once the app has run |
| `profiles/<id>/cli` | `CLAUDE_CONFIG_DIR`; contains `.claude.json` and `projects/<encoded-cwd>/<sessionId>.jsonl` |
| `profiles/<id>/browser` | Chrome `--user-data-dir` |
| `runs.json` | The last 40 headless runs, including events |
| `alerts.json` | Fired (disarmed) alert keys `[profile, code, threshold]` |
| `archive/` | Folders of removed profiles |
| `manager.log` | Every launch command, kill, notification and error (prefixed `DRY` in dry-run mode) |

**Default profile paths:**

- desktop: `~/Library/Application Support/Claude`
- CLI: `~/.claude`, with the account file at `~/.claude.json`
- browser: none

**Profile ID:** the name made lowercase, with runs of characters outside `[a-z0-9]` turned into `-`, cut to 32 characters, with `-2`, `-3` and so on added if the ID is taken.

**Environment variables:**

- `CLAUDE_SYSTEM_HOME`: data folder.
- `CLAUDE_SYSTEM_PORT`: port, default 7788.
- `CLAUDE_SYSTEM_DRY_RUN=1`: log commands instead of running them; used for testing on Linux.
- Command-line flag `--no-open`: don't open a browser on start.

If the port is already in use, the new process opens the dashboard of the instance that is already running and exits.

## 4. Process detection (`manager.classify`)

- **Command:** `ps -axeww -o pid=,command=`. On macOS, the `e` flag adds the process environment to the output for processes owned by the same user.
- **Desktop:** the command contains `<desktop_app>.app/Contents/MacOS/`, and its first segment doesn't contain `Helper`. If it has `--user-data-dir=X`, the process is matched to the profile whose desktop folder is X. Otherwise it belongs to `default`.
- **Browser:** the same check with `<browser_app>.app/Contents/MacOS/`. A `--user-data-dir` flag is required, so ordinary Chrome isn't counted.
- **CLI:** the program's base name is `claude`, or the command contains `@anthropic-ai/claude-code`. If the environment contains `CLAUDE_CONFIG_DIR=X`, the process is matched to that profile. Otherwise it belongs to `default`.
- **Working folders of CLI processes:** `lsof -a -d cwd -Fn -p <pids>` (`monitor.process_cwds`).

## 5. Session index (`monitor.SessionIndex`)

**Scanning.** It walks `<cli>/projects` for each profile. `*.jsonl` files directly in a project folder are sessions. Files deeper down (subagents) count towards usage only. Files whose last change is older than 35 days are skipped.

**Reading.** Each file is read incrementally from its last byte offset, and only complete lines are processed. If a file shrinks, it is re-read from the start. Usage is de-duplicated by the key `message.id + ":" + requestId`.

**Stored per file:**

- `sid`, `cwd`, `branch`
- `title`, taken from `ai-title`, then `custom-title`, then `summary`, then the first prompt
- `last_prompt`, `last_text`, `last_tool`
- `last_kind`: one of `prompt`, `tool_result`, `text`, `tool_use`
- `model`, `tokens`, `cost`
- hourly buckets: `{hour_epoch: {model: [input, output, cache_write_5m, cache_write_1h, cache_read]}}`

**Noise prompts** are skipped when picking titles and prompts: text that starts with `<`, `Caveat:` or `[Request interrupted`, plus anything marked `isMeta`.

**Session key.** `key = sha1(file path)[:12]`. The UI uses this key, because the same session ID can appear in different project folders. Resume uses the real `sid`.

**Attached.** A session counts as attached if a live CLI process for its profile has the session's working folder as its own, *and* it is the most recent session in that folder.

**Status rules** (`status_of`; age is measured from the file's last change):

| Last event | Result |
|---|---|
| `text` (or `stop_reason == end_turn`) | `needs_you` if attached, else `idle` |
| `tool_use` | `working` if age < 25 s; otherwise `waiting` if attached, else `idle` |
| `prompt` or `tool_result` | `working` if age < 180 s and (attached or age < 30 s), else `idle` |

**Pricing (API list price per million tokens, input/output):**

| Model id contains | Input | Output |
|---|---|---|
| `opus-4-1`, `opus-4-2025`, `3-opus` | 15 | 75 |
| other `opus` | 5 | 25 |
| `sonnet` | 3 | 15 |
| `3-5-haiku` | 0.8 | 4 |
| `3-haiku` | 0.25 | 1.25 |
| other `haiku` | 1 | 5 |
| anything else | 0 | 0 |

Cache writes cost input × 1.25 (5-minute cache) or × 2 (1-hour cache). Cache reads cost input × 0.1. These figures are assumptions (see A-04).

## 6. Plan usage (`monitor.plan_usage`)

1. Parse `plan-usage-history.json` (versions 1 and 2). Keep only samples from the latest `org`.
2. For each metric with a window:
   - The window is 5 h (`fh`) or 7 d (the others).
   - The rate window is `max(30 min, window/5)`.
   - A reading is stale after `max(1 h, window/4)`.
   - Take the samples inside the rate window and trim them to the stretch after the last drop of more than 0.5 (a reset).
   - If there are at least two samples spanning at least 10 minutes and the value is rising: `rate = Δvalue / Δhours` and `eta = latest_t + (100 − value)/rate × 3600`.
3. The **binding** metric is the higher of `fh` and `sd`. The whole reading is stale if the latest sample is more than 1 hour old.
4. **Best account:** the highest `100 − binding` among accounts with fresh readings. It is only shown when at least two accounts qualify.
5. In the UI, if the time to limit is longer than the window, it shows "On pace — won't hit the limit this window".

## 7. Runner (`monitor.Runner`)

**Command:** `[resolve_cli(), "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", mode]`. It runs with `cwd` set to the chosen folder, the environment set to `CLAUDE_CONFIG_DIR` (removed for the default profile), and stdin closed.

**Parsed events:** `system` (init), `assistant` (text, tool), `user` (tool results), `result`. Up to 600 events are kept per run.

**Stop:** sends SIGTERM and sets the status to `stopped`. Runs that were still `running` when the server restarted are marked `interrupted`.

**`resolve_cli()`:** `shutil.which(name)`, then these fallbacks in order: `~/.local/bin/claude`, `~/.claude/local/claude`, `/opt/homebrew/bin/claude`, `/usr/local/bin/claude`, `~/.npm-global/bin/claude`.

## 8. Terminal launch

AppleScript sent with `osascript -e`:

- **Terminal:** `tell application "Terminal" … do script "<cmd>"`
- **iTerm:** `create window with default profile`, then `write text`

`<cmd>` is built as follows:

```
cd <workdir> && export CLAUDE_CONFIG_DIR=<dir> && printf '\033]0;Claude · <name>\007' && clear && <claude path> [--resume <sid>]
```

The `export` part is omitted for the default profile. If the working folder doesn't exist, the command `cd`s to the home folder instead.

## 9. Security

- The server binds to `127.0.0.1` only.
- Every `/api/*` request (GET and POST) needs the header `X-Token: <random token generated at each start>` and a Host header of `127.0.0.1` or `localhost`.
- The page is served with the token embedded in it. Other websites can't read the page, so they can't get the token.
- Profile IDs are slugs. Shell arguments are quoted with `shlex.quote`, and AppleScript strings are escaped.
