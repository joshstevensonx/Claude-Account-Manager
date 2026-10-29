# Artifacts and references

## Delivered source files (contents inspected; copies in `source/`)

| File | Type | Location on owner's Mac | SHA-256 (first 12) | Transfer? |
|---|---|---|---|---|
| `manager.py` | Python 3 | `~/Desktop/DEV/claude_system/manager.py` | 3f485db9ac34 | Included |
| `monitor.py` | Python 3 | `~/Desktop/DEV/claude_system/monitor.py` | 7a545a4a73bf | Included |
| `index.html` | HTML/CSS/JS | `~/Desktop/DEV/claude_system/index.html` | d48e29a24720 | Included |
| `Claude Manager.command` | bash, executable | `~/Desktop/DEV/claude_system/Claude Manager.command` | 5cb3c055a897 | Included (run `chmod +x` again after copying) |
| `README.md` | Markdown user guide | `~/Desktop/DEV/claude_system/README.md` | 6e606461433a | Included |

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
