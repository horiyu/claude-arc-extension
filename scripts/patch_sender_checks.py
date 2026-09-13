"""Recognise the tab-hosted panel as a side-panel sender.

The official build treats a runtime message as coming from its own side panel
only when ``sender.tab`` is undefined. In Arc the panel is a regular tab, so
every message from the panel (and from the claude.ai Cowork iframe inside it)
is rejected as "not a side panel" and the panel reports that the extension did
not respond. This script widens the check to also accept senders whose tab's
top-level URL is the extension's own ``sidepanel.html``. Only extension pages
can have that URL as the top frame, so ordinary web pages still fail the check.

Usage: python3 scripts/patch_sender_checks.py <extension-dir>
Idempotent: running it twice is safe. Run ``apply_arc_patches.py`` first.
"""
import pathlib
import sys

W = pathlib.Path(sys.argv[1])

GUARD = (
    'function __arcIsPanel(s){return void 0===s.tab||!!(s.tab&&"string"==typeof s.tab.url'
    '&&s.tab.url.startsWith(chrome.runtime.getURL("sidepanel.html")))}'
)
INLINE = (
    '(void 0===t.tab||!!(t.tab&&"string"==typeof t.tab.url'
    '&&t.tab.url.startsWith(chrome.runtime.getURL("sidepanel.html"))))'
)


def replace_once(text, old, new, label):
    n = text.count(old)
    assert n == 1, f"{label}: expected exactly 1 match for {old[:60]!r}, got {n}"
    return text.replace(old, new)


sw = next((W / "assets").glob("service-worker.ts-*.js"))
s = sw.read_text(encoding="utf-8")
if "__arcIsPanel" in s:
    print("service worker: already patched")
else:
    s = replace_once(
        s,
        "function ki(e){return void 0===e.tab&&e.id===chrome.runtime.id}",
        GUARD + "function ki(e){return __arcIsPanel(e)&&e.id===chrome.runtime.id}",
        "sw ki()",
    )
    s = replace_once(
        s,
        "const r=void 0===i.tab,a=zi(i.origin)",
        "const r=__arcIsPanel(i),a=zi(i.origin)",
        "sw get_sidepanel_host_info",
    )
    s = replace_once(
        s,
        'if(void 0!==i.tab||!zi(i.origin))return void o({ok:!1,error:"Action not allowed from this origin/context"})',
        'if(!__arcIsPanel(i)||!zi(i.origin))return void o({ok:!1,error:"Action not allowed from this origin/context"})',
        "sw sidepanel actions",
    )
    sw.write_text(s, encoding="utf-8")
    print("service worker: patched", sw.name)

mcp = next((W / "assets").glob("mcpPermissions-*.js"))
m = mcp.read_text(encoding="utf-8")
old = '"sidepanel-voice-auth"!==e.name)return;const t=e.sender;t&&void 0===t.tab&&t.id===chrome.runtime.id?'
new = '"sidepanel-voice-auth"!==e.name)return;const t=e.sender;t&&' + INLINE + '&&t.id===chrome.runtime.id?'
if new in m:
    print("mcpPermissions: already patched")
else:
    m = replace_once(m, old, new, "mcp voice-auth port")
    mcp.write_text(m, encoding="utf-8")
    print("mcpPermissions: patched", mcp.name)
