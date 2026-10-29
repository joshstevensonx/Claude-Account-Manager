"""
Session monitoring, usage tracking and headless task runs for Claude Account Manager.

  SessionIndex  – incrementally indexes Claude Code transcripts (<config>/projects/**.jsonl)
                  per account: titles, live status, token usage per hour and model.
  plan_usage()  – reads the Claude desktop app's own plan accounting
                  (<desktop profile>/plan-usage-history.json: 5-hour / weekly utilisation %),
                  with burn rate and time-to-limit forecasts.
  Runner        – runs `claude -p` tasks headless under a chosen account and streams output.
  Notifier      – macOS notifications for finished sessions, approvals and usage thresholds.

Standard library only.
"""
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- pricing
# API list prices in USD per million tokens, used only for an "API-equivalent" estimate.
# Subscription plans aren't billed per token; this is a way to compare accounts.
PRICES = [
    # (substring in model id, input, output)
    ("opus-4-1", 15.0, 75.0), ("opus-4-2025", 15.0, 75.0), ("3-opus", 15.0, 75.0),
    ("opus", 5.0, 25.0),
    ("sonnet", 3.0, 15.0),
    ("3-5-haiku", 0.8, 4.0), ("3-haiku", 0.25, 1.25),
    ("haiku", 1.0, 5.0),
]


def price_for(model):
    m = (model or "").lower()
    for key, i, o in PRICES:
        if key in m:
            return i, o
    return 0.0, 0.0


def cost_of(model, u):
    """u = [input, output, cache_write_5m, cache_write_1h, cache_read]"""
    i, o = price_for(model)
    return (u[0] * i + u[1] * o + u[2] * i * 1.25 + u[3] * i * 2.0 + u[4] * i * 0.1) / 1e6


