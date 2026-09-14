import json, re, sys, pathlib
if len(sys.argv) != 2 or not (pathlib.Path(sys.argv[1]) / "manifest.json").is_file():
    sys.exit("usage: python3 %s <extension-dir>  (a copy of the official bundle containing manifest.json)" % sys.argv[0])
W = pathlib.Path(sys.argv[1])

def sub_once(path, old, new):
    p = W / path
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    assert n == 1, f"{path}: expected 1 match for {old[:60]!r}, got {n}"
    p.write_text(s.replace(old, new), encoding="utf-8")

# ---- 1. manifest.json ----
mp = W / "manifest.json"
m = json.loads(mp.read_text(encoding="utf-8"))
m["description"] = "Claude for Arc Browser"
m.pop("update_url", None)
perms = [p for p in m["permissions"] if p != "sidePanel"]
if "declarativeNetRequest" not in perms:
    perms.insert(perms.index("declarativeNetRequestWithHostAccess"), "declarativeNetRequest")
m["permissions"] = perms
m["declarative_net_request"] = {"rule_resources": [
    {"id": "arc-net-rules", "enabled": True, "path": "cdn-redirect-rules.json"}]}
# The panel is reached by a user navigation (Arc's command bar) or by chrome.tabs.create from
# the extension itself; neither needs web_accessible_resources. Keep the official entries only
# and drop the over-broad <all_urls> entry that earlier patch runs added.
m["web_accessible_resources"] = [
    w for w in m.get("web_accessible_resources", []) if "sidepanel.html" not in w.get("resources", [])]
mp.write_text(json.dumps(m, indent=3, ensure_ascii=False) + "\n", encoding="utf-8")

# ---- 2. service worker: fallback when chrome.sidePanel is absent ----
# Arc has no Side Panel API. First ask the native host (native-host/claude-arc-host.py)
# to open the panel in an Arc Split View pane; if that is unavailable or fails, open
# the panel as a regular tab. Either way the panel tab is remembered per page tab so
# that a second click re-activates it instead of opening another one.
FALLBACK_JS = (
 '/*__ARC_FALLBACK_BEGIN__*/if(!chrome.sidePanel){'
 # one open per page tab at a time: a re-click during the native round-trip joins the pending open
 'const _k=String(e);const _inflight=(globalThis.__arcInflight||(globalThis.__arcInflight=new Map()));'
 'if(_inflight.has(_k))return _inflight.get(_k);'
 'const _p=(async()=>{'
 'const _claudeUrl=chrome.runtime.getURL(`sidepanel.html?tabId=${encodeURIComponent(e)}`);'
 'const _sk="_arcPanel_"+_k;const _existing=(await chrome.storage.session.get(_sk))[_sk];'
 'if(_existing!==undefined){try{await chrome.tabs.get(_existing);await chrome.tabs.update(_existing,{active:true});await __ARC_GI__(e);return;}catch(_){await chrome.storage.session.remove(_sk);}}'
 'let _panelTabId;'
 'try{const _r=await new Promise((res)=>{chrome.runtime.sendNativeMessage("com.claude.arc",{command:"openInSplitView",url:_claudeUrl,tabId:e},(x)=>{res(chrome.runtime.lastError?null:x);});});'
 'if(_r&&_r.success){const _isPanel=(t)=>{if(typeof t.url!=="string")return false;try{const u=new URL(t.url);return u.origin===chrome.runtime.getURL("").slice(0,-1)&&u.pathname==="/sidepanel.html"&&u.searchParams.get("tabId")===String(e);}catch(_){return false;}};'
 'for(let _i=0;_i<30&&_panelTabId===undefined;_i++){await new Promise((r)=>setTimeout(r,200));const _t=(await chrome.tabs.query({})).find(_isPanel);if(_t&&_t.id!==undefined)_panelTabId=_t.id;}}}catch(_){}'
 'if(_panelTabId===undefined){const _newTab=await chrome.tabs.create({url:_claudeUrl,active:true});_panelTabId=_newTab.id;}'
 'await chrome.storage.session.set({[_sk]:_panelTabId});await __ARC_GI__(e);'
 '})().finally(()=>{_inflight.delete(_k);});_inflight.set(_k,_p);return _p;}/*__ARC_FALLBACK_END__*/')
CLEANUP_JS = ('/*__ARC_CLEANUP_BEGIN__*/try{const _all=await chrome.storage.session.get(null);'
              'const _ks=Object.keys(_all).filter((k)=>k.startsWith("_arcPanel_")&&_all[k]===e);'
              'if(_ks.length)await chrome.storage.session.remove(_ks);}catch(_){}/*__ARC_CLEANUP_END__*/')

