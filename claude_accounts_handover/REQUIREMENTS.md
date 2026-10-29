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
