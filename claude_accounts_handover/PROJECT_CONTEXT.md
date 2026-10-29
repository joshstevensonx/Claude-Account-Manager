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
