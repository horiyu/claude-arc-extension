"""Replace user-facing "Chrome" wording with "Arc".

Only display strings are touched. API identifiers (``chrome.runtime``), URL
schemes (``chrome-extension://``), functional ``chrome://`` navigation targets,
user-agent regexes, and the "Chrome Web Store" notice for internal builds are
left as they are, because changing them would break behaviour or state
something false.

Usage: python3 scripts/rebrand_chrome_strings.py <extension-dir>
Idempotent. Run after apply_arc_patches.py.
"""
import json
import pathlib
import re
import sys

if len(sys.argv) != 2 or not (pathlib.Path(sys.argv[1]) / "manifest.json").is_file():
    sys.exit("usage: python3 %s <extension-dir>  (a copy of the official bundle containing manifest.json)" % sys.argv[0])
W = pathlib.Path(sys.argv[1])

# Exact phrases inside the JS bundles (React defaultMessage values and plain
# error/tool strings). Each pair is (old, new).
BUNDLE_PHRASES = [
    ("Chrome extension with connected apps", "Arc extension with connected apps"),
    ("Extend what you can do in Chrome", "Extend what you can do in Arc"),
    ("<link>open Chrome settings</link>", "<link>open Arc settings</link>"),
    ('defaultMessage:"Chrome settings"', 'defaultMessage:"Arc settings"'),
    ("Scheduled tasks only run while Chrome is open on this computer",
     "Scheduled tasks only run while Arc is open on this computer"),
    ("Switch to the Chrome window you want Claude to use",
     "Switch to the Arc window you want Claude to use"),
    ("“Personal Chrome”", "“Personal Arc”"),
    ("Please open a new tab or window in Chrome.", "Please open a new tab or window in Arc."),
    ("Chrome blocked the extension from accessing this page",
     "Arc blocked the extension from accessing this page"),
    ("may be turned off in chrome://extensions.", "may be turned off in arc://extensions."),
    ("Chrome auto-removes the group", "Arc auto-removes the group"),
    ("Failed to create Chrome tab group", "Failed to create Arc tab group"),
    ("is not in Chrome group", "is not in Arc group"),
    ("under chrome://extensions → Claude → Site access.",
     "under arc://extensions → Claude → Site access."),
]

# Locale entries are rewritten wherever they mention Chrome, except the ids
# below, whose statements would become false under Arc.
I18N_KEEP = {
    "s5uJOAoEr4",  # "Click below to get the latest internal build from the Chrome Web Store."
}

JSON_STRING = r'"((?:[^"\\]|\\.)*)"'


def rebrand_text(t):
    return t.replace("Chrome", "Arc").replace("chrome://extensions", "arc://extensions")


def rebrand_json_literal(raw):
    """Re-encode the body of a JSON string literal with Arc wording."""
    value = json.loads('"' + raw + '"')
    return json.dumps(rebrand_text(value), ensure_ascii=False)


def entry_span(txt, mid):
    """Return (start, end) of the JSON value for key `mid`, or None."""
    m = re.search(r'"%s":\s*' % re.escape(mid), txt)
    if not m:
        return None
    i = m.end()
    if txt[i] == '"':
        m2 = re.compile(JSON_STRING).match(txt, i)
        return i, m2.end()
    if txt[i] == "[":
        depth = 0
        for j in range(i, len(txt)):
            if txt[j] == "[":
                depth += 1
            elif txt[j] == "]":
                depth -= 1
                if depth == 0:
                    return i, j + 1
    return None


bundle_hits = 0
for p in sorted((W / "assets").glob("*.js")):
    s = p.read_text(encoding="utf-8")
    u = s
    for old, new in BUNDLE_PHRASES:
        bundle_hits += u.count(old)
        u = u.replace(old, new)
    if u != s:
        p.write_text(u, encoding="utf-8")
print("bundle replacements:", bundle_hits)

# Translations are edited in place (string values only) so that each locale
# file keeps its original formatting. Pseudo-locales store ICU AST arrays, in
# which only the "value" strings are rewritten.
i18n_hits = 0
for p in sorted((W / "i18n").glob("*.json")):
    txt = p.read_text(encoding="utf-8")
    data = json.loads(txt)
    out = txt
    for mid, val in data.items():
        if mid in I18N_KEEP:
            continue
        flat = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
        if "Chrome" not in flat and "chrome://extensions" not in flat:
            continue
        span = entry_span(out, mid)
        if span is None:
            continue
        i, j = span
        block = out[i:j]
        if block.startswith('"'):
            new_block = re.sub(JSON_STRING, lambda m: rebrand_json_literal(m.group(1)), block, count=1)
        else:
            new_block = re.sub(r'("value":\s*)' + JSON_STRING,
                               lambda m: m.group(1) + rebrand_json_literal(m.group(2)), block)
        if new_block != block:
            i18n_hits += 1
            out = out[:i] + new_block + out[j:]
    if out != txt:
        json.loads(out)  # fail loudly rather than write a broken locale file
        p.write_text(out, encoding="utf-8")
print("i18n replacements:", i18n_hits)
