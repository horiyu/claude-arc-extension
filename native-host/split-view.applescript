-- Runs under launchd (com.claude.arc.splitview) whenever the queue directory
-- ~/Library/Application Support/claude-arc/queue/ is non-empty.
--
-- The native host writes one file per request, named <unix-ms>-<pid>, whose
-- content is the word "check" (probe Accessibility without touching Arc),
-- the word "dump" (write Arc's accessibility tree to a log, for diagnosis),
-- or a numeric Chrome tab id. The panel URL is rebuilt here from the
-- fixed extension id, so nothing read from the queue is ever typed into Arc.
-- The outcome is written atomically to results/<same name> as
-- "ok <detail>" or "error <number> <message>".
--
-- Being spawned by launchd rather than by Arc makes /usr/bin/osascript its own
-- responsible process for macOS privacy checks, so the Accessibility grant for
-- osascript applies here. System Events additionally needs Automation consent
-- (macOS asks once: "osascript wants access to control System Events").

property extensionId : "fcoeoabgfenejglbffodgkkbkcdhcgfn"
-- Menu items tried first by direct lookup, as {menu title, item title}.
property menuCandidates : {{"View", "Add Split View"}, {"View", "Add Vertical Split View"}, {"View", "New Vertical Split View"}, {"Tabs", "Add Split View"}, {"Tabs", "Add Vertical Split View"}, {"Window", "Add Split View"}, {"Window", "Add Vertical Split View"}}
-- Item titles searched across every menu and submenu when the lookup fails.
property itemNames : {"Add Split View", "Add Vertical Split View", "New Vertical Split View"}
-- Requests older than this are dropped: the host that wrote them has given up.
property staleAfterMs : 30000
-- How long to wait (x 0.1 s) for Arc's command bar to take focus.
property focusWaitTries : 25

on run
	set homeDir to POSIX path of (path to home folder)
	set baseDir to homeDir & "Library/Application Support/claude-arc/"
	set queueDir to baseDir & "queue/"
	set resultDir to baseDir & "results/"
	set logPath to homeDir & "Library/Logs/claude-arc-host.log"
	try
		do shell script "mkdir -p " & quoted form of queueDir & " " & quoted form of resultDir & "; find " & quoted form of resultDir & " -type f -mmin +5 -delete 2>/dev/null; true"
	end try
	repeat
		-- -A: launchd counts dotfiles as queue entries, so this script must see them too
		set nextName to do shell script "ls -1A " & quoted form of queueDir & " 2>/dev/null | head -n 1"
		if nextName is "" then exit repeat
		set reqPath to queueDir & nextName
		if not my isRequestName(nextName) then
			-- not written by the host (.DS_Store, editor swap file, ...); it would keep launchd respawning
			try
				do shell script "rm -rf " & quoted form of reqPath
			on error errMsg
				my logLine(logPath, "launchd: cannot remove stray queue entry " & nextName & ": " & errMsg)
				exit repeat
			end try
		else
			set inflightPath to resultDir & nextName & ".inflight"
			set request to ""
			try
				-- atomic claim: a request the host withdrew meanwhile simply fails to move
				do shell script "mv " & quoted form of reqPath & " " & quoted form of inflightPath
				set request to do shell script "cat " & quoted form of inflightPath
			end try
			if request is not "" then
				if my isStale(nextName) then
					my logLine(logPath, "launchd: dropped stale request " & nextName)
				else
					set outcome to ""
					try
						if request is "check" then
							set outcome to "ok " & my probeAccessibility()
						else if request is "dump" then
							set outcome to "ok " & my dumpFrontWindow(homeDir & "Library/Logs/claude-arc-axdump.txt")
						else if my isTabId(request) then
							set outcome to "ok " & my openSplit("chrome-extension://" & extensionId & "/sidepanel.html?tabId=" & request)
						else
							error "refusing request (" & (length of request) & " chars)"
						end if
					on error errMsg number errNum
						set outcome to "error " & errNum & " " & errMsg
					end try
					my writeResult(resultDir & nextName, outcome)
					my logLine(logPath, "launchd: " & outcome)
				end if
			end if
			try
				do shell script "rm -f " & quoted form of inflightPath
			end try
		end if
	end repeat
end run

-- ---------------------------------------------------------------- requests

on isRequestName(entryName)
	set r to do shell script "printf '%s' " & quoted form of entryName & " | grep -Eq '^[0-9]+-[0-9]+$' && echo yes || echo no"
	return r is "yes"
end isRequestName

on isTabId(request)
	set r to do shell script "printf '%s' " & quoted form of request & " | grep -Eq '^[0-9]{1,12}$' && echo yes || echo no"
	return r is "yes"
end isTabId

on isStale(entryName)
	set dashPos to offset of "-" in entryName
	if dashPos < 2 then return true
	set stampMs to (text 1 thru (dashPos - 1) of entryName) as number
	set nowMs to ((do shell script "date +%s") as number) * 1000
	return (nowMs - stampMs) > staleAfterMs
end isStale

on writeResult(resultPath, outcome)
	set tmpPath to resultPath & ".tmp"
	try
		do shell script "printf '%s' " & quoted form of outcome & " > " & quoted form of tmpPath & " && mv -f " & quoted form of tmpPath & " " & quoted form of resultPath
	end try
end writeResult

on logLine(logPath, msg)
	try
		do shell script "printf '%s %s\\n' \"$(date '+%Y-%m-%d %H:%M:%S')\" " & quoted form of msg & " >> " & quoted form of logPath
	end try
end logLine

-- ---------------------------------------------------------------- probe

on probeAccessibility()
	tell application "System Events"
		if not (UI elements enabled) then error "osascript is not allowed assistive access" number -1719
		set frontName to name of first application process whose frontmost is true
		-- a real Accessibility read, on a process that always exists; raises -1719 when untrusted
		set barCount to count of menu bar items of menu bar 1 of process "Finder"
	end tell
	return "check frontmost=" & frontName & " finder-menus=" & barCount
end probeAccessibility

-- ---------------------------------------------------------------- diagnostics

-- Writes the accessibility tree of Arc's front window (web content excluded)
-- to outPath, one element per line, so the split view structure can be read.
on dumpFrontWindow(outPath)
	set collected to {}
	tell application "System Events"
		if not (exists process "Arc") then error "Arc is not running"
		tell process "Arc"
			set winCount to count of windows
			repeat with i from 1 to winCount
				set wi to window i
				set wname to ""
				try
					set wname to name of wi
				end try
				set end of collected to "window " & i & ": [" & wname & "] subrole=" & (value of attribute "AXSubrole" of wi) & " main=" & (value of attribute "AXMain" of wi) & " focused=" & (value of attribute "AXFocused" of wi)
			end repeat
			set w to front window
		end tell
	end tell
	my walkElement(w, 0, collected, 16)
	set AppleScript's text item delimiters to linefeed
	set body to collected as text
	set AppleScript's text item delimiters to ""
	set fileRef to open for access (POSIX file outPath) with write permission
	try
		set eof fileRef to 0
		write body & linefeed to fileRef as «class utf8»
	end try
	close access fileRef
	return "dump " & (count of collected) & " elements -> " & outPath
end dumpFrontWindow

on walkElement(el, depth, collected, maxDepth)
	set r to ""
	set sr to ""
	set d to ""
	set extra to ""
	tell application "System Events"
		try
			set r to value of attribute "AXRole" of el
		end try
		try
			set sr to value of attribute "AXSubrole" of el
			if sr is missing value then set sr to ""
		end try
		try
			set d to value of attribute "AXDescription" of el
			if d is missing value then set d to ""
		end try
		try
			set p to value of attribute "AXPosition" of el
			set s to value of attribute "AXSize" of el
			set extra to extra & " pos=" & (item 1 of p) & "," & (item 2 of p) & " size=" & (item 1 of s) & "x" & (item 2 of s)
		end try
		try
			set extra to extra & " children=" & (count of (value of attribute "AXChildren" of el))
		end try
		if depth ≤ 3 then
			try
				set extra to extra & " attrs=" & ((name of attributes of el) as text)
			end try
		end if
		if r is "AXSplitter" or r is "AXSplitGroup" then
			try
				set extra to extra & " value=" & (value of attribute "AXValue" of el)
			end try
			try
				set extra to extra & " min=" & (value of attribute "AXMinValue" of el) & " max=" & (value of attribute "AXMaxValue" of el)
			end try
			try
				set extra to extra & " orientation=" & (value of attribute "AXOrientation" of el)
			end try
			try
				set extra to extra & " settable=" & (settable of attribute "AXValue" of el)
			end try
			try
				set extra to extra & " actions=" & ((name of actions of el) as text)
			end try
		end if
	end tell
	set indent to ""
	repeat depth times
		set indent to indent & "  "
	end repeat
	set end of collected to indent & r & " " & sr & " [" & d & "]" & extra
	if depth < maxDepth and r is not "AXWebArea" then
		set kids to {}
		try
			tell application "System Events" to set kids to UI elements of el
		end try
		repeat with k in kids
			my walkElement(k, depth + 1, collected, maxDepth)
		end repeat
	end if
end walkElement

-- ---------------------------------------------------------------- split view

on openSplit(theURL)
	tell application "System Events"
		if not (exists process "Arc") then error "Arc is not running"
		set frontmost of process "Arc" to true
	end tell
	delay 0.2
	set method to my addSplitPane()
	set focusInfo to my waitForCommandBar()
	if focusInfo starts with "no:" then error "Arc's command bar did not take focus after adding a split pane (" & focusInfo & ")"
	my pasteAndGo(theURL)
	return method
end openSplit

on addSplitPane()
	-- 1. known menu items, looked up directly (fast, no menu enumeration)
	repeat with pair in menuCandidates
		set menuName to item 1 of pair
		set itemName to item 2 of pair
		try
			tell application "System Events" to tell process "Arc"
				set mi to menu item itemName of menu 1 of menu bar item menuName of menu bar 1
				if enabled of mi then
					click mi
					return "menu " & menuName & " > " & itemName
				end if
			end tell
		end try
	end repeat
	-- 2. search every menu, submenus included, for the known item titles
	tell application "System Events" to tell process "Arc"
		set barItems to menu bar items of menu bar 1
	end tell
	repeat with barItem in barItems
		try
			set found to my clickIn(menu 1 of barItem)
			if found is not "" then return "menu " & found
		end try
	end repeat
	-- 3. Arc's default shortcut for a new vertical split
	tell application "System Events" to tell process "Arc"
		keystroke "=" using {control down, shift down}
	end tell
	return "shortcut"
end addSplitPane

on clickIn(aMenu)
	tell application "System Events"
		set names to name of every menu item of aMenu
	end tell
	repeat with i from 1 to count of names
		set n to item i of names
		if n is not missing value then
			if n is in itemNames then
				tell application "System Events"
					set mi to menu item i of aMenu
					if enabled of mi then
						click mi
						return n
					end if
				end tell
			end if
		end if
	end repeat
	repeat with i from 1 to count of names
		try
			tell application "System Events" to set sub to menu 1 of menu item i of aMenu
			set r to my clickIn(sub)
			if r is not "" then return r
		end try
	end repeat
	return ""
end clickIn

-- Returns "ok" once a native text input outside web content has focus,
-- otherwise "no:<what was focused>" so the failure can be diagnosed.
on waitForCommandBar()
	set lastSeen to "nothing"
	repeat focusWaitTries times
		delay 0.1
		try
			tell application "System Events" to tell process "Arc"
				set fe to value of attribute "AXFocusedUIElement"
				set r to value of attribute "AXRole" of fe
			end tell
			set lastSeen to r
			if r is in {"AXTextField", "AXTextArea", "AXComboBox"} then
				if my insideWebArea(fe) then
					set lastSeen to r & " inside AXWebArea"
				else
					return "ok"
				end if
			end if
		on error errMsg
			set lastSeen to "error: " & errMsg
		end try
	end repeat
	return "no:" & lastSeen
end waitForCommandBar

on insideWebArea(el)
	set cur to el
	repeat 15 times
		try
			tell application "System Events" to set cur to value of attribute "AXParent" of cur
		on error
			return false
		end try
		if cur is missing value then return false
		try
			tell application "System Events" to set r to value of attribute "AXRole" of cur
			if r is "AXWebArea" then return true
		end try
	end repeat
	return false
end insideWebArea

-- Paste rather than type: immune to the active input method (e.g. Japanese IME).
-- The previous clipboard contents are saved as a record and put back afterwards.
on pasteAndGo(theURL)
	set oldClip to missing value
	try
		set oldClip to (the clipboard as record) -- a record keeps non-text flavors (images, files) restorable
	end try
	set the clipboard to theURL
	tell application "System Events" to tell process "Arc"
		keystroke "a" using {command down}
		keystroke "v" using {command down}
		delay 0.25
		key code 117 -- forward delete: discard inline autocompletion, if any
		key code 36 -- return
	end tell
	delay 0.3
	if oldClip is not missing value then
		try
			set the clipboard to oldClip
		end try
	end if
end pasteAndGo
