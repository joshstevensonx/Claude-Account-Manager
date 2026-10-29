# Paste this into the new AI session

You are taking over a software project from a previous AI session that ran under another account. You have no memory of that session. This message and the attached handover package (Markdown files plus a `source/` folder) are the only record. Don't claim to remember anything that isn't written here.

## The project

**Claude Account Manager**: a local dashboard for macOS that lets the owner, Josh (a freelance developer in Cape Town who works across several clients), run several Claude accounts at the same time in separate windows and manage them from one place. It lives at `~/Desktop/DEV/claude_system/` on his MacBook Pro.

The owner asked for, in order:

1. How to run multiple Claude accounts at once on a Mac with central management.
2. "build with a intuitive interface".
3. Add the functionality of **Maestro** (run and watch several Claude sessions from one dashboard) and **trackmyusage** (track usage per account).

He prefers concise answers.

## How it works

- **Stack:** `manager.py` (a Python standard-library HTTP server on 127.0.0.1:7788, with a per-start `X-Token`), `monitor.py` (session index, plan usage, notifier, headless runner), `index.html` (the whole UI, no libraries), and `Claude Manager.command` (the double-click launcher). No pip or npm. Must work on macOS system python3 (3.9+).
- **Isolation per account ("profile"):**
  - Claude Code: `CLAUDE_CONFIG_DIR=~/.claude-system/profiles/<id>/cli`
  - Desktop: `open -n -a Claude --args --user-data-dir=…/desktop`
  - claude.ai: Chrome with `--user-data-dir=…/browser`
  - The built-in `default` profile is the normal install and is never touched.
- **Tabs:**
  - **Accounts:** launch tiles, running dots, mini limit bars, live session pills.
  - **Sessions:** Claude Code transcripts from `<cli>/projects/**.jsonl`, with status working / needs_you / waiting / idle worked out from the last event and `lsof` working folders; a transcript drawer; resume in Terminal.
  - **Usage:** real 5-hour and weekly percentages from the desktop app's `plan-usage-history.json` (format `{"version":2,"samples":[{"t":ms,"org":…,"u":{"fh":…,"sd":…}}]}`), burn rate, time to limit, most-headroom account, token and API-equivalent $ totals, 14-day chart.
  - **Tasks:** headless `claude -p --output-format stream-json --verbose --permission-mode plan|default|acceptEdits` with streamed output.
- macOS notifications go through `osascript`.

## Rules to preserve

- Never delete user data: removing a profile archives it to `~/.claude-system/archive/`.
- Never start two desktop or browser copies on the same profile folder.
- Don't read Keychain credentials or call undocumented usage APIs.
- No `bypassPermissions` unless the owner asks.
- Costs are labelled as API-equivalent estimates.
- Keep it to the standard library, local-only and token-protected.
- Light and dark mode; works at phone width.

## State

- Built and sandbox-tested: the API, sample transcripts and usage files, and one real `claude -p` run.
- Installed on the Mac.
- **Not yet verified on macOS.** The biggest unknown is whether `--user-data-dir` desktop copies work and receive sign-ins correctly. trackmyusage notes that the last-launched copy grabs the `claude://` sign-in link, so the UI tells the user to sign in right after opening a copy.

## What to do first

1. Read `CURRENT_STATE.md`, then `IMPLEMENTATION_PLAN.md` (Phase 2: verify on the Mac).
2. Ask the owner whether he has run it and what happened. Don't rebuild anything that works.
3. Consult these files for detail:
   - `ARCHITECTURE.md`: algorithms, paths, process detection
   - `API_SPECIFICATION.md`
   - `UI_UX_SPECIFICATION.md`
   - `REQUIREMENTS.md`: IDs and acceptance criteria
   - `DECISIONS_AND_ASSUMPTIONS.md`: open assumptions A-01 to A-08
4. For any change, test in dry-run mode (`CLAUDE_SYSTEM_HOME=/tmp/cs_test CLAUDE_SYSTEM_DRY_RUN=1 python3 manager.py --no-open`). Then update `CURRENT_STATE.md` and the decision log.
