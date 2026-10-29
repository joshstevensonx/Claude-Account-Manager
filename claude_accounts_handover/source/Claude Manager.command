#!/bin/bash
# Double-click to open the Claude Account Manager.
# Keeps running in this Terminal window; close the window (or Ctrl+C) to stop it.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "python3 not found" message "Install the Xcode Command Line Tools: run  xcode-select --install  in Terminal."'
  exit 1
fi
printf '\033]0;Claude Account Manager\007'
exec python3 manager.py
