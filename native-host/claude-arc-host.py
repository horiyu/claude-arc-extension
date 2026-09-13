#!/usr/bin/env python3
"""Native messaging host: open the Claude panel in an Arc Split View pane.

Arc exposes no API for Split View, so the panel is opened by driving Arc's own
menu through macOS System Events (see split-view.applescript). That needs
Accessibility access, and macOS attributes a process spawned by Arc to Arc,
which makes the grant unreliable. This host therefore only queues the request
in ~/Library/Application Support/claude-arc/queue/; a launchd user agent
(com.claude.arc.splitview, installed by install.sh) runs the AppleScript with
/usr/bin/osascript as its own responsible process, so the Accessibility grant
for osascript is what counts. The host waits for the result file and relays it.

Only the numeric tab id is queued; the AppleScript rebuilds the panel URL from
the fixed extension id, so the queue cannot be used to type arbitrary text.

Protocol (one request per process, as with chrome.runtime.sendNativeMessage):
  {"command": "ping"}                                  -> {"pong": true}
  {"command": "check"}                                 -> {"success": true, "detail": "..."}
  {"command": "openInSplitView", "url": "...", "tabId": N}
      -> {"success": true, "method": "menu ..."|"shortcut"} | {"success": false, "error": "..."}
Log: ~/Library/Logs/claude-arc-host.log
"""
import json
import os
import struct
import subprocess
import sys
import time

EXTENSION_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"  # fixed by the "key" field in manifest.json
LABEL = "com.claude.arc.splitview"
BASE_DIR = os.path.expanduser("~/Library/Application Support/claude-arc")
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
RESULT_DIR = os.path.join(BASE_DIR, "results")
LAUNCH_AGENT = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
LOG_PATH = os.path.expanduser("~/Library/Logs/claude-arc-host.log")

CLAIM_TIMEOUT = 20.0   # seconds for launchd to start the job and claim the request
EXEC_TIMEOUT = 45.0    # seconds for a claimed request to finish (menu walk, focus wait, paste)
ORPHAN_GRACE = 1.5     # seconds a claimed request may be missing before it counts as crashed
RESULT_MAX_AGE = 300   # seconds; older result files are pruned


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except OSError:
        pass


def read_message():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        sys.exit(0)
    length = struct.unpack("<I", raw)[0]
    if length > 1 << 20:
        raise ValueError("frame too large")
    return json.loads(sys.stdin.buffer.read(length))


def send_message(msg):
    data = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def agent_loaded():
    try:
        return subprocess.run(
            ["launchctl", "print", "gui/%d/%s" % (os.getuid(), LABEL)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def parse_outcome(outcome):
    if outcome.startswith("ok"):
        return {"success": True, "method": outcome[2:].strip()}
    if outcome.startswith("error"):
        return {"success": False, "error": outcome[5:].strip()}
    return {"success": False, "error": outcome}


def submit(request):
    """Queue one request for the launchd job and wait for its outcome."""
    if not os.path.exists(LAUNCH_AGENT):
        return {"success": False, "error": "launch agent not installed; run native-host/install.sh"}
    if not agent_loaded():
        return {"success": False, "error": "launch agent not loaded; run native-host/install.sh"}
    os.makedirs(BASE_DIR, 0o700, exist_ok=True)
    os.chmod(BASE_DIR, 0o700)
    os.makedirs(QUEUE_DIR, exist_ok=True)
    os.makedirs(RESULT_DIR, exist_ok=True)
    now = time.time()
    for entry in os.listdir(RESULT_DIR):  # results nobody collected
        path = os.path.join(RESULT_DIR, entry)
        try:
            if now - os.path.getmtime(path) > RESULT_MAX_AGE:
                os.remove(path)
        except OSError:
            pass

    name = "%d-%d" % (int(now * 1000), os.getpid())
    tmp = os.path.join(BASE_DIR, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(request)
    queue_path = os.path.join(QUEUE_DIR, name)
    os.rename(tmp, queue_path)  # atomic hand-off; launchd wakes on the new entry
    inflight_path = os.path.join(RESULT_DIR, name + ".inflight")
    result_path = os.path.join(RESULT_DIR, name)

    claim_deadline = now + CLAIM_TIMEOUT
    hard_deadline = now + EXEC_TIMEOUT
    missing_since = None
    while time.time() < hard_deadline:
        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as f:
                outcome = f.read().strip()
            if outcome:  # an empty read means the writer is not done yet
                os.remove(result_path)
                return parse_outcome(outcome)
        elif os.path.exists(queue_path):
            if time.time() >= claim_deadline:
                try:
                    os.remove(queue_path)  # withdraw; fails if the job claimed it meanwhile
                    return {"success": False,
                            "error": "%s did not pick up the request within %ds" % (LABEL, CLAIM_TIMEOUT)}
                except FileNotFoundError:
                    pass
        elif not os.path.exists(inflight_path):
            # claimed, no longer in flight, and no result: the job died or dropped it
            missing_since = missing_since or time.time()
            if time.time() - missing_since > ORPHAN_GRACE:
                return {"success": False, "error": "%s finished without reporting a result" % LABEL}
        time.sleep(0.1)
    return {"success": False, "error": "timed out waiting for %s" % LABEL}


def dispatch(msg):
    cmd = msg.get("command")
    if cmd == "ping":
        send_message({"pong": True})
    elif cmd == "check":
        r = submit("check")
        log("check -> %s" % json.dumps(r))
        send_message(r)
    elif cmd == "openInSplitView":
        tab_id = msg.get("tabId")
        url = msg.get("url")
        expected = "chrome-extension://%s/sidepanel.html?tabId=%s" % (EXTENSION_ID, tab_id)
        if type(tab_id) is not int or not (0 <= tab_id < 10 ** 12) or url != expected:
            send_message({"success": False, "error": "refusing to open a non-panel URL"})
            return
        r = submit(str(tab_id))
        log("openInSplitView -> %s" % json.dumps(r))
        send_message(r)
    else:
        send_message({"success": False, "error": "unknown command: %r" % (cmd,)})


def main():
    try:
        msg = read_message()
        if not isinstance(msg, dict):
            raise ValueError("frame is not a JSON object")
    except Exception as e:  # malformed frame
        log("bad request: %s" % e)
        send_message({"success": False, "error": str(e)})
        return
    log("request: %s" % json.dumps(msg)[:300])
    try:
        dispatch(msg)
    except Exception as e:
        log("error: %s: %s" % (type(e).__name__, e))
        send_message({"success": False, "error": "%s: %s" % (type(e).__name__, e)})


if __name__ == "__main__":
    main()
