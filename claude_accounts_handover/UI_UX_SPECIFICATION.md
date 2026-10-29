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
