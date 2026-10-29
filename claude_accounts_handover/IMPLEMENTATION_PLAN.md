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
