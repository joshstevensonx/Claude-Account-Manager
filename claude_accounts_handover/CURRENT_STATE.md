# Current state (as of 2026-10-29)

## Summary

Version 3 (Workspace: multiple sessions in the GUI) is complete in the repo; version 2 is complete and has been written to the owner's Mac at `~/Desktop/DEV/claude_system/`. It hasn't been run on macOS yet: no feedback from the owner after installation.

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

| Version 3: Workspace tab — several Claude Code sessions side by side in the GUI, each on any account, with a message box per pane (`claude -p --resume`), stop, per-pane permission mode, enlarge, continue in Terminal; open from Sessions, Tasks or an account menu | **Real-tested** in the sandbox: two panes ran in parallel with separate session ids; a follow-up in one pane recalled its own earlier message; transcripts load through `/api/transcript`. UI checked in Chromium (light, dark, 390 px): no JS errors, no horizontal scroll |

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
7. Workspace panes run headless, so in **Ask** mode tools that need approval are refused rather than prompted; use **Terminal** for those. Replying in a pane to a session that's also open in a Terminal branches it (the UI warns).
8. A `__pycache__/` folder appears next to the code after the first run. This is harmless.

## Work in progress

None. Both build rounds were finished.

## Outstanding

See IMPLEMENTATION_PLAN.md. The top priority is verifying on the Mac.
