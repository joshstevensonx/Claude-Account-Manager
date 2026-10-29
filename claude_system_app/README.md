# Claude Hub (Claude Account Manager)

A local dashboard for running several Claude accounts on one Mac at the same time. Each account can run Claude Code in a terminal or right inside the dashboard, Claude.ai in its own browser profile, or a separate Claude Desktop copy.

## Start

Double-click **Claude Manager.command**. It opens http://127.0.0.1:7788 in your browser. Leave that Terminal window open while you use the dashboard; closing it stops the manager. Any Claude windows you opened keep running.

The first time, macOS may block it as being from an unidentified developer. If it does, right-click the file, choose **Open**, then confirm.

You need python3 (comes with the Xcode Command Line Tools). Nothing else to install.

## Pages

- **Overview**: counts, accounts with quick launch, everything active right now, recent activity, and which account has the most plan headroom.
- **Accounts**: one card per account. The **Desktop / Terminal / Browser** pills open (or focus) that client; **Launch** opens the account's default client; **Manage** edits name, colour, default folder and default client. Archiving an account moves its folders to `~/.claude-system/archive` and it can be **restored** from the same page.
- **Sessions**: every Claude Code conversation from the last 14 days, plus open Desktop and browser windows. Status: **Your turn**, **Needs approval?** (a best guess), **Working**, **Idle**. Click one to read it, resume it in Terminal, or continue it in Chat.
- **GUI Windows**: the Claude.ai and Claude Desktop windows that are open, with **Focus** and **Quit** per window. **Open multiple** opens several accounts at once.
- **Chat**: several Claude Code sessions side by side in the dashboard, each on any account. Every message runs `claude -p --resume` under that pane's account, so panes work in parallel and keep their history. Permissions per pane: **Plan** (read-only), **Ask** (tools needing approval are refused), **Edit** (may change files). Don't reply from a pane to a session that is also open in a Terminal; the two would branch apart.
- **Workspaces**: your project folders (with Git branch, read-only). **New session** on a workspace starts in that folder. Missing folders are flagged so you can relink them.
- **Tasks**: run a one-off prompt headless under any account; continue it in Terminal or Chat.
- **Usage**: real 5-hour and weekly plan limits (from each account's Claude Desktop `plan-usage-history.json`), burn rate, time to limit, and Claude Code token totals with API-equivalent dollars (for comparison, not a bill).
- **Activity**: a log of launches, failures, stops and configuration changes. It never stores prompts or chat content. Export or clear it any time; retention is set there or in Settings.
- **Settings**: appearance, notifications, terminal and browser, confirm-before-quit, privacy, and **Diagnostics** (checks Claude Code, the apps, folder isolation and missing folders).

**New session** (top right) asks for an account, where to open it (Terminal, Chat pane, Browser, Desktop) and a folder, and shows exactly what will open before you launch.

Keyboard: `⌘K` or `/` search, `n` new session, `o` `a` `s` `g` `c` `w` `t` `u` `l` switch pages, `1`–`9` launch an account's default client (`⇧` + number opens Claude Code), `Esc` closes.

## Signing in

Sign in inside each window the first time you open it; Claude Hub never asks for passwords or codes. An account shows **Signed in** once Claude Code is logged in (read from its own config). Desktop and browser sign-ins can't be read from outside those apps, so they stay **Configured** and Desktop windows are marked **identity unverified**.

## Notifications

You get a macOS notification when a session, chat reply or task finishes, when a session seems stuck on an approval, and when an account passes 80% or 95% of a limit. Recent alerts also appear under the bell icon.

## Where data lives

```
~/.claude-system/
  profiles.json        account list
  settings.json        preferences
  workspaces.json      project folders
  activity.jsonl       Activity log (no prompts or chat content)
  aliases.zsh          optional claude-<name> shell commands (source it from ~/.zshrc yourself)
  profiles/<id>/desktop   Claude Desktop data   (--user-data-dir)
  profiles/<id>/cli       Claude Code config/login  (CLAUDE_CONFIG_DIR)
  profiles/<id>/browser   browser profile for claude.ai
  runs.json            task and chat run history
  alerts.json          which limit alerts already fired
  archive/             archived accounts, never deleted
```

The **Default** account is your normal Claude install, which this tool leaves as it is.

## Notes

- Separate Claude Desktop copies use the `--user-data-dir` flag. Claude doesn't officially support it, so it isn't guaranteed and an app update could stop it working. Claude.ai browser profiles and Claude Code are the dependable ways to run accounts side by side.
- **Sign in to a new Desktop copy right after opening it.** The most recently opened copy receives the `claude://` sign-in link.
- The manager never starts a second Desktop or browser copy for an account that already has one open — it brings the existing window to the front instead. Quit only signals the processes started with that account's own folder.
- The server only listens on 127.0.0.1 and requires a per-session token, so other websites can't trigger launches.
