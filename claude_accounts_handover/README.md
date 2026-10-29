# Handover package: Claude Account Manager

| | |
|---|---|
| Package version | 1.1 |
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
