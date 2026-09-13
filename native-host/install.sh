#!/usr/bin/env bash
# Register the "com.claude.arc" native messaging host for Arc (and Chrome, for
# testing) and install the launchd user agent that performs the Split View
# automation. Run it from a Terminal inside your GUI login session; re-run
# after moving the repository.
#
# Uninstall: launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
#            rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
#            rm ".../NativeMessagingHosts/com.claude.arc.json" (Arc and Chrome)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="$HERE/claude-arc-host.py"
SCRIPT="$HERE/split-view.applescript"
# Fixed by the "key" field in manifest.json.
EXTENSION_ID="fcoeoabgfenejglbffodgkkbkcdhcgfn"
LABEL="com.claude.arc.splitview"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
BASE="$HOME/Library/Application Support/claude-arc"
DOMAIN="gui/$(id -u)"

chmod +x "$HOST"
mkdir -p "$BASE" "$HOME/Library/LaunchAgents"
chmod 700 "$BASE"
mkdir -p "$BASE/queue" "$BASE/results"

for dir in \
  "$HOME/Library/Application Support/Arc/NativeMessagingHosts" \
  "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"; do
  mkdir -p "$dir"
  cat > "$dir/com.claude.arc.json" <<EOF
{
  "name": "com.claude.arc",
  "description": "Claude Arc Split View Helper",
  "path": "$HOST",
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
    <string>$SCRIPT</string>
  </array>
  <key>QueueDirectories</key>
  <array>
    <string>$BASE/queue</string>
  </array>
  <key>ThrottleInterval</key>
  <integer>1</integer>
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>
  <key>StandardErrorPath</key>
  <string>$HOME/Library/Logs/claude-arc-splitview.err.log</string>
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
    echo "No answer from the launch agent within 25 s. See ~/Library/Logs/claude-arc-splitview.err.log" ;;
  *)
    echo "Probe failed: $OUTCOME" ;;
esac
echo "Log: ~/Library/Logs/claude-arc-host.log"
