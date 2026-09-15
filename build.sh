#!/usr/bin/env bash
# Build the Arc version of the extension from YOUR OWN copy of the official
# "Claude in Chrome" extension. Nothing from Anthropic is stored in this
# repository: the official bundle is read from the browser that installed it,
# copied into an output directory, and patched there.
#
# Usage: bash build.sh [source-dir] [output-dir]
#   source-dir  a "<version>_0" directory of the official extension
#               (default: the newest one found under Chrome's or Arc's profiles)
#   output-dir  where the patched extension is written (default: ./build)
# Then load output-dir as an unpacked extension in arc://extensions.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_ID="fcoeoabgfenejglbffodgkkbkcdhcgfn"  # Chrome Web Store id of Claude in Chrome
SRC="${1:-}"
OUT="${2:-$HERE/build}"

# Pick a Python 3 that actually runs (the /usr/bin stub stops working until the
# Xcode license is accepted again after an Xcode update).
PY=""
for py in python3 /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys' >/dev/null 2>&1; then PY="$py"; break; fi
done
if [ -z "$PY" ]; then
  echo "error: no working python3 found (if you rely on /usr/bin/python3, run: sudo xcodebuild -license accept)" >&2
  exit 1
fi

if [ -z "$SRC" ]; then
  # Newest installed build across Chrome and Arc profiles, by version number.
  # (find exits non-zero when a profile directory is absent; that is not an error here)
  SRC="$({ find \
      "$HOME/Library/Application Support/Google/Chrome" \
      "$HOME/Library/Application Support/Google/Chrome Beta" \
      "$HOME/Library/Application Support/Google/Chrome Canary" \
      "$HOME/Library/Application Support/Arc/User Data" \
      -maxdepth 4 -type d -path "*/Extensions/$EXTENSION_ID/*_0" 2>/dev/null || true; } \
    | awk -F/ '{print $NF "\t" $0}' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1 | cut -f2-)"
  if [ -z "$SRC" ]; then
    echo "error: the official Claude in Chrome extension was not found in any Chrome or Arc profile." >&2
    echo "Install it from the Chrome Web Store first, or pass its directory as the first argument." >&2
    exit 1
  fi
fi
if [ ! -f "$SRC/manifest.json" ]; then
  echo "error: $SRC has no manifest.json" >&2
  exit 1
fi
VERSION="$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$SRC/manifest.json")"
echo "source : $SRC (version $VERSION)"
echo "output : $OUT"

case "$OUT" in
  "$HERE"|"$HERE/"|/|"$HOME"|"$HOME/") echo "error: refusing to use $OUT as the output directory" >&2; exit 1 ;;
esac
rm -rf "$OUT"
mkdir -p "$OUT"
# _metadata/ is Chrome's signature store for the installed copy; it is not part of the extension.
rsync -a --exclude '_metadata' --exclude '.DS_Store' "$SRC/" "$OUT/"

"$PY" "$HERE/scripts/apply_arc_patches.py" "$OUT"
"$PY" "$HERE/scripts/patch_sender_checks.py" "$OUT"
"$PY" "$HERE/scripts/rebrand_chrome_strings.py" "$OUT"

echo
echo "done. Load this directory as an unpacked extension in arc://extensions:"
echo "  $OUT"
echo "Re-run build.sh after the official extension updates in Chrome."
