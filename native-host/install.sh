#!/usr/bin/env bash
# Register the "com.claude.arc" native messaging host for Arc and install the
# launchd user agent that performs the Split View automation. Run it from a
# Terminal inside your GUI login session; re-run after moving the repository.
# Set WITH_CHROME=1 to also register the host with Google Chrome (developer
# testing only: the allowed origin is the same extension id as the official
# Claude in Chrome extension, so the default registers Arc only).
#
# Uninstall: launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
#            rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
#            rm ".../NativeMessagingHosts/com.claude.arc.json" (Arc; and Chrome if WITH_CHROME=1 was used)
#            remove /usr/bin/osascript from System Settings > Privacy & Security > Accessibility
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="$HERE/claude-arc-host"  # sh launcher that picks a working python3 for claude-arc-host.py
SCRIPT="$HERE/split-view.applescript"
# Fixed by the "key" field in manifest.json.
EXTENSION_ID="fcoeoabgfenejglbffodgkkbkcdhcgfn"
LABEL="com.claude.arc.splitview"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
BASE="$HOME/Library/Application Support/claude-arc"
DOMAIN="gui/$(id -u)"

# Escape user-controlled paths for the JSON manifest and the XML plist.
json_esc() { sed 's/\\/\\\\/g; s/"/\\"/g'; }
xml_esc()  { sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }

chmod +x "$HOST" "$HERE/claude-arc-host.py"

# Arc starts the host with the login session's PATH, not the shell's; probe it the same way.
ARC_PATH="$(launchctl getenv PATH 2>/dev/null || true)"
ARC_PATH="${ARC_PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"
if ! printf '\x12\x00\x00\x00{"command":"ping"}' \
  | env -i PATH="$ARC_PATH" HOME="$HOME" "$HOST" 2>/dev/null | tail -c +5 | grep -q '"pong": true'; then
  echo "error: $HOST does not start with the PATH Arc uses ($ARC_PATH)." >&2
  echo "No working Python 3 was found (/usr/bin/python3 may need 'sudo xcodebuild -license accept';" >&2
  echo "python.org or Homebrew installs are also accepted). Fix that and run this script again." >&2
  exit 1
fi

mkdir -p "$BASE" "$HOME/Library/LaunchAgents"
chmod 700 "$BASE"
mkdir -p "$BASE/queue" "$BASE/results"

DIRS=("$HOME/Library/Application Support/Arc/NativeMessagingHosts")
if [ "${WITH_CHROME:-0}" = 1 ]; then
  DIRS+=("$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts")
fi
for dir in "${DIRS[@]}"; do
  mkdir -p "$dir"
  cat > "$dir/com.claude.arc.json" <<EOF
{
  "name": "com.claude.arc",
  "description": "Claude Arc Split View Helper",
  "path": "$(printf '%s' "$HOST" | json_esc)",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF
  echo "wrote $dir/com.claude.arc.json"
done

# The launchd job runs osascript whenever the queue directory is non-empty.
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
rm -f "$BASE/queue/"* "$BASE/results/"* 2>/dev/null || true
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/osascript</string>
    <string>$(printf '%s' "$SCRIPT" | xml_esc)</string>
  </array>
  <key>QueueDirectories</key>
  <array>
    <string>$(printf '%s' "$BASE" | xml_esc)/queue</string>
  </array>
  <key>ThrottleInterval</key>
  <integer>1</integer>
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>
  <key>StandardErrorPath</key>
  <string>$(printf '%s' "$HOME" | xml_esc)/Library/Logs/claude-arc-splitview.err.log</string>
</dict>
</plist>
EOF
launchctl enable "$DOMAIN/$LABEL" 2>/dev/null || true
if ! launchctl bootstrap "$DOMAIN" "$PLIST"; then
  rm -f "$PLIST"  # keep "plist exists" equivalent to "agent loaded" for the host
  echo "error: could not load $LABEL. Run this script from Terminal in your GUI login" >&2
  echo "session and check System Settings > General > Login Items > Allow in the Background." >&2
  exit 1
fi
echo "loaded launch agent $LABEL"

# Probe Accessibility now, while the user is at the terminal to answer prompts.
echo
echo "Probing Accessibility through the launch agent (up to 25 s)..."
echo "If macOS asks whether osascript may control System Events, click Allow."
NAME="$(( $(date +%s) * 1000 ))-$$"
printf 'check' > "$BASE/$NAME.tmp"
mv "$BASE/$NAME.tmp" "$BASE/queue/$NAME"
OUTCOME=""
for _ in $(seq 1 250); do
  if [ -s "$BASE/results/$NAME" ]; then
    OUTCOME="$(cat "$BASE/results/$NAME")"
    rm -f "$BASE/results/$NAME"
    break
  fi
  sleep 0.1
done
rm -f "$BASE/queue/$NAME"
case "$OUTCOME" in
  ok*)
    echo "Accessibility OK: $OUTCOME"
    echo "Reload the extension in arc://extensions and click the Claude icon." ;;
  *1719*)
    echo "Accessibility is NOT granted to /usr/bin/osascript."
    echo "System Settings > Privacy & Security > Accessibility > + > Cmd+Shift+G > /usr/bin/osascript,"
    echo "switch it on, then run this script again." ;;
  *1743*)
    echo "Automation consent is missing: allow osascript to control System Events"
    echo "(System Settings > Privacy & Security > Automation), then run this script again." ;;
  "")
    echo "No answer from the launch agent within 25 s. If a permission dialog was showing, answer it"
    echo "and run this script again; otherwise see ~/Library/Logs/claude-arc-splitview.err.log" ;;
  *)
    echo "Probe failed: $OUTCOME" ;;
esac
echo "Log: ~/Library/Logs/claude-arc-host.log"
