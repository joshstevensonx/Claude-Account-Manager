# Local API (manager.py)

Base URL: `http://127.0.0.1:7788`.

Every `/api/*` request needs the header `X-Token: <token>` and a Host header of `127.0.0.1` or `localhost`. Without them the server returns `403 {"error":"forbidden"}`. Errors return `{"error": "<message>"}` with status 400, 404 or 500. Request and response bodies are JSON.

## GET

| Path | Returns |
|---|---|
| `/` | `index.html` with `__TOKEN__` replaced by the token (no auth needed) |
| `/api/state` | `{profiles:[…], settings, aliases_file, dry_run, indexed, best}`. Each profile adds: `running{desktop,browser,cli}` (process counts), `account{email,org}`, `paths{desktop,cli,browser}`, `initialised{…}`, `sessions{working,needs_you,waiting}`, `plan{available,binding,stale,observed,metrics:[{code,label,value}] (fh/sd only)}`, `today{tokens,cost,…}` |
| `/api/sessions?profile=&limit=300` | `{sessions:[{id,key,profile,cwd,project,branch,title,last_prompt,last_text,last_tool,started,last_ts,model,tokens,cost,messages,status,open}], ready}` |
| `/api/sessions/<profile>/<key>` | `{messages:[{t,kind:user/assistant/tool/result,name?,error?,text}], cwd, title}`: the last 120 items, from up to the last 1.5 MB of the file |
| `/api/usage` | `{plan:{<pid>: plan_usage result}, tokens:{<pid>:{windows:{5h,today,7d,30d:{tokens,output,cost,by_family}}, daily:[14 × {day,tokens,cost}]}}, best:{profile,headroom}\|null}` |
| `/api/runs` | `{runs:[summary]}`, newest first |
| `/api/runs/<id>` | The run summary plus `events:[{t,kind,text,name?,error?}]` |
| `/api/notifications` | `{items:[{t,title,body,kind}]}`, newest first, up to 50 |
| `/api/projects` | `{projects:[cwd…]}`: up to 30 recent distinct session folders |

A `plan_usage` result looks like `{available, observed, org, stale, binding:{code,label,value}, metrics:[{code,label,value,window,rate_per_hour,eta,stale,history:[[t,v]…]}]}`. When there is no data it is `{available:false, reason:"no-file"|"unreadable"|"empty"}`.

A run summary has the fields `id, profile, cwd, project, prompt, mode, status (starting/running/done/error/stopped/interrupted), started, ended, session_id, model, cost, turns, result`.

## POST

| Path | Body | Effect |
|---|---|---|
| `/api/profiles` | `{name, note?, color?, workdir?}` | Creates a profile and its folders, and regenerates the aliases. Returns the profile |
| `/api/profiles/<id>/desktop` \| `cli` \| `browser` | `{workdir?}` | Launches. Returns `{ok}`, or `{ok, already:true}` if a desktop or browser copy is already running |
| `/api/profiles/<id>/resume` | `{session_id: <key>}` | Opens Terminal with `--resume <sid>` in the session's folder |
| `/api/profiles/<id>/stop` | `{kind: desktop\|browser}` | Sends SIGTERM to the matching processes. Returns `{stopped:n}` |
| `/api/profiles/<id>/update` | `{name?, note?, color?, workdir?, pinned?}` | Updates the profile |
| `/api/profiles/<id>/remove` | – | Archives the folders. Refused for `default` |
| `/api/profiles/<id>/reveal` | `{kind: cli\|desktop\|browser}` | Runs `open <folder>` (Finder) |
| `/api/profiles/<id>/size` | – | Size in bytes of each folder |
| `/api/launch-all` | `{kind, ids:[…]}` | Launches each, 0.4 s apart |
| `/api/runs` | `{profile, cwd, prompt, mode: plan\|default\|acceptEdits}` | Starts a headless run. Returns its summary |
| `/api/runs/<id>/stop` | – | Returns `{stopped:bool}` |
| `/api/runs/<id>/terminal` | – | Runs `--resume <session_id>` in Terminal. Returns 400 if there's no session yet |
| `/api/settings` | Any settings keys | Strings must not be empty. Booleans and threshold lists (1–100, at most 4) are validated |
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
# Artifacts and references

## Delivered source files (contents inspected; copies in `source/`)

| File | Type | Location on owner's Mac | SHA-256 (first 12) | Transfer? |
|---|---|---|---|---|
| `manager.py` | Python 3 | `~/Desktop/DEV/claude_system/manager.py` | f47ba84bc777 | Included |
| `monitor.py` | Python 3 | `~/Desktop/DEV/claude_system/monitor.py` | af159c22d69a | Included |
| `index.html` | HTML/CSS/JS | `~/Desktop/DEV/claude_system/index.html` | c7020369cd2d | Included |
| `Claude Manager.command` | bash, executable | `~/Desktop/DEV/claude_system/Claude Manager.command` | 5cb3c055a897 | Included (run `chmod +x` again after copying) |
| `README.md` | Markdown user guide | `~/Desktop/DEV/claude_system/README.md` | 8bccdf80c2a8 | Included |

The `claude_system` folder held nothing before this project, so the five files above are its only contents.

## Runtime data (on the Mac only; not transferable, and must not be shared)

`~/.claude-system/`: profiles, logins, transcripts, `runs.json`, `alerts.json` and logs. **It contains account credentials and conversation history. Don't upload it to an AI session.** Its layout is described in ARCHITECTURE.md §3.

## Test fixtures (sandbox only; not preserved)

A sample generator wrote fake transcripts for the projects scooty_web, onegrid, macos-assistant and edward-site, plus `plan-usage-history.json` files for three test profiles. Playwright screenshot scripts were also used. These were throwaway and aren't included. Tests can be rebuilt from the formats in PROJECT_CONTEXT.md §3.

