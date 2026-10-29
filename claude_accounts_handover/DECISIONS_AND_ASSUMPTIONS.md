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
| D-14 | "Multiple sessions in the GUI" = a Workspace tab of chat panes; each message is a headless `claude -p --resume <sid>` run | Owner asked to open multiple sessions in the GUI. Reuses the tested Runner, needs no PTY or extra libraries, and every pane is a normal Claude Code session that can still be continued in Terminal | Embedding real terminals (needs a PTY bridge and xterm.js, against the no-library rule); `--input-format stream-json` long-lived processes (more fragile) | Yes |
| D-15 | Runs drop inherited `CLAUDECODE` / `CLAUDE_CODE_SESSION_ID` (and similar) env vars | Found in testing: when the manager is started from inside Claude Code, every run reused that session's id, so panes would share one conversation | – | Yes |
| D-16 | The list of open panes is stored in the browser (`localStorage`), not on the server | It's a view preference; the conversations themselves are the transcripts, so losing the list loses nothing | `~/.claude-system/workspace.json` | Yes |
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
