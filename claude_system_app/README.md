# Claude Account Manager

A local dashboard for running several Claude accounts on one Mac at the same time. Each account can run in the desktop app, in Claude Code in a terminal, or on claude.ai in its own browser window.

## Start

Double-click **Claude Manager.command**. It opens http://127.0.0.1:7788 in your browser. Leave that Terminal window open while you use the dashboard; closing it stops the manager. Any Claude windows you opened keep running.

The first time, macOS may block it as being from an unidentified developer. If it does, right-click the file, choose **Open**, then confirm.

You need python3 (comes with the Xcode Command Line Tools). Nothing else to install.

## Use

1. **New account**: enter a name, colour and the folder the terminal should start in.
2. Click **Desktop**, **Terminal** or **Browser** on its card, then sign in with that account. You only sign in once per account and window type.
3. Green dots show which windows are running. ✕ quits that account's desktop app or browser window.

Keyboard: `1`–`9` opens the desktop app for an account, `⇧` + number opens Claude Code, `/` searches, `n` creates a new account.

## Sessions (live monitoring)

The **Sessions** tab lists every Claude Code conversation from the last 14 days for every account, newest and most urgent first:

- **Your turn**: Claude finished and is waiting for you.
- **Needs approval?**: Claude has been on one tool call for a while, which usually means a permission prompt.
- **Working**: Claude is thinking or running tools.
- **Idle**: no terminal is open on it.

Click a session to read its transcript live. You can **resume it in Terminal** under the right account, or copy the resume command. Status comes from the transcripts in `<account>/cli/projects/` and from which `claude` processes are running in which folder.

## Usage

- **Plan limits (real numbers).** The Claude desktop app records the account's 5-hour and weekly utilisation in `plan-usage-history.json` inside its data folder, about every 5 minutes while it's open. This is the same source [trackmyusage](https://github.com/frogbark/trackmyusage) reads. The dashboard shows each limit, how fast it's rising, and roughly how long until it's hit. It also marks the account with the **most headroom**, which the task runner picks by default.
- **Claude Code tokens.** Totals for the last 5 hours, today, 7 days and 30 days, from the transcripts. The dollar figure is what those tokens would cost at API list prices. It's useful for comparing accounts, but it isn't your bill.
- An account only has limit readings once its **desktop app** has been opened at least once.

## Tasks (background runs)

Pick an account, a folder and a prompt, and Claude Code runs headless (`claude -p`). The output streams into the dashboard, and **Continue in Terminal** picks up the same conversation interactively. Permission choices:

- **Plan**: read-only.
- **Ask**: anything that would need approval is refused, because there's no one to ask.
- **Edit**: Claude may change files in that folder.

## Notifications

You get a macOS notification when a session or task finishes, when a session seems stuck on an approval, and when an account passes 80% or 95% of a limit. You can switch these off or change the thresholds in Settings. Recent alerts also appear under the bell icon.

Keyboard: `a` / `s` / `u` / `t` switch tabs.

## Where data lives

```
~/.claude-system/
  profiles.json        account list
  settings.json        terminal / browser choice
  aliases.zsh          claude-<name> shell commands (source it from ~/.zshrc)
  profiles/<id>/desktop   Claude desktop app data   (--user-data-dir)
  profiles/<id>/cli       Claude Code config/login  (CLAUDE_CONFIG_DIR)
  profiles/<id>/browser   Chrome profile for claude.ai
  runs.json            background task history
  alerts.json          which limit alerts already fired
  archive/             removed accounts are moved here, never deleted
```

The **Default** card is your normal Claude install, which this tool leaves as it is.

## Notes

- Running separate desktop app copies uses the `--user-data-dir` flag. Claude doesn't officially support it, so an app update could stop it working. If that happens, the Terminal and Browser options still work.
- **Sign in to a new desktop copy right after opening it.** Every copy registers itself for the `claude://` sign-in link, and the most recently opened copy wins, so a sign-in can land in the wrong window if you open another account in between.
- The manager won't start a second desktop or browser copy for an account that already has one open. Claude Code can run in as many terminals as you like.
- The server only listens on 127.0.0.1 and requires a per-session token, so other websites can't trigger launches.
- Settings let you switch to iTerm, or to Brave, Edge or Arc instead of Chrome.
