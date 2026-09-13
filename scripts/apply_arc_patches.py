import json, re, sys, pathlib
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
m["web_accessible_resources"].append({
    "matches": ["<all_urls>"],
    "resources": ["sidepanel.html", "assets/*", "sounds/*", "i18n/*", "icon-128.png", "claude_icon.svg"],
    "use_dynamic_url": False})
mp.write_text(json.dumps(m, indent=3, ensure_ascii=False) + "\n", encoding="utf-8")

# ---- 2. service worker: tab fallback when chrome.sidePanel is absent ----
sw = next((W / "assets").glob("service-worker.ts-*.js"))
s = sw.read_text(encoding="utf-8")
old_head = re.search(r'async function (\w+)\(e\)\{if\(!chrome\.sidePanel\)return \w+\("claude_chrome\.sidepanel\.unsupported_browser".*?\}\)\)\);', s)
assert old_head, "ji head not found"
fallback = (
 'async function %s(e){if(!chrome.sidePanel){'
 'const _claudeUrl=chrome.runtime.getURL(`sidepanel.html?tabId=${encodeURIComponent(e)}`);'
 'const _sr=await chrome.storage.session.get("_tabMap");const _tabMap=_sr._tabMap||{};'
 'const _existing=_tabMap[String(e)];let _needNew=true;'
 'if(_existing){try{await chrome.tabs.get(_existing);await chrome.tabs.update(_existing,{active:true});_needNew=false;}catch(_){delete _tabMap[String(e)];}}'
 'if(_needNew){const _newTab=await chrome.tabs.create({url:_claudeUrl,active:true});_tabMap[String(e)]=_newTab.id;await chrome.storage.session.set({_tabMap});'
 'try{await new Promise((res)=>{chrome.runtime.sendNativeMessage("com.claude.arc",{command:"openInSplitView",url:_claudeUrl},(r)=>{res(r);});});}catch(_){}}'
 'return void await %s(e);}' ) % (old_head.group(1), "__ARC_GI__")
# find Gi (the group-setup helper called at end of ji)
tail = re.search(r'chrome\.sidePanel\.open\(\{tabId:e\}\),await (\w+)\(e\)\}', s[old_head.end():])
assert tail, "Gi call not found"
fallback = fallback.replace("__ARC_GI__", tail.group(1))
s = s[:old_head.start()] + fallback + s[old_head.end():]
# clean _tabMap when a Claude tab is closed
old_rm = "chrome.tabs.onRemoved.addListener(async e=>{"
assert s.count(old_rm) == 1
s = s.replace(old_rm, old_rm + 'try{const _sr=await chrome.storage.session.get("_tabMap");const _m=_sr._tabMap||{};const _n=Object.fromEntries(Object.entries(_m).filter(([k,v])=>v!==e));await chrome.storage.session.set({_tabMap:_n});}catch(_){}')
# always answer DISMISS_STATIC_INDICATOR_FOR_GROUP so the message port is not left open
old_d = '"DISMISS_STATIC_INDICATOR_FOR_GROUP"===e.type&&(async()=>{'
assert s.count(old_d) == 1
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
  "condition": {"urlFilter": "||claude.ai/", "resourceTypes": ["main_frame", "sub_frame"]}},
]
(W / "cdn-redirect-rules.json").write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
print("done")