## External references

| Reference | Used for | Inspected? |
|---|---|---|
| https://docs.runmaestro.ai/multi-claude.md | Maestro's multi-account model (`CLAUDE_CONFIG_DIR` per agent) | Summary fetched |
| https://github.com/frogbark/trackmyusage | `plan-usage-history.json` format, metric codes, and the identity caveats of plain `--user-data-dir` copies. Key files: `Sources/TMUKit/UsageSample.swift`, `Sources/TMUClaude/ClaudeUsage.swift`, README "Why wrappers break" | Source cloned and read |
| https://github.com/jmdarre-v/claude-multiprofile | Mentioned as an alternative | Not inspected |
| https://blog.codeminer42.com/ai-tip-running-two-claude-code-accounts/ ; https://dev.to/truongandev/claude-code-multiple-accounts-on-one-machine-2026-2497 | `CLAUDE_CONFIG_DIR` approach | Search results only |
| Anthropic API pricing | Pricing table (A-04) | Not fetched; from prior knowledge |

## What to transfer manually

Only this package (including `source/`). Nothing else is needed.
# Completeness audit

| Check | Result |
|---|---|
| Whole session reviewed: question, round 1 build, round 2 build, handover request | Yes |
| Every user request captured (U1–U3) | Yes (PROJECT_CONTEXT §2, REQUIREMENTS) |
| User corrections or rejections | None occurred |
| Source files inspected and copied exactly | Yes. Hashes are in ARTIFACTS_AND_REFERENCES |
| Implementation status backed by evidence | Yes. Mac verification is explicitly marked as not done |
| Assumptions kept separate from facts | Yes (A-01 to A-08) |
| Secrets excluded | Yes. No tokens or credentials are in the package; the owner's email address is left out on purpose |
| Consistency across documents | IDs (R-, N-, D-, A-) cross-referenced |

## Gaps and limitations

- **No access to earlier conversations.** The owner's other projects (for example Scooty XP, 1-grid, a macOS assistant) appear only as background and aren't part of this project.
- **No observations from macOS.** The connection to the owner's computer dropped before this package was written, so the package couldn't be copied into his folder. Download it from the chat.
- The Maestro feature summary came from one docs page, so its UI wasn't studied in depth.
- The pricing table wasn't checked against a live source.
# Current state (as of 2026-10-29)

## Summary

Version 2 is complete and has been written to the owner's Mac at `~/Desktop/DEV/claude_system/`. It hasn't been run on macOS yet: no feedback from the owner after installation.

## Evidence levels

| Level | Meaning |
|---|---|
| Implemented | The code exists in `source/` |
| Sandbox-tested | Run in a Linux sandbox, either in dry-run mode (`CLAUDE_SYSTEM_DRY_RUN=1`) or with sample transcripts and usage files |
| Real-tested | Exercised with real Claude Code in the sandbox |
| Mac-verified | Observed on the owner's Mac. **Nothing has reached this level yet.** |

## Completed work

| Item | Evidence |
|---|---|
| Version 1: profiles, launching, process detection, quitting, aliases, settings, `.command` launcher | Sandbox-tested: API smoke tests passed (create, launch, update, remove, 403 without token). Process classification checked against simulated macOS `ps` lines, with helper processes correctly excluded. UI screenshots taken |
| Version 2: SessionIndex, status, transcript drawer, resume | Sandbox-tested with sample transcripts and one real transcript. Statuses and titles came out correctly. Resume produced the correct `--resume` command |
| Plan usage parsing and forecasts, most-headroom account | Sandbox-tested with sample `plan-usage-history.json` files in the confirmed format. Example: rising 5-hour usage at 18%/h gave a time to limit of about 2 h |
| Notifier (finished, approval, limits; dedupe; persistence) | Unit-tested: correct transitions, one alert per metric, no repeat after restart, re-armed after the value drops |
| Runner | **Real-tested:** `claude -p "Reply with just: pong"` ran in plan mode, status was done, model, cost and session ID were captured, and the events were system then assistant "pong" |
| UI: four tabs, drawer, modals, chart | Screenshots in light and dark; no JS errors; no horizontal scroll at 390 px |
| Files installed on the Mac | All five files written to the Mac folder; executable bit set; syntax-checked with Python 3.10 in the Mac's Linux VM |

## Not verified (needs the Mac)

- Desktop app isolation through `--user-data-dir`, and whether sign-ins go to the right copy (A-02, A-07).
- Terminal and iTerm AppleScript launch, the macOS Automation permission prompt, and Gatekeeper on the `.command` file.
- `ps -axeww` showing the environment on macOS (A-03) and `lsof` finding working folders.
- Notification delivery with `osascript`.
- Performance with large real `~/.claude/projects` folders.

## Known issues and limitations

1. Session status is heuristic. A long-running tool (for example a 2-minute build) shows as "Needs approval?" after 25 s if a terminal is attached.
2. The desktop app records plan limits only while it is running. Accounts used only in the CLI show token counts but no limits.
3. The time-to-limit forecast doesn't know exact reset times; the file has no reset timestamps.
4. The manager runs in a Terminal window; closing that window stops the dashboard. Claude windows keep running.
5. The pricing table may be out of date for new model families (A-04).
6. `Run again` fills in the form but doesn't submit it (by design).
7. A `__pycache__/` folder appears next to the code after the first run. This is harmless.

## Work in progress

None. Both build rounds were finished.

## Outstanding

See IMPLEMENTATION_PLAN.md. The top priority is verifying on the Mac.
# Decisions, assumptions, open questions, risks

## Decisions

