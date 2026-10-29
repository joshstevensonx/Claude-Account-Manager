# Local API (manager.py)

Base URL: `http://127.0.0.1:7788`.

Every `/api/*` request needs the header `X-Token: <token>` and a Host header of `127.0.0.1` or `localhost`. Without them the server returns `403 {"error":"forbidden"}`. Errors return `{"error": "<message>"}` with status 400, 404 or 500. Request and response bodies are JSON.

## GET

| Path | Returns |
|---|---|
| `/` | `index.html` with `__TOKEN__` replaced by the token (no auth needed) |
| `/api/state` | `{profiles:[…], settings, aliases_file, dry_run, indexed, best}`. Each profile adds: `running{desktop,browser,cli}` (process counts), `account{email,org}`, `paths{desktop,cli,browser}`, `initialised{…}`, `sessions{working,needs_you,waiting}`, `plan{available,binding,stale,observed,metrics:[{code,label,value}] (fh/sd only)}`, `today{tokens,cost,…}` |
| `/api/sessions?profile=&limit=300` | `{sessions:[{id,key,profile,cwd,project,branch,title,last_prompt,last_text,last_tool,started,last_ts,model,tokens,cost,messages,status,open}], ready}` |
| `/api/sessions/<profile>/<key>` | `{messages:[{t,kind:user/assistant/tool/result,name?,error?,text}], cwd, title}`: the last 120 items, from up to the last 1.5 MB of the file |
| `/api/usage` | `{plan:{<pid>: plan_usage result}, tokens:{<pid>:{windows:{5h,today,7d,30d:{tokens,output,cost,by_family}}, daily:[14 × {day,tokens,cost}]}}, best:{profile,headroom}\|null}` |
| `/api/runs` | `{runs:[summary]}`, newest first |
| `/api/runs/<id>` | The run summary plus `events:[{t,kind,text,name?,error?}]` |
| `/api/notifications` | `{items:[{t,title,body,kind}]}`, newest first, up to 50 |
| `/api/projects` | `{projects:[cwd…]}`: up to 30 recent distinct session folders |

A `plan_usage` result looks like `{available, observed, org, stale, binding:{code,label,value}, metrics:[{code,label,value,window,rate_per_hour,eta,stale,history:[[t,v]…]}]}`. When there is no data it is `{available:false, reason:"no-file"|"unreadable"|"empty"}`.

A run summary has the fields `id, profile, cwd, project, prompt, mode, status (starting/running/done/error/stopped/interrupted), started, ended, session_id, model, cost, turns, result`.

## POST

| Path | Body | Effect |
|---|---|---|
| `/api/profiles` | `{name, note?, color?, workdir?}` | Creates a profile and its folders, and regenerates the aliases. Returns the profile |
| `/api/profiles/<id>/desktop` \| `cli` \| `browser` | `{workdir?}` | Launches. Returns `{ok}`, or `{ok, already:true}` if a desktop or browser copy is already running |
| `/api/profiles/<id>/resume` | `{session_id: <key>}` | Opens Terminal with `--resume <sid>` in the session's folder |
| `/api/profiles/<id>/stop` | `{kind: desktop\|browser}` | Sends SIGTERM to the matching processes. Returns `{stopped:n}` |
| `/api/profiles/<id>/update` | `{name?, note?, color?, workdir?, pinned?}` | Updates the profile |
| `/api/profiles/<id>/remove` | – | Archives the folders. Refused for `default` |
| `/api/profiles/<id>/reveal` | `{kind: cli\|desktop\|browser}` | Runs `open <folder>` (Finder) |
| `/api/profiles/<id>/size` | – | Size in bytes of each folder |
| `/api/launch-all` | `{kind, ids:[…]}` | Launches each, 0.4 s apart |
| `/api/runs` | `{profile, cwd, prompt, mode: plan\|default\|acceptEdits}` | Starts a headless run. Returns its summary |
| `/api/runs/<id>/stop` | – | Returns `{stopped:bool}` |
| `/api/runs/<id>/terminal` | – | Runs `--resume <session_id>` in Terminal. Returns 400 if there's no session yet |
| `/api/settings` | Any settings keys | Strings must not be empty. Booleans and threshold lists (1–100, at most 4) are validated |