def family(model):
    m = (model or "").lower()
    for f in ("opus", "sonnet", "haiku"):
        if f in m:
            return f
    return "other"


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def short(s, n=180):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def text_of(content):
    """Plain text from a message content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(b.get("text", ""))
    return "\n".join(out)


def is_noise_prompt(t):
    t = t.strip()
    return (not t) or t.startswith("<") or t.startswith("Caveat:") or t.startswith("[Request interrupted")


# --------------------------------------------------------------------------- sessions
class FileState:
    __slots__ = ("offset", "mtime", "size", "seen", "sid", "cwd", "branch", "title", "first_prompt",
                 "last_prompt", "started", "last_ts", "last_kind", "last_tool", "last_text",
                 "model", "tokens", "cost", "buckets", "is_sub", "messages")

    def __init__(self, is_sub):
        self.offset = 0
        self.mtime = 0
        self.size = 0
        self.seen = set()
        self.sid = None
        self.cwd = None
        self.branch = None
        self.title = None
        self.first_prompt = None
        self.last_prompt = None
        self.started = None
        self.last_ts = None
        self.last_kind = None     # prompt | tool_result | text | tool_use
        self.last_tool = None
        self.last_text = None
        self.model = None
        self.tokens = 0
        self.cost = 0.0
        self.buckets = {}         # hour_epoch -> {model: [in, out, cw5, cw1h, cr]}
        self.is_sub = is_sub
        self.messages = 0


class SessionIndex:
    USAGE_DAYS = 35

    def __init__(self, profiles_fn, paths_fn):
        self.profiles_fn = profiles_fn
        self.paths_fn = paths_fn
        self.files = {}           # path -> FileState
        self.owner = {}           # path -> profile id
        self.lock = threading.Lock()
        self.ready = False

    def projects_dir(self, p):
        return Path(self.paths_fn(p)["cli"]) / "projects"

    def scan(self):
        cutoff = time.time() - self.USAGE_DAYS * 86400
        alive = set()
        for p in self.profiles_fn():
            root = self.projects_dir(p)
            if not root.is_dir():
                continue
            for dirpath, _dirs, names in os.walk(root):
                is_sub = Path(dirpath) != root and Path(dirpath).parent != root
                for n in names:
                    if not n.endswith(".jsonl"):
                        continue
                    fp = os.path.join(dirpath, n)
                    try:
                        st = os.stat(fp)
                    except OSError:
                        continue
                    if st.st_mtime < cutoff:
                        continue
                    alive.add(fp)
                    fs = self.files.get(fp)
                    if fs is None or self.owner.get(fp) != p["id"]:
                        fs = FileState(is_sub)
                        with self.lock:
                            self.files[fp] = fs
                            self.owner[fp] = p["id"]
                    if st.st_size < fs.offset:          # rewritten/truncated: start over
                        fs = FileState(is_sub)
                        with self.lock:
                            self.files[fp] = fs
                    if st.st_size != fs.size or st.st_mtime != fs.mtime:
                        self._read(fp, fs)
                        fs.size, fs.mtime = st.st_size, st.st_mtime
        with self.lock:
            for fp in list(self.files):
                if fp not in alive:
                    del self.files[fp]
                    self.owner.pop(fp, None)
        self.ready = True

    def _read(self, fp, fs):
        try:
            with open(fp, "rb") as f:
                f.seek(fs.offset)
                data = f.read()
        except OSError:
            return
        end = data.rfind(b"\n")
        if end < 0:
            return
        chunk, fs.offset = data[: end + 1], fs.offset + end + 1
        with self.lock:
            for raw in chunk.splitlines():
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    self._ingest(fs, d)

    def _ingest(self, fs, d):
        t = d.get("type")
        if t == "ai-title" and d.get("aiTitle"):
            fs.title = d["aiTitle"]
            return
        if t == "custom-title" and d.get("customTitle"):
            fs.title = d["customTitle"]
            return
        if t == "summary" and d.get("summary") and not fs.title:
            fs.title = d["summary"]
            return
        if t not in ("user", "assistant"):
            return
        ts = parse_ts(d.get("timestamp"))
        fs.sid = fs.sid or d.get("sessionId")
        fs.cwd = d.get("cwd") or fs.cwd
        fs.branch = d.get("gitBranch") or fs.branch
        if ts:
            fs.started = fs.started or ts
            fs.last_ts = max(fs.last_ts or 0, ts)
        msg = d.get("message") or {}
        if t == "user":
            content = msg.get("content")
            if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                fs.last_kind = "tool_result"
            elif not d.get("isMeta"):
                txt = text_of(content)
                if not is_noise_prompt(txt):
                    fs.first_prompt = fs.first_prompt or short(txt, 140)
                    fs.last_prompt = short(txt, 200)
                    fs.last_kind = "prompt"
                    fs.messages += 1
            return
        # assistant
        model = msg.get("model")
        if model and model != "<synthetic>":
            fs.model = model
        for b in msg.get("content") or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                fs.last_kind, fs.last_tool = "tool_use", b.get("name")
            elif b.get("type") == "text" and b.get("text", "").strip():
                fs.last_kind, fs.last_text = "text", short(b["text"], 220)
        if msg.get("stop_reason") == "end_turn":
            fs.last_kind = "text"
        key = (msg.get("id") or "") + ":" + (d.get("requestId") or "")
        u = msg.get("usage")
        if u and key not in fs.seen and ts:
            fs.seen.add(key)
            fs.messages += 1
            cc = u.get("cache_creation") or {}
            cw_total = u.get("cache_creation_input_tokens") or 0
            cw1h = cc.get("ephemeral_1h_input_tokens") or 0
            vec = [u.get("input_tokens") or 0, u.get("output_tokens") or 0,
                   max(cw_total - cw1h, 0), cw1h, u.get("cache_read_input_tokens") or 0]
            hour = int(ts // 3600) * 3600
            slot = fs.buckets.setdefault(hour, {}).setdefault(model or "unknown", [0, 0, 0, 0, 0])
            for i in range(5):
                slot[i] += vec[i]
            fs.tokens += vec[0] + vec[1] + vec[2] + vec[3]
            fs.cost += cost_of(model, vec)

    # ---- queries
    def sessions(self, live_cwds, now=None, days=14):
        """live_cwds: {profile_id: set(cwd)} of running interactive claude processes."""
        now = now or time.time()
        out = []
        with self.lock:
            items = [(fp, fs, self.owner[fp]) for fp, fs in self.files.items()]
        latest_per_cwd = {}
        for fp, fs, pid in items:
            if fs.is_sub or not fs.last_ts:
                continue
            k = (pid, fs.cwd)
            if fs.last_ts > latest_per_cwd.get(k, 0):
                latest_per_cwd[k] = fs.last_ts
        for fp, fs, pid in items:
            if fs.is_sub or not fs.last_ts or fs.last_ts < now - days * 86400:
                continue
            if not fs.messages:
                continue
            age = now - (fs.mtime or fs.last_ts)
            attached = fs.cwd in live_cwds.get(pid, set()) and latest_per_cwd.get((pid, fs.cwd)) == fs.last_ts
            out.append({
                "id": fs.sid or Path(fp).stem, "key": file_key(fp), "profile": pid, "cwd": fs.cwd,
                "project": Path(fs.cwd).name if fs.cwd else "?", "branch": fs.branch,
                "title": fs.title or fs.first_prompt or "(untitled)",
                "last_prompt": fs.last_prompt, "last_text": fs.last_text, "last_tool": fs.last_tool,
                "started": fs.started, "last_ts": fs.last_ts, "model": fs.model,
                "tokens": fs.tokens, "cost": round(fs.cost, 4), "messages": fs.messages,
                "status": status_of(fs.last_kind, age, attached),
                "open": bool(attached or age < 20),
            })
        out.sort(key=lambda s: s["last_ts"], reverse=True)
        return out

    def find(self, profile_id, sid):
        with self.lock:
            for fp, fs in self.files.items():
                if self.owner.get(fp) == profile_id and not fs.is_sub and file_key(fp) == sid:
                    return fp, fs
        return None, None

    def usage(self, now=None):
        """Token usage per profile for several windows, plus a 14-day daily series."""
        now = now or time.time()
        midnight = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        windows = {"5h": now - 5 * 3600, "today": midnight, "7d": now - 7 * 86400, "30d": now - 30 * 86400}
        days = [midnight - i * 86400 for i in range(13, -1, -1)]
        res = {}
        with self.lock:
            items = [(self.owner[fp], fs) for fp, fs in self.files.items()]
        for pid, fs in items:
            r = res.setdefault(pid, {
                "windows": {k: {"tokens": 0, "output": 0, "cost": 0.0, "by_family": {}} for k in windows},
                "daily": [{"day": d, "tokens": 0, "cost": 0.0} for d in days],
            })
            for hour, models in fs.buckets.items():
                for model, v in models.items():
                    tok = v[0] + v[1] + v[2] + v[3]
                    c = cost_of(model, v)
                    for k, since in windows.items():
                        if hour + 3600 > since:
                            w = r["windows"][k]
                            w["tokens"] += tok
                            w["output"] += v[1]
                            w["cost"] += c
                            fam = family(model)
                            w["by_family"][fam] = w["by_family"].get(fam, 0) + tok
                    if hour >= days[0]:
                        i = min(int((hour - days[0]) // 86400), 13)
                        r["daily"][i]["tokens"] += tok
                        r["daily"][i]["cost"] += c
        for r in res.values():
            for w in r["windows"].values():
                w["cost"] = round(w["cost"], 2)
            for d in r["daily"]:
                d["cost"] = round(d["cost"], 2)
        return res


def file_key(fp):
    return hashlib.sha1(fp.encode()).hexdigest()[:12]


def status_of(last_kind, age, attached):
    """working | needs_you | waiting | idle"""
    if last_kind == "text":
        return "needs_you" if attached else "idle"
    if last_kind == "tool_use":
        if age < 25:
            return "working"
        return "waiting" if attached else "idle"
    if last_kind in ("prompt", "tool_result"):
        if age < 180 and (attached or age < 30):
            return "working"
        return "idle"
    return "idle"


def transcript(fp, limit=120):
    """Readable tail of a transcript file."""
    try:
        size = os.path.getsize(fp)
        with open(fp, "rb") as f:
            f.seek(max(0, size - 1_500_000))
            data = f.read()
    except OSError:
        return []
    lines = data.splitlines()
    if size > 1_500_000:
        lines = lines[1:]
    out = []
    for raw in lines:
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        t = d.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = d.get("message") or {}
        ts = parse_ts(d.get("timestamp"))
        content = msg.get("content")
        if t == "user":
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content")
                        out.append({"t": ts, "kind": "result", "error": bool(b.get("is_error")),
                                    "text": short(text_of(c) if not isinstance(c, str) else c, 400)})
                txt = text_of(content)
                if txt.strip() and not is_noise_prompt(txt) and not d.get("isMeta"):
                    out.append({"t": ts, "kind": "user", "text": short(txt, 4000)})
            elif isinstance(content, str) and not d.get("isMeta") and not is_noise_prompt(content):
                out.append({"t": ts, "kind": "user", "text": short(content, 4000)})
            continue
        for b in content or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and b.get("text", "").strip():
                out.append({"t": ts, "kind": "assistant", "text": b["text"][:6000]})
            elif b.get("type") == "tool_use":
                inp = b.get("input") or {}
                hint = inp.get("command") or inp.get("file_path") or inp.get("path") or inp.get("pattern") \
                    or inp.get("url") or inp.get("description") or ""
                out.append({"t": ts, "kind": "tool", "name": b.get("name"), "text": short(hint, 240)})
    return out[-limit:]


# --------------------------------------------------------------------------- plan usage
METRICS = {
    "fh": ("5-hour", 5 * 3600), "sd": ("Weekly", 7 * 86400), "so": ("Weekly · Opus", 7 * 86400),
    "sn": ("Weekly · Sonnet", 7 * 86400), "cw": ("Weekly · Cowork", 7 * 86400),
    "oa": ("Weekly · OAuth apps", 7 * 86400), "om": ("Weekly · Omelette", 7 * 86400),
    "op": ("Omelette promo", 7 * 86400), "xu": ("Extra usage", None),
}


def plan_usage(desktop_dir, now=None):
    """Parses Claude desktop's plan-usage-history.json (written ~every 5 min while the app runs).
    Format: {"version":2,"samples":[{"t":<ms>,"org":"…","u":{"fh":19,"sd":100,…}}]}"""
    now = now or time.time()
    fp = Path(desktop_dir) / "plan-usage-history.json" if desktop_dir else None
    if not fp or not fp.exists():
        return {"available": False, "reason": "no-file"}
    try:
        root = json.loads(fp.read_text())
        raw = root.get("samples") or []
        version = root.get("version", 2)
    except (OSError, ValueError, AttributeError):
        return {"available": False, "reason": "unreadable"}
    samples = []
    for e in raw:
        if not isinstance(e, dict) or not isinstance(e.get("t"), (int, float)):
            continue
        u = e.get("u") if version != 1 else {k: e.get(k) for k in ("fh", "sd")}
        u = {k: float(v) for k, v in (u or {}).items() if isinstance(v, (int, float))}
        samples.append((e["t"] / 1000.0, e.get("org"), u))
    if not samples:
        return {"available": False, "reason": "empty"}
    samples.sort(key=lambda s: s[0])
    org = samples[-1][1]
    samples = [s for s in samples if s[1] == org] if org else samples
    latest_t, _, latest = samples[-1]
    metrics = []
    for code, val in latest.items():
        label, window = METRICS.get(code, (code, None))
        m = {"code": code, "label": label, "value": round(val, 2), "window": window,
             "rate_per_hour": None, "eta": None, "stale": False}
        if window:
            rate_window = max(1800, window / 5)
            stale_after = max(3600, window / 4)
            m["stale"] = (now - latest_t) > stale_after
            series = [(t, u[code]) for t, _, u in samples if code in u and t >= latest_t - rate_window]
            # keep only the stretch after the most recent reset (a drop in value)
            for i in range(len(series) - 1, 0, -1):
                if series[i][1] < series[i - 1][1] - 0.5:
                    series = series[i:]
                    break
            if len(series) >= 2 and not m["stale"]:
                (t0, v0), (t1, v1) = series[0], series[-1]
                if t1 - t0 >= 600 and v1 > v0:
                    rate = (v1 - v0) / ((t1 - t0) / 3600.0)
                    m["rate_per_hour"] = round(rate, 2)
                    if val < 100:
                        m["eta"] = latest_t + (100 - val) / rate * 3600
            m["history"] = [[round(t), u[code]] for t, _, u in samples[-400:] if code in u and t >= now - window]
        metrics.append(m)
    order = list(METRICS)
    metrics.sort(key=lambda m: order.index(m["code"]) if m["code"] in order else 99)
    windowed = [m for m in metrics if m["window"] and m["code"] in ("fh", "sd")]
    binding = max(windowed, key=lambda m: m["value"]) if windowed else None
    return {"available": True, "observed": latest_t, "org": org, "metrics": metrics,
            "binding": binding and {"code": binding["code"], "label": binding["label"], "value": binding["value"]},
            "stale": (now - latest_t) > 3600}


# --------------------------------------------------------------------------- notifications
class Notifier:
    def __init__(self, settings_fn, dry_run, log_fn, state_file=None):
        self.settings_fn = settings_fn
        self.dry = dry_run
        self.log = log_fn
        self.session_status = {}
        self.state_file = state_file
        self.armed = {}
        try:   # remember which limit alerts already fired, across restarts
            for k in json.loads(Path(state_file).read_text()):
                self.armed[tuple(k[:2]) + (int(k[2]),)] = False
        except (OSError, ValueError, TypeError, IndexError):
            pass
        self.recent = []          # surfaced to the UI as well

    def send(self, title, body, kind):
        s = self.settings_fn()
        self.recent.append({"t": time.time(), "title": title, "body": body, "kind": kind})
        self.recent = self.recent[-50:]
        if not s.get("notify_" + kind, True):
            return
        script = 'display notification %s with title %s sound name "Glass"' % (osa(body), osa(title))
        self.log(("DRY " if self.dry else "") + "notify: %s — %s" % (title, body))
        if not self.dry and shutil.which("osascript"):
            subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def sessions(self, sessions, names):
        for s in sessions:
            key = (s["profile"], s["id"])
            prev = self.session_status.get(key)
            cur = s["status"]
            self.session_status[key] = cur
            if prev is None or prev == cur:
                continue
            who = names.get(s["profile"], s["profile"])
            if prev == "working" and cur == "needs_you":
                self.send("Claude finished · %s" % s["project"], "%s — %s" % (who, short(s["title"], 80)), "done")
            elif prev == "working" and cur == "waiting":
                self.send("Claude may need approval · %s" % s["project"], "%s — waiting on %s" % (who, s["last_tool"] or "a tool"), "approval")

    def usage(self, pid, name, plan):
        if not plan.get("available") or plan.get("stale"):
            return
        thresholds = sorted({int(x) for x in self.settings_fn().get("alert_thresholds", [80, 95])})
        for m in plan["metrics"]:
            if not m["window"]:
                continue
            crossed = [th for th in thresholds if m["value"] >= th and self.armed.get((pid, m["code"], th), True)]
            for th in thresholds:
                if m["value"] >= th:
                    self.armed[(pid, m["code"], th)] = False
                elif m["value"] < th - 10:          # the window rolled over: re-arm
                    self.armed[(pid, m["code"], th)] = True
            if self.state_file:
                try:
                    Path(self.state_file).write_text(json.dumps([list(k) for k, v in self.armed.items() if v is False]))
                except OSError:
                    pass
            if crossed:                              # one alert, for the highest threshold crossed
                self.send("%s at %d%% of %s limit" % (name, m["value"], m["label"]),
                          "Switch to an account with more headroom.", "limits")


def osa(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


# --------------------------------------------------------------------------- headless runs
class Run:
    def __init__(self, profile, cwd, prompt, mode):
        self.id = uuid.uuid4().hex[:10]
        self.profile = profile
        self.cwd = cwd
        self.prompt = prompt
        self.mode = mode
        self.status = "starting"
        self.started = time.time()
        self.ended = None
        self.session_id = None
        self.model = None
        self.cost = None
        self.turns = None
        self.result = None
        self.events = []
        self.proc = None

    def summary(self, events=False):
        d = {k: getattr(self, k) for k in ("id", "profile", "cwd", "prompt", "mode", "status", "started", "ended",
                                           "session_id", "model", "cost", "turns", "result")}
        d["project"] = Path(self.cwd).name
        if events:
            d["events"] = self.events
        return d


class Runner:
    MODES = ("plan", "default", "acceptEdits")

    def __init__(self, home, dry_run, log_fn, notifier):
        self.home = Path(home)
        self.dry = dry_run
        self.log = log_fn
        self.notifier = notifier
        self.runs = {}
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            for d in json.loads((self.home / "runs.json").read_text()):
                r = Run(d["profile"], d["cwd"], d["prompt"], d["mode"])
                for k, v in d.items():
                    if k != "events" and hasattr(r, k):
                        setattr(r, k, v)
                r.events = d.get("events", [])
                if r.status in ("running", "starting"):
                    r.status = "interrupted"
                self.runs[r.id] = r
        except (OSError, ValueError, KeyError):
            pass

    def _save(self):
        with self.lock:
            runs = sorted(self.runs.values(), key=lambda r: r.started)[-40:]
            data = [r.summary(events=True) for r in runs]
        tmp = self.home / "runs.json.tmp"
        tmp.write_text(json.dumps(data))
        os.replace(tmp, self.home / "runs.json")

    def list(self):
        with self.lock:
            return [r.summary() for r in sorted(self.runs.values(), key=lambda r: r.started, reverse=True)]

    def get(self, rid):
        r = self.runs.get(rid)
        return r and r.summary(events=True)

    def start(self, profile, name, cli, config_dir, cwd, prompt, mode):
        if mode not in self.MODES:
            raise ValueError("Unknown permission mode")
        cwd = os.path.expanduser(cwd or "~")
        if not os.path.isdir(cwd):
            raise ValueError("Folder not found: %s" % cwd)
        if not prompt.strip():
            raise ValueError("Write a prompt first")
        r = Run(profile, cwd, prompt.strip(), mode)
        with self.lock:
            self.runs[r.id] = r
        env = dict(os.environ)
        if config_dir:
            env["CLAUDE_CONFIG_DIR"] = config_dir
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)
        cmd = [cli, "-p", r.prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", mode]
        self.log(("DRY " if self.dry else "RUN ") + "task %s in %s: %s" % (r.id, cwd, " ".join(cmd[:2]) + " …"))
        threading.Thread(target=self._pump, args=(r, cmd, env, name), daemon=True).start()
        return r.summary()

    def _event(self, r, kind, text, **extra):
        e = {"t": time.time(), "kind": kind, "text": text}
        e.update(extra)
        r.events.append(e)
        if len(r.events) > 600:
            r.events = r.events[-600:]

    def _pump(self, r, cmd, env, name):
        if self.dry:
            r.status = "running"
            self._event(r, "system", "Dry run: would run %s" % " ".join(cmd[:1] + ["-p", "…"] + cmd[3:]))
            time.sleep(1.5)
            self._event(r, "assistant", "This is a simulated reply (dry-run mode).")
            r.status, r.ended, r.result, r.cost = "done", time.time(), "Simulated.", 0.0
            self._save()
            return
        try:
            r.proc = subprocess.Popen(cmd, cwd=r.cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      stdin=subprocess.DEVNULL, text=True, bufsize=1, start_new_session=True)
        except OSError as e:
            r.status, r.ended = "error", time.time()
            self._event(r, "error", "Couldn't start Claude Code: %s" % e)
            self._save()
            return
        r.status = "running"
        for line in r.proc.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                if line.strip():
                    self._event(r, "system", short(line, 400))
                continue
            t = d.get("type")
            if t == "system" and d.get("subtype") == "init":
                r.session_id = d.get("session_id")
                r.model = d.get("model")
                self._event(r, "system", "Started · %s" % (r.model or "Claude"))
            elif t == "assistant":
                for b in (d.get("message") or {}).get("content") or []:
                    if b.get("type") == "text" and b.get("text", "").strip():
                        self._event(r, "assistant", b["text"][:8000])
                    elif b.get("type") == "tool_use":
                        inp = b.get("input") or {}
                        hint = inp.get("command") or inp.get("file_path") or inp.get("path") or inp.get("pattern") or ""
                        self._event(r, "tool", short(hint, 240), name=b.get("name"))
            elif t == "user":
                for b in (d.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        c = b.get("content")
                        self._event(r, "result", short(c if isinstance(c, str) else text_of(c), 400),
                                    error=bool(b.get("is_error")))
            elif t == "result":
                r.cost = d.get("total_cost_usd")
                r.turns = d.get("num_turns")
                r.result = d.get("result")
                r.session_id = d.get("session_id") or r.session_id
                if d.get("is_error"):
                    self._event(r, "error", short(d.get("result") or d.get("subtype"), 600))
        err = r.proc.stderr.read()
        code = r.proc.wait()
        if r.status == "running":
            r.status = "done" if code == 0 else "error"
        if code != 0 and err.strip():
            self._event(r, "error", short(err, 800))
        r.ended = time.time()
        self._save()
        self.notifier.send("Task %s · %s" % ("finished" if r.status == "done" else r.status, Path(r.cwd).name),
                           "%s — %s" % (name, short(r.prompt, 80)), "done")

    def stop(self, rid):
        r = self.runs.get(rid)
        if r and r.proc and r.proc.poll() is None:
            r.status = "stopped"
            r.proc.terminate()
            return True
        return False


# --------------------------------------------------------------------------- process cwd
def process_cwds(pids):
    """{pid: cwd} via lsof (macOS & Linux)."""
    if not pids or not shutil.which("lsof"):
        return {}
    try:
        out = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fn", "-p", ",".join(map(str, pids))],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return {}
    res, cur = {}, None
    for line in out.splitlines():
        if line.startswith("p"):
            cur = int(line[1:]) if line[1:].isdigit() else None
        elif line.startswith("n") and cur:
            res[cur] = line[1:]
    return res