| ID | Decision | Rationale | Alternatives considered | Valid? |
|---|---|---|---|---|
| D-01 | Local web dashboard (Python standard-library server and HTML) rather than a native app | No install, quick to change, works in any browser, Python is already on macOS | SwiftUI menu-bar app (owner knows SwiftUI); Electron | Yes |
| D-02 | Isolate accounts by folder: `CLAUDE_CONFIG_DIR` (CLI), `--user-data-dir` (desktop and browser) | Documented or commonly used mechanisms; nothing gets modified | Swapping login state in and out | Yes |
| D-03 | Data lives in `~/.claude-system`, separate from the code folder | Keeps credentials out of the Desktop/DEV folder, which might get synced | Inside `claude_system/` | Yes |
| D-04 | Removing an account archives it rather than deleting it | Sign-ins can be recovered; safe default | Hard delete | Yes |
| D-05 | Don't clone Claude.app per account (trackmyusage's approach) | Complex: re-signing, Apple Silicon only, clones don't auto-update. Worked around with a "sign in right after launching" message instead | Clone the bundle and use a shim | Revisit if desktop isolation fails on the Mac (see R-06) |
| D-06 | Plan limits come only from the desktop app's `plan-usage-history.json` | Real accounting with no credentials needed (same as trackmyusage) | Estimating from tokens | Yes |
| D-07 | Don't read OAuth tokens from the Keychain or call undocumented usage endpoints | Security; undocumented APIs | Community scripts | Yes |
| D-08 | Costs are labelled "API-equivalent" estimates | Subscription plans aren't billed per token | Showing them as cost | Yes |
| D-09 | Headless modes are limited to `plan`, `default` and `acceptEdits`; no `bypassPermissions` | Safety for unattended runs | Include bypass | Yes; can be added if the owner asks |
| D-10 | Session status is worked out from transcripts and processes (heuristic), with the label "Needs approval?" including a question mark | There is no official status API for interactive sessions | Hooks-based status | Yes; hooks are a possible upgrade (see the plan) |
| D-11 | Never start a second desktop or browser copy on the same data folder | Avoids corrupted profile data | Allow it | Yes |
| D-12 | Session key = sha1(path)[:12] | The same session ID was seen in two project folders (a `claude -p` run re-used its parent session's ID) | Using the session ID as the key | Yes |
| D-13 | One alert per metric per window, persisted across restarts | Early testing showed duplicate alerts (80 and 95 at once) and repeats after a restart | – | Yes |

## Assumptions (not confirmed)

| ID | Assumption | Confidence | How to confirm |
|---|---|---|---|
| A-01 | The owner accepts the design choices made for him: local web UI, data location, archiving | Medium (no objection given) | Ask |
| A-02 | `open -n -a Claude --args --user-data-dir=…` still gives separate, working copies of the current Claude desktop app | Medium. trackmyusage's notes say the flag separates the data but has identity side effects | Test on the Mac |
| A-03 | On macOS, `ps -axeww` shows `CLAUDE_CONFIG_DIR` for the user's own processes | Medium-high | Run `ps -axeww` with a profile terminal open |
| A-04 | API prices in the pricing table are current for the models in use | Medium. Newer model IDs fall back to their family's price | Check Anthropic's pricing page |
| A-05 | The macOS python3 is ≥ 3.9 (Xcode Command Line Tools) | High | `python3 --version` |
| A-06 | `claude` is on PATH in a Terminal login shell, or in one of the fallback paths | High | `which claude` |
| A-07 | The desktop app writes `plan-usage-history.json` into a custom `--user-data-dir` the same way as the default one | Medium-high (trackmyusage relies on this) | Look in the profile's desktop folder after running it for 10 minutes |
| A-08 | The status timing thresholds (25 s, 30 s, 180 s) suit real use | Low-medium | Watch real sessions |

## Open questions

1. Has the owner run version 2 on his Mac yet, and did the desktop isolation work?
2. Which accounts and plans does he have (Pro, Max, Team)? This affects which metrics appear.
3. Does he want a menu-bar or always-running mode (for example a LaunchAgent) instead of a Terminal window?
4. Does he want `bypassPermissions` for tasks, a task queue or schedules, or one task across several accounts in parallel?
5. Should hooks (Claude Code `Stop` / `Notification` hooks) give exact approval and finished states?

## Risks and blockers

| Risk | Impact | Mitigation |
|---|---|---|
| Claude desktop updates break `--user-data-dir`, or the sign-in link goes to the wrong copy | No desktop isolation | Terminal and Browser still work; on-screen guidance; bundle cloning (D-05) as a fallback |
| All desktop copies share one Keychain key (`Claude Safe Storage`) | Low (data stays separate) | Accept |
| Large transcript history slows the first scan | Slow first load | Files older than 35 days are skipped; incremental reads |
| Changes to the transcript JSONL format | Wrong status or totals | Parser ignores unknown types; revisit after Claude Code updates |
| Gatekeeper blocks `.command`; macOS asks to allow Terminal automation | First run is confusing | Covered in the README |
| Running two Claude instances in the same project folder (Maestro's warning) | Corrupted session files | Owner guidance only; not enforced |

## Rejected or avoided approaches

- Reading Keychain credentials or calling `api/oauth/usage` (D-07).
- Hard-deleting profiles (D-04).
- Allowing duplicate desktop or browser copies per profile (D-11).
- An earlier version 1 alias format (`shlex.quote` with the quotes then removed) was replaced by `CLAUDE_CONFIG_DIR="<path>"` inside single quotes.
# Implementation plan

## Phase 1: Restore context (P0)

| Task | Output | Done when |
|---|---|---|
| 1.1 Load this package and `source/` | The AI has read all five source files | It can explain `Watcher.tick()` and the status rules |
| 1.2 Compare `source/` with the owner's current copy in `~/Desktop/DEV/claude_system` (use the SHA-256 prefixes in ARTIFACTS_AND_REFERENCES.md) | Note of any differences | Hashes match, or the differences are recorded |

## Phase 2: Verify on the Mac (P0)

| Task | Steps | Done when |
|---|---|---|
| 2.1 First launch | Double-click `Claude Manager.command`; right-click → Open if Gatekeeper blocks it | The dashboard opens at 127.0.0.1:7788 |
| 2.2 Claude Code isolation | Create a profile, open Terminal, `/login` with account B | The card shows B's email; `~/.claude` is untouched |
| 2.3 Desktop isolation (A-02) | Open Desktop on profile B and sign in immediately; open the default copy | Two windows, two different accounts. **If this fails, consider D-05 (bundle cloning).** |
| 2.4 Detection (A-03) | With windows open, check the green dots and counts; also check `ps -axeww \| grep CLAUDE_CONFIG_DIR` | Counts are correct |
| 2.5 Plan usage (A-07) | Keep desktop B open for at least 10 minutes | `profiles/b/desktop/plan-usage-history.json` exists and the bars show |
| 2.6 Notifications | Finish a Claude Code turn in an attached terminal | A macOS notification appears |
| 2.7 Tasks | Run a Plan-mode task, then Continue in Terminal | Output streams, and the resumed session works |

Problems found in Phase 2 should be fixed in place. Record new decisions in DECISIONS_AND_ASSUMPTIONS.md.

## Phase 3: Immediate improvements (P1, confirm with the owner first)

1. **Exact status through Claude Code hooks.** Optionally install per-profile `settings.json` hooks (`Stop`, `Notification`) that write events to `~/.claude-system/events/`. The watcher would prefer these over the heuristics. This fixes known issue #1.
2. **Run in the background.** Add a LaunchAgent install option (starts at login, no Terminal window) and/or a small menu-bar status item.
3. **Reset times.** Infer reset times by finding drops in the 5-hour series (time of the last drop + 5 h) and show "resets in …".

## Phase 4: Optional features (P2, only if the owner asks)

- A task queue or schedule; running one prompt across several accounts in parallel.
- `bypassPermissions` mode, behind a clear warning (currently excluded by D-09).
- Per-account budgets or alerts based on API-equivalent $.
- Export usage to CSV.
- Fallback to bundle cloning for the desktop app (D-05) if 2.3 fails.

## Phase 5: Validation

After any change:

- Run `python3 -c "import ast;…"` to syntax-check `manager.py` and `monitor.py`.
- Start in dry-run mode: `CLAUDE_SYSTEM_HOME=/tmp/cs_test CLAUDE_SYSTEM_DRY_RUN=1 python3 manager.py --no-open`.
- Smoke-test the API with the token taken from `/`.
- Take screenshots of all four tabs in light and dark, and at 390 px wide. Check for JS errors and horizontal scroll.
- Then re-test on the Mac.

## Phase 6: Maintain the handover

Update CURRENT_STATE.md, the hashes, and the decision log. Increase the version in README.md.
# Project context

## 1. Purpose

The owner (Josh, a freelance developer whose work runs through his agency, Nexora Web Agency) works across several client accounts. He wants to run **multiple Claude accounts on one Mac at the same time, in separate windows, with a central place to manage them**. This lets him:

- keep each client's or team's Claude usage and quota separate;
- switch to another account when one hits its plan limit;
- see what every Claude Code session is doing without hunting through terminal windows.

Intended user: the owner alone, on his own MacBook Pro. It is not a multi-user or hosted service.

## 2. Conversation history (2026-10-29, one session)

| # | User message (paraphrased unless quoted) | Outcome |
|---|---|---|
| 1 | "how to run multiple claude accounts on mac simultaneously in different windows with a centralised management system" | Explained three isolation methods: `CLAUDE_CONFIG_DIR` for Claude Code, `open -n -a Claude --args --user-data-dir=…` for the desktop app, and separate browser profiles for claude.ai. Suggested a launcher. Named existing tools: claude-multiprofile, Maestro, trackmyusage. Offered to build a launcher in the owner's connected `claude_system` folder. |
| 2 | "build with a intuitive interface" | **Version 1 built.** Local Python server and dashboard with account cards, Desktop/Terminal/Browser launch, running-status detection, quit, add/edit/pin/remove, settings, shell aliases, and a double-click launcher. Installed in `~/Desktop/DEV/claude_system/` on the owner's Mac. |
| 3 | "add functionality of: Maestro runs and watches several Claude sessions from one dashboard; trackmyusage tracks usage per account" | **Version 2 built.** Added the Sessions tab (live monitoring and transcripts), Usage tab (plan limits, burn rate, time to limit, most-headroom account, token and cost estimates, 14-day chart), Tasks tab (headless runs), macOS notifications, and a notification bell. Installed over version 1. |
| 4 | Asked for this handover package | This package |

There were no corrections or rejections from the user during the session. The user gave short instructions and left design decisions to the assistant (see DECISIONS_AND_ASSUMPTIONS.md, A-01).

### How the requirements changed

- Round 1 asked for a how-to and got an explanation.
- Round 2 asked for a GUI launcher ("intuitive interface"). The scope stayed at launching, isolating, and showing status.
- Round 3 widened the scope to monitoring and usage. The source of truth for limits became the desktop app's own `plan-usage-history.json`, which the assistant found by reading the trackmyusage source code.

## 3. Research findings carried forward

- **Maestro** ([docs](https://docs.runmaestro.ai/multi-claude.md)) gives each agent one account through `CLAUDE_CONFIG_DIR`, with per-account quota panels in a usage dashboard. Its docs warn not to run two Claude instances on the same project at once.
- **trackmyusage** ([repo](https://github.com/frogbark/trackmyusage)) is a Swift app for Apple Silicon. Facts learned from its source, cloned and read on 2026-10-29:
  - The Claude desktop app writes `plan-usage-history.json` at the **root of its user-data directory**, about every 5 minutes while it runs.
  - The file format is version 2: `{"version":2,"samples":[{"t":<epoch ms>,"org":"<uuid>","u":{"fh":19,"sd":100,...}}]}`. Version 1 was `{t, fh, sd}` with no `org` field.
  - Metric codes: `fh` = five_hour, `sd` = seven_day, `so` = seven_day_opus, `sn` = seven_day_sonnet, `cw` = seven_day_cowork, `oa` = seven_day_oauth_apps, `om` = seven_day_omelette, `op` = omelette_promotional, `xu` = extra_usage (has no limit window). Values are utilisation percentages from 0 to 100.
  - Its "Why wrappers break" section says that launching the stock app binary with `--user-data-dir` separates the data but not the macOS app identity. As a result:
    - The app calls `setAsDefaultProtocolClient("claude")` on every launch, and the last copy launched wins, so a sign-in or MCP OAuth callback can land in the wrong copy.
    - LaunchServices may just re-activate the existing copy.
    - All copies share the `Claude Safe Storage` keychain key.
  - trackmyusage avoids this by cloning the app bundle per instance (unique bundle ID, re-signed, plus a launcher shim). This project chose **not** to do that (see D-05).
- **Claude Code transcript format.** This was checked by reading a real Claude Code 2.1.x JSONL transcript in the build sandbox. Each line is JSON with a `type` field:
  - `user` and `assistant` lines carry `sessionId`, `cwd`, `gitBranch`, a `timestamp` (ISO time), and a `message` with `model`, `id`, `content[]`, `stop_reason` and `usage{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, cache_creation{ephemeral_1h_input_tokens, ephemeral_5m_input_tokens}}`.
  - Assistant content blocks are split over several lines that share the same `message.id`, and the usage figures repeat on each line, so they must be de-duplicated.
  - Other line types: `ai-title` (`aiTitle`), `summary`, `custom-title`, `attachment`, `queue-operation`, `last-prompt`, `tools-used`, `system`.
- **`claude -p --output-format stream-json --verbose`** emits lines of type `system`/`init` (with `session_id` and `model`), then `assistant`, `user` (tool results), and `result` (with `total_cost_usd`, `num_turns`, `result`, `is_error`, `session_id`). It also emits unrelated types such as `active_goal` and `autocompact_state`, which are ignored. This was verified with a real run.

## 4. User preferences and conventions

| Preference | Explicit or inferred |
|---|---|
| Wants an *intuitive* graphical interface, not only shell commands | Explicit |
| Wants a central management system for multiple accounts in different windows | Explicit |
| Wants the features of Maestro (run and watch sessions) and trackmyusage (per-account usage) | Explicit |
| Platform is macOS (MacBook Pro), project folder `~/Desktop/DEV/claude_system` | Explicit (folder connected by user) |
| Concise responses | Explicit (standing preference) |
| Comfortable with code, terminal, Python, and JS; works with SwiftUI, React Native, Next.js and Laravel elsewhere | Inferred from profile |
| Prefers zero-install tooling (stdlib Python, no npm or pip) | Inferred; an assistant decision the user didn't object to |
| Data must stay local (127.0.0.1, no cloud) | Inferred; an assistant decision |
| Never delete user data; archive instead | Assistant decision (safety default) |

No explicit exclusions or prohibited technologies were stated by the user.
# Handover package: Claude Account Manager

| | |
|---|---|
| Package version | 1.0 |
| Generated | 2026-10-29 (Africa/Johannesburg) |
| Context covered | One working session on 2026-10-29: the first question, two build rounds, and this handover request |
| Project owner | Josh, a freelance web developer and data engineer based in Cape Town |
| Status | Version 2 is built and installed on the owner's Mac. It was tested in a Linux sandbox (dry-run mode plus one real headless run). **It has not yet been run on macOS.** |

## What this is

The Claude Account Manager is a local web dashboard for macOS. It lets one person run several Claude accounts at the same time and manage them from one place:

- **Launching:** opens each account in the Claude desktop app, in Claude Code (CLI) in a terminal, or on claude.ai in an isolated browser window.
- **Watching:** shows every Claude Code session across accounts, live (inspired by Maestro).
- **Usage:** tracks plan-limit usage per account and finds the account with the most headroom (inspired by trackmyusage).
- **Background tasks:** runs `claude -p` tasks headless, with the output streamed into the dashboard.

It is written in Python 3 using only the standard library (no third-party packages). The interface is a single HTML/JS page with no build step.

## Start here

1. **New AI session:** paste [`AI_HANDOVER_PROMPT.md`](AI_HANDOVER_PROMPT.md) as your first message, then attach this whole package, including `source/`.
2. Read [`CURRENT_STATE.md`](CURRENT_STATE.md) for what is verified and what isn't.
3. Read [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the next actions.

## Document index

| File | Contents |
|---|---|
| [AI_HANDOVER_PROMPT.md](AI_HANDOVER_PROMPT.md) | Prompt to paste into the new AI session; works on its own |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Purpose, conversation history, user preferences |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Requirements register with IDs, status and acceptance criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, data locations, process detection, file formats, algorithms |
| [API_SPECIFICATION.md](API_SPECIFICATION.md) | Every HTTP endpoint of the local server |
| [UI_UX_SPECIFICATION.md](UI_UX_SPECIFICATION.md) | Tabs, components, interactions, design tokens |
| [DECISIONS_AND_ASSUMPTIONS.md](DECISIONS_AND_ASSUMPTIONS.md) | Decisions, assumptions, open questions, risks, rejected approaches |
| [CURRENT_STATE.md](CURRENT_STATE.md) | What was built and tested, known issues |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Phased roadmap |
| [ARTIFACTS_AND_REFERENCES.md](ARTIFACTS_AND_REFERENCES.md) | File inventory, hashes, external links, what to transfer |
| [COMPLETENESS_AUDIT.md](COMPLETENESS_AUDIT.md) | What was reviewed, what could not be verified |
| `source/` | Exact copies of the five delivered files |

## Updating this package

When you change the code, update `CURRENT_STATE.md` and the file hashes in `ARTIFACTS_AND_REFERENCES.md`. Add new decisions to `DECISIONS_AND_ASSUMPTIONS.md` with the next free ID. Increase the package version in this file.
# Requirements register

**Status values:**

- **Implemented**: the code exists.
- **Verified-sandbox**: tested in a Linux sandbox, either in dry-run mode or with sample data.
- **Unverified-mac**: depends on macOS behaviour that hasn't been observed yet.
- **Proposed**: not built.

**Origin:** "U1/U2/U3" are user messages 1–3 (see PROJECT_CONTEXT.md §2). "A" means a decision the assistant made while implementing.

## Functional: accounts and launching (U1, U2)

| ID | Requirement | Origin | Status | Acceptance criteria |
|---|---|---|---|---|
| R-01 | Several Claude accounts can run at the same time on one Mac, each in its own windows | U1 | Implemented; Unverified-mac | Two accounts open together, and each stays signed in to its own account |
| R-02 | One central dashboard manages all accounts | U1, U2 | Implemented; Verified-sandbox | Opens at http://127.0.0.1:7788 |
| R-03 | Intuitive interface | U2 | Implemented; Verified-sandbox (screenshots, light and dark, 390px wide) | Cards, one click to launch, empty-state guide, keyboard shortcuts |
| R-04 | Account (profile) create, edit (name, note, colour, start folder), pin, and remove | A | Implemented; Verified-sandbox | API tests passed |
| R-05 | Isolated Claude Code per account through `CLAUDE_CONFIG_DIR=~/.claude-system/profiles/<id>/cli` | U1 | Implemented; Verified-sandbox (dry-run command) | Terminal opens with the environment variable exported and runs `claude` |
| R-06 | Isolated desktop app per account through `open -n -a Claude --args --user-data-dir=~/.claude-system/profiles/<id>/desktop` | U1 | Implemented; **Unverified-mac** | A separate signed-in window opens per account |
| R-07 | Isolated claude.ai per account through `open -n -a "Google Chrome" --args --user-data-dir=…/browser --no-first-run --no-default-browser-check https://claude.ai` | U1 | Implemented; Unverified-mac | |
| R-08 | Built-in "Default" profile is the normal install, which is never modified and can't be removed | A | Implemented | Default desktop = `open -a Claude`; default CLI = no environment variable; default browser = `open https://claude.ai` |
| R-09 | Detect running windows per account and quit desktop or browser copies (SIGTERM) | A | Implemented; detection unit-tested with simulated macOS `ps` output | Green dot, count, ✕ quits |
| R-10 | Never start a second desktop or browser copy on the same data folder | A | Implemented | API returns `{"already": true}` |
| R-11 | Removing an account moves its folders to `~/.claude-system/archive/<id>-<epoch>` and never deletes them | A | Implemented; Verified-sandbox | |
| R-12 | Generate `~/.claude-system/aliases.zsh` containing `alias claude-<id>='CLAUDE_CONFIG_DIR="<dir>" claude'` | A | Implemented; Verified-sandbox | |
| R-13 | Double-click launcher `Claude Manager.command` | A | Implemented; Unverified-mac | Opens the browser to the dashboard |
| R-14 | Settings: terminal app (Terminal or iTerm), desktop app name, browser app, `claude` command | A | Implemented | |
| R-15 | "Open all desktops" button and keyboard shortcuts (1–9 = desktop, ⇧+number = terminal, `/` search, `n` new, a/s/u/t tabs, Esc) | A | Implemented | |
| R-16 | Show the signed-in Claude Code email per account, read from `<cli>/.claude.json` → `oauthAccount.emailAddress` | A | Implemented; Verified-sandbox (default profile) | |

## Functional: session monitoring (U3, "Maestro")

| ID | Requirement | Status | Acceptance criteria |
|---|---|---|---|
| R-20 | List Claude Code sessions from the last 14 days across all accounts | Implemented; Verified-sandbox (sample data and a real transcript) | Shows title (`ai-title`, else the first prompt), project, branch, account, last activity, tokens, cost |
| R-21 | Live status: `working`, `needs_you` ("Your turn"), `waiting` ("Needs approval?"), or `idle` | Implemented; heuristics unverified against real interactive use | See the status rules in ARCHITECTURE.md §5 |
| R-22 | Transcript viewer drawer that refreshes live | Implemented; Verified-sandbox | |
| R-23 | Resume a session in Terminal under the correct account (`claude --resume <sessionId>` in the session's working folder) | Implemented; Verified-sandbox (dry-run command) | |
| R-24 | Filters by account and status, plus search | Implemented | |
| R-25 | Headless task runner: account, folder, prompt, and mode (`plan`, `default`, or `acceptEdits`), with streamed output, stop, "Continue in Terminal", run again, and history (last 40 runs) | Implemented; Verified-sandbox with a real `claude -p` run | |
| R-26 | macOS notifications through `osascript display notification`: session finished (working→needs_you), probable approval wait (working→waiting), task finished | Implemented; logic unit-tested; delivery unverified on Mac | |

## Functional: usage tracking (U3, "trackmyusage")

| ID | Requirement | Status | Acceptance criteria |
|---|---|---|---|
| R-30 | Read plan limits per account from `<desktop profile>/plan-usage-history.json` (default profile: `~/Library/Application Support/Claude/`) | Implemented; Verified-sandbox with sample files in the confirmed format | 5-hour and weekly bars on cards and in the Usage tab |
| R-31 | Burn rate (%/hour) and time to limit | Implemented | See the algorithm in ARCHITECTURE.md §6 |
| R-32 | Highlight the account with the most headroom; the task form picks it by default | Implemented | Needs ≥2 accounts with fresh readings |
| R-33 | Threshold alerts (default 80 and 95%): one alert per metric per window, re-armed when the value drops below threshold − 10, persisted in `alerts.json` | Implemented; unit-tested | |
| R-34 | Claude Code token totals per account for 5h, today, 7d and 30d; API-equivalent cost; model-family mix; 14-day stacked chart (tokens or $) | Implemented; Verified-sandbox | |
| R-35 | Recent notifications shown in a bell drop-down | Implemented | |

## Non-functional

| ID | Requirement | Status |
|---|---|---|
| N-01 | Python standard library only, compatible with macOS system python3 (3.9+); no pip or npm | Implemented; syntax checked on Python 3.10 and 3.13 |
| N-02 | Local only: binds to 127.0.0.1, requires a per-start random `X-Token` header, and checks the Host header | Implemented |
| N-03 | Light and dark mode; responsive down to 390px with no horizontal scroll | Verified-sandbox |
| N-04 | Never delete user data | Implemented |
| N-05 | Indexing must stay cheap: incremental JSONL reads by byte offset, files older than 35 days skipped, 3-second loop | Implemented; performance on large histories unmeasured |
| N-06 | No secrets stored; credentials stay in each account's own folder or Keychain | Implemented |

## Exclusions (not built, deliberately)

- Cloning the Claude.app bundle per account (trackmyusage-style identities). See D-05.
- Reading OAuth tokens from the Keychain or calling undocumented usage APIs. See D-07.
- A `bypassPermissions` mode for headless tasks. See D-09.
- Sending input to an already-running interactive terminal session (not feasible).
# UI/UX specification (index.html)

A single page. The **header** holds the logo "✳", the title "Claude Accounts", the subtitle "Run, watch and balance every Claude account from one place.", a notification bell (with an unseen-count badge), Settings, and a primary button "＋ New account".

**Tabs:** Accounts · Sessions (badge = active sessions; turns orange when something needs you) · Usage · Tasks (badge = running count). The last tab used is remembered in `localStorage` (`cam.tab`), as is when notifications were last seen (`cam.seen`). All storage access is wrapped in try/catch. The page polls every 3 s, but pauses when the tab is hidden or a menu is open.

## Accounts tab

**Toolbar:** a filter box (`/` focuses it), chips showing "N accounts" and "N active · N windows", and an "Open all desktops" button. A green banner names the account with the most headroom.

**Account card**, from top to bottom:

- A colour bar along the top.
- An avatar with the account's initials, the name, and tags: `DEFAULT`, `PINNED`, `MOST HEADROOM`.
- The note.
- "● email" when signed in to Claude Code; otherwise "Not signed in to Claude Code yet" or "Sign in on first launch".
- A shortcut-key badge (1–9).
- A ••• menu: Edit, Pin/Unpin, Run a task with this account, Show Claude Code folder, Show desktop data folder, Copy terminal command, Remove account… (in red).
- Mini 5-hour and weekly bars, when plan data exists. Bar colours: green, then amber at ≥70, then red at ≥90.
- Live session pills ("N your turn", "N needs approval?", "N working"). Clicking one opens Sessions filtered to that account.
- Three launch tiles: Desktop, Terminal, Browser. Each has an icon, a status dot and "start"/"running". Desktop and Browser tiles show an ✕ to quit while running.
- A footer showing "used Xm ago", "Nk today", and `claude-<id>`.

Also on this tab:

- A dashed "＋ New account" card.
- A "How it works" guide with three steps, hidden when there are more than 2 accounts.
- A "Terminal shortcuts" panel with the `source …aliases.zsh` line and a Copy button.

**Toasts:**

- On first opening a new desktop copy: "Opening X — sign in now, before opening another account".
- When a copy is already running: "X already has Desktop open — switch to it with ⌘Tab".

## Sessions tab

- Search box, account selector, and filter chips: Active (default), Your turn, Needs approval?, Working, All recent, each with a count.
- Rows are sorted by urgency (waiting, then needs_you, then working, then idle) and then by most recent. Each row shows:
  - a status pill (working = blue and pulsing; needs_you = green; waiting = amber and pulsing; idle = grey);
  - the title and a context line (last reply, the tool it's waiting on, the tool running, or the last prompt);
  - meta: account badge, project · branch · relative time, tokens · $.
- Clicking a row opens a **drawer** on the right (620 px wide; full width on phones; Esc closes it) with:
  - the account, project and status, and the title;
  - Resume in Terminal and Copy resume command buttons, plus the working folder;
  - the transcript feed (user messages as bubbles on the right; assistant replies as plain text; tool calls and results in grey monospace; errors in red). It auto-scrolls when already at the bottom.

## Usage tab

- The most-headroom banner.
- One card per account:
  - each windowed limit as a bar with its % and a forecast line: "≈ 1h 56m to the limit at +18%/h", "On pace — won't hit the limit this window", "Limit reached", "Flat — no measurable burn", or "Last reading … open this account's desktop app to refresh";
  - extra usage, and "Updated Xm ago";
  - a table of Claude Code tokens and API-equivalent $ for 5 hours, Today, 7 days and 30 days;
  - the 7-day model mix.
- With no plan data, the card says: "No plan-limit readings yet. Open this account's Desktop app…".
- A "Last 14 days · Claude Code" stacked SVG bar chart, coloured by account colour, with a Tokens / API-equivalent $ toggle, hover tooltips and a legend.
- A footnote explaining the data sources.

## Tasks tab

**Left column:** a "Run a task in the background" form:

- Account, defaulting to the most-headroom account.
- Project folder, with suggestions from recent sessions.
- Three permission buttons: Plan (read-only), Ask (blocked if unsafe), Edit (may change files).
- A prompt box; ⌘↩ submits.
- Below the form, the list of runs.

**Right column:** the selected run, showing account · folder · mode · model, the prompt as a heading, a status pill, Stop / Continue in Terminal / Run again buttons, the duration, number of turns and $, and the streamed feed.

## Modals

- **New/Edit account:** name, note, eight colour swatches, starting folder.
- **Settings:** terminal, desktop app name, browser, claude command, three notification checkboxes, thresholds.
- **Remove confirmation:** explains that the data is archived, not deleted.

## Design tokens

Defined on `:root`, with dark-mode values under `prefers-color-scheme`.

| Token | Light | Dark |
|---|---|---|
| `--bg` | #f6f5f1 | #1a1917 |
| `--panel` | #fff | #242320 |
| `--panel-2` | #f0eee8 | #2d2b28 |
| `--ink` | #1d1c1a | #ecebe7 |
| `--muted` | #6f6c66 | #9c9890 |
| `--line` | #e3e0d8 | #38362f |
| `--accent` | #c96442 | #d97757 |
| `--ok` | #3f8f5a | #5fb37a |
| `--warn` | #b7791f | #d9a441 |
| `--danger` | #b4413a | #e0675f |
| `--info` | #3b6fb6 | #7aa7e6 |

- **Account colours:** #d97757, #6a9bcc, #788c5d, #b07cc6, #c9a227, #4fa3a5, #c75b7a, #7f8c9b.
- **Font:** system (-apple-system / SF Pro). Radii are 9–16 px, with soft shadows.
- **Responsive:** account cards use `minmax(min(340px,100%),1fr)`. Session rows collapse to one column below 560 px. The tasks layout stacks below 860 px. Verified with no horizontal scroll at 390 px.
# Claude Account Manager

A local dashboard for running several Claude accounts on one Mac at the same time. Each account can run in the desktop app, in Claude Code in a terminal, or on claude.ai in its own browser window.

## Start

Double-click **Claude Manager.command**. It opens http://127.0.0.1:7788 in your browser. Leave that Terminal window open while you use the dashboard; closing it stops the manager. Any Claude windows you opened keep running.

The first time, macOS may block it as being from an unidentified developer. If it does, right-click the file, choose **Open**, then confirm.

You need python3 (comes with the Xcode Command Line Tools). Nothing else to install.

## Use

1. **New account**: enter a name, colour and the folder the terminal should start in.
2. Click **Desktop**, **Terminal** or **Browser** on its card, then sign in with that account. You only sign in once per account and window type.
3. Green dots show which windows are running. ✕ quits that account's desktop app or browser window.

Keyboard: `1`–`9` opens the desktop app for an account, `⇧` + number opens Claude Code, `/` searches, `n` creates a new account.

## Sessions (live monitoring)

The **Sessions** tab lists every Claude Code conversation from the last 14 days for every account, newest and most urgent first:

- **Your turn**: Claude finished and is waiting for you.
- **Needs approval?**: Claude has been on one tool call for a while, which usually means a permission prompt.
- **Working**: Claude is thinking or running tools.
- **Idle**: no terminal is open on it.

Click a session to read its transcript live. You can **resume it in Terminal** under the right account, or copy the resume command. Status comes from the transcripts in `<account>/cli/projects/` and from which `claude` processes are running in which folder.

## Usage

- **Plan limits (real numbers).** The Claude desktop app records the account's 5-hour and weekly utilisation in `plan-usage-history.json` inside its data folder, about every 5 minutes while it's open. This is the same source [trackmyusage](https://github.com/frogbark/trackmyusage) reads. The dashboard shows each limit, how fast it's rising, and roughly how long until it's hit. It also marks the account with the **most headroom**, which the task runner picks by default.
- **Claude Code tokens.** Totals for the last 5 hours, today, 7 days and 30 days, from the transcripts. The dollar figure is what those tokens would cost at API list prices. It's useful for comparing accounts, but it isn't your bill.
- An account only has limit readings once its **desktop app** has been opened at least once.

## Tasks (background runs)

Pick an account, a folder and a prompt, and Claude Code runs headless (`claude -p`). The output streams into the dashboard, and **Continue in Terminal** picks up the same conversation interactively. Permission choices:

- **Plan**: read-only.
- **Ask**: anything that would need approval is refused, because there's no one to ask.
- **Edit**: Claude may change files in that folder.

## Notifications

You get a macOS notification when a session or task finishes, when a session seems stuck on an approval, and when an account passes 80% or 95% of a limit. You can switch these off or change the thresholds in Settings. Recent alerts also appear under the bell icon.

Keyboard: `a` / `s` / `u` / `t` switch tabs.

## Where data lives

```
~/.claude-system/
  profiles.json        account list
  settings.json        terminal / browser choice
  aliases.zsh          claude-<name> shell commands (source it from ~/.zshrc)
  profiles/<id>/desktop   Claude desktop app data   (--user-data-dir)
  profiles/<id>/cli       Claude Code config/login  (CLAUDE_CONFIG_DIR)
  profiles/<id>/browser   Chrome profile for claude.ai
  runs.json            background task history
  alerts.json          which limit alerts already fired
  archive/             removed accounts are moved here, never deleted
```

The **Default** card is your normal Claude install, which this tool leaves as it is.

## Notes

- Running separate desktop app copies uses the `--user-data-dir` flag. Claude doesn't officially support it, so an app update could stop it working. If that happens, the Terminal and Browser options still work.
- **Sign in to a new desktop copy right after opening it.** Every copy registers itself for the `claude://` sign-in link, and the most recently opened copy wins, so a sign-in can land in the wrong window if you open another account in between.
- The manager won't start a second desktop or browser copy for an account that already has one open. Claude Code can run in as many terminals as you like.
- The server only listens on 127.0.0.1 and requires a per-session token, so other websites can't trigger launches.
- Settings let you switch to iTerm, or to Brave, Edge or Arc instead of Chrome.