sw = next((W / "assets").glob("service-worker.ts-*.js"))
s = sw.read_text(encoding="utf-8")
if "__ARC_FALLBACK_BEGIN__" in s:
    # re-apply: swap the previously injected block for the current template
    gi = re.search(r'chrome\.sidePanel\.open\(\{tabId:e\}\),await (\w+)\(e\)\}', s).group(1)
    s = re.sub(r"/\*__ARC_FALLBACK_BEGIN__\*/.*?/\*__ARC_FALLBACK_END__\*/",
               lambda _: FALLBACK_JS.replace("__ARC_GI__", gi), s, count=1, flags=re.S)
elif "sendNativeMessage(\"com.claude.arc\"" in s:
    # first-generation patch (no markers): replace the old fallback block in place
    old = re.search(r"if\(!chrome\.sidePanel\)\{const _claudeUrl=.*?return void await (\w+)\(e\);\}", s, re.S)
    assert old, "legacy fallback block not found"
    s = s[:old.start()] + FALLBACK_JS.replace("__ARC_GI__", old.group(1)) + s[old.end():]
else:
    old_head = re.search(r'async function (\w+)\(e\)\{if\(!chrome\.sidePanel\)return \w+\("claude_chrome\.sidepanel\.unsupported_browser".*?\}\)\)\);', s)
    assert old_head, "ji head not found"
    tail = re.search(r'chrome\.sidePanel\.open\(\{tabId:e\}\),await (\w+)\(e\)\}', s[old_head.end():])
    assert tail, "Gi call not found"
    s = (s[:old_head.start()] + "async function %s(e){" % old_head.group(1)
         + FALLBACK_JS.replace("__ARC_GI__", tail.group(1)) + s[old_head.end():])
# forget the panel tab when it is closed
old_rm = "chrome.tabs.onRemoved.addListener(async e=>{"
assert s.count(old_rm) == 1
legacy = 'try{const _sr=await chrome.storage.session.get("_tabMap");const _m=_sr._tabMap||{};const _n=Object.fromEntries(Object.entries(_m).filter(([k,v])=>v!==e));await chrome.storage.session.set({_tabMap:_n});}catch(_){}'
s = s.replace(old_rm + legacy, old_rm)
if "__ARC_CLEANUP_BEGIN__" in s:
    s = re.sub(r"/\*__ARC_CLEANUP_BEGIN__\*/.*?/\*__ARC_CLEANUP_END__\*/", lambda _: CLEANUP_JS, s, count=1, flags=re.S)
else:
    s = s.replace(old_rm, old_rm + CLEANUP_JS)
# always answer DISMISS_STATIC_INDICATOR_FOR_GROUP so the message port is not left open
old_d = '"DISMISS_STATIC_INDICATOR_FOR_GROUP"===e.type&&(async()=>{'
if old_d in s:
    s = s.replace(old_d, '"DISMISS_STATIC_INDICATOR_FOR_GROUP"===e.type?(async()=>{')
    old_e = 'else n({success:!1})})();var r,i}'
    assert s.count(old_e) == 1, s.count(old_e)
    s = s.replace(old_e, 'else n({success:!1})})():n({success:!1});var r,i}')
sw.write_text(s, encoding="utf-8")

# ---- 3. branding strings ----
count = 0
for p in list(W.rglob("*.js")) + list(W.rglob("*.json")) + list(W.rglob("*.html")):
    t = p.read_text(encoding="utf-8")
    u = t.replace("Claude in Chrome", "Claude in Arc").replace("Claude for Chrome", "Claude in Arc")
    if u != t:
        count += t.count("Claude in Chrome") + t.count("Claude for Chrome")
        p.write_text(u, encoding="utf-8")
print("branding replacements:", count)

# ---- 4. network rules ----
rules = [
 {"id": 1, "priority": 1,
  "action": {"type": "modifyHeaders", "responseHeaders": [
     {"header": "Access-Control-Allow-Origin", "operation": "set", "value": "*"},
     {"header": "Cross-Origin-Resource-Policy", "operation": "set", "value": "cross-origin"}]},
  "condition": {"urlFilter": "https://claude.ai/images/*", "resourceTypes": ["image", "xmlhttprequest", "other"]}},
 {"id": 2, "priority": 2,
  "action": {"type": "modifyHeaders", "responseHeaders": [
     {"header": "Content-Security-Policy", "operation": "remove"}]},
  "condition": {"urlFilter": "||claude.ai/", "resourceTypes": ["sub_frame"]}},
]
(W / "cdn-redirect-rules.json").write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
print("done")
