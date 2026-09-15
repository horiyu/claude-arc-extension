# Claude in Arc

[日本語](#日本語) | [English](#english)

## 日本語

公式の「Claude in Chrome」拡張機能を，Side Panel API を持たない Arc ブラウザで動かすための，個人利用向けの非公式パッチ集です．利用者が自分で入手した公式拡張機能に手元でパッチを当てて Arc 版を生成します．本リポジトリに Anthropic の配布物は含まれていません．生成した Claude のパネルは通常タブとして，または任意で Arc の Split View のペインとして開きます．

> [!WARNING]
> このリポジトリは非公式・実験的なものです．Anthropic，Claude，The Browser Company，Arc とは関係ありません．

![Arc の Split View で開いた Claude のパネルが，隣のタブの GitHub ページを操作している様子](docs/demo.png)

左が操作対象のタブ，右が Split View で開いた Claude のパネルです．パネルからの指示で，隣のタブのページを読み取り，操作できます．操作中のタブにはオレンジ色の枠と「Stop Claude」ボタンが表示されます．

## 概要

この拡張機能は，Arc の拡張機能として Claude を開き，ブラウザ内での作業を補助することを目的としています．

主な用途は次の通りです．

- Claude のパネルを通常タブ，または Arc の Split View のペインとして開く
- Claude と会話しながらブラウザ操作を補助する
- タスクのスケジュール実行や通知を利用する
- 必要に応じてファイル操作やダウンロード機能を利用する

## 仕組みと変更点

`build.sh` は，Chrome（または Arc）にインストール済みの公式「Claude in Chrome」拡張機能（拡張機能 ID `fcoeoabgfenejglbffodgkkbkcdhcgfn`）を `build/` に複製し，`scripts/` の 3 つのスクリプトで次の変更を加えます．公式拡張機能はバージョン 1.0.93 で確認しています．

- Arc に Side Panel API が無いため，サイドパネルの代わりに拡張機能ページを通常タブとして開く
- `Claude in Chrome` 等の表示文言を `Claude in Arc` に置換する
- `declarativeNetRequest` で，`claude.ai/images/*` の応答に CORS ヘッダーを付与し，`claude.ai` の iframe（`sub_frame`）応答から `Content-Security-Policy` ヘッダーを除去する（パネル内で claude.ai を iframe 表示するため）．通常のタブで開いた claude.ai には適用しない
- Arc では `chrome.tabs.group` などタブグループ API の Promise が解決しないため，service worker 内でタブグループを擬似的に実装する（パネルと拡張機能の初期化はタブグループを前提としており，これが無いとブラウザ操作がすべてタイムアウトする）
- 拡張機能の読み込み前から開いていたページには，ページ読み取り用の補助スクリプトを実行時に注入する（公式版では該当ページの再読み込みが必要）
- 任意で，同梱のネイティブホストにより Arc の Split View としてパネルを開く（後述）

スクリプトの役割は次の通りです．`apply_arc_patches.py` はマニフェスト，通常タブへのフォールバック，タブグループの擬似実装，補助スクリプトの注入，ネットワークルールを適用します．`patch_sender_checks.py` は，サイドパネルを通常タブで代替している Arc 版でも service worker がパネルからのメッセージを受け付けるようにします．`rebrand_chrome_strings.py` は，画面に表示される「Chrome」の表記を「Arc」に置き換えます．いずれも `build/` 内のファイルだけを書き換え，公式拡張機能のインストール先には触れません．

生成物 `build/` は，利用者自身が入手した公式拡張機能の複製にパッチを当てたものです．その権利は Anthropic および各コンポーネント（gif.js や KaTeX フォントなど）の元の著作権者に帰属します．本リポジトリの作者が権利を有するのは `scripts/`，`native-host/`，`build.sh` および Arc 向けの変更内容に限られ，`build/` は `.gitignore` により追跡対象外です．

## 注意事項

この拡張機能は開発者向け・検証用途のものです．公開ストアで配布される一般利用向け拡張機能ではありません．

また，生成される `manifest.json` は以下のような強い権限を要求します（完全な一覧は `manifest.json` の `permissions` を参照してください）．

- `host_permissions: ["<all_urls>"]`
- `debugger`
- `tabs`
- `scripting`
- `downloads`
- `nativeMessaging`
- `declarativeNetRequest`
- `webNavigation`
- `notifications`
- `identity`
- `tabGroups`

これらの権限は，閲覧中のページ情報へのアクセス，ブラウザ操作，ページ遷移の検知，ネットワークルールの適用，通知の表示，ダウンロード，OAuth によるサインイン，外部プロセス連携などに関係します．
内容を理解したうえで，自分の管理下にある環境でのみ利用してください．

## インストール

### 前提条件

- macOS と Arc
- 同じ Mac の Chrome（または Arc）に，Chrome Web Store から公式の「Claude in Chrome」拡張機能がインストールされていること．`build.sh` はそこから複製します
- Python 3（`build.sh` と，Split View 連携のネイティブホストが使います）．`/usr/bin/python3`（Xcode Command Line Tools），python.org 版，Homebrew 版のいずれかで構いません．`/usr/bin/python3` は Xcode の更新後にライセンス再同意（`sudo xcodebuild -license accept`）を求めて停止することがありますが，他の Python があればそちらが使われます
- claude.ai のアカウント．パネルは有料プランを要求します

### 手順

1. このリポジトリをローカルに clone する
2. `bash build.sh` を実行する．公式拡張機能の最新版を探して `build/` に Arc 版を生成する．複数のプロファイルにある場合は最も新しいバージョンを使う．別の場所にある場合は `bash build.sh <公式拡張機能のディレクトリ>` と指定する
3. Arc を開き，アドレスバーに `arc://extensions` と入力する
4. 右上の「デベロッパーモード」を有効化する
5. 「パッケージ化されていない拡張機能を読み込む」をクリックし，`build/` を選択する
6. ツールバーの Claude アイコンをクリックする（Cmd+E でも開く）．パネルは通常タブとして開き，claude.ai へのサインインを求められる

生成物の `manifest.json` には公式版の公開鍵が含まれているため，拡張機能 ID は公式版と同じになり，どのディレクトリから読み込んでも変わりません．隣のペインに開きたい場合は次節の設定を追加してください．

公式拡張機能が Chrome 側で更新されたら，`bash build.sh` を再実行し，`arc://extensions` で再読み込みしてください．最初の 2 つのスクリプトは minify された識別子を文字列一致で探して書き換えるため，公式ビルド側のコードが変わると `AssertionError` で停止します．その場合はスクリプト内の検索パターンを新しいビルドに合わせて更新してください．3 つ目は見つからない語句を読み飛ばすだけで停止しないため，出力される置換件数を確認し，残った「Chrome」表記があれば語句リストに追加してください．

拡張機能を外すには，`arc://extensions` で「削除」を押してから，`build/` を削除します．先にディレクトリを消すと一覧に壊れた項目が残ります．Split View 連携を登録している場合は次節の解除手順も実行してください．

## Split View で開く（任意）

Arc には Side Panel API が無いため，既定ではパネルを通常タブとして開きます．同梱のネイティブメッセージングホストと launchd エージェントを登録すると，ツールバーのアイコンや Cmd+E で，現在のタブの隣に Split View としてパネルを開きます．

1. システム設定 → プライバシーとセキュリティ → アクセシビリティ で「＋」を押し，Cmd+Shift+G で `/usr/bin/osascript` を指定して追加し，オンにする．この許可は本プロジェクトではなく `/usr/bin/osascript` そのものに与えられるため，以後は同じユーザーで動くどのプロセスでも，launchd 経由などで `osascript` を起動すれば同じ許可の下で GUI を操作できるようになる．Split View 連携をやめるときは，後述の解除手順でこの許可も外すこと
2. ターミナルで `native-host/install.sh` を実行する．ネイティブホスト（`native-host/claude-arc-host`．内部で `claude-arc-host.py` を起動します）が Arc に登録され（`~/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json`），launchd ユーザーエージェント `com.claude.arc.splitview` が読み込まれる．続けてアクセシビリティの検査が走り，結果が表示される．初回は「osascript が System Events を制御することを許可しますか」という確認が出るので許可する．開発時の検証用に Google Chrome にも同じ登録を書き込む場合は `WITH_CHROME=1 native-host/install.sh` として実行する
3. `arc://extensions` で拡張機能を再読み込みし，Claude アイコンをクリックする

仕組みは次の通りです．ホストはタブ ID だけを `~/Library/Application Support/claude-arc/queue/` に書き，launchd がそれを検知して `/usr/bin/osascript` で `native-host/split-view.applescript` を実行します．AppleScript はパネルの URL を固定の拡張機能 ID から組み立て直し（キューの内容をそのまま入力することはしない），System Events で Arc のメニューから「Add Split View」「Add Vertical Split View」などの項目を探してクリックします（見つからなければ Arc の既定ショートカット Control+Shift+= を送ります）．新しいペインの入力欄にフォーカスが移ったことを確認してから，URL をクリップボード経由で貼り付けて Return を送ります．貼り付けの前後でクリップボードの内容を退避・復元しますが，その間は一時的に置き換わります．入力欄が見つからなければ何も入力せずエラーを返し，拡張機能は通常タブで開きます．

Arc の子プロセスから直接 AppleScript を実行すると，macOS はアクセシビリティ権限を Arc に帰属させて判定するため，許可が安定して効きません．launchd から起動した `osascript` は自分自身が責任元になるので，`osascript` への許可がそのまま適用されます．動作の記録は `~/Library/Logs/claude-arc-host.log` に残ります（ホストと AppleScript の両方が書き込みます）．launchd が起動した `osascript` の標準エラーは `~/Library/Logs/claude-arc-splitview.err.log` に出ます．

Split View が開かなくなった場合（Arc の更新後など）は，ターミナルで次を実行してください．Arc の最前面ウィンドウのアクセシビリティツリー（Web コンテンツの内部を除く）が `~/Library/Logs/claude-arc-axdump.txt` に書き出され，メニュー項目名や分割の構造が変わっていないかを確認できます．ウィンドウ名やタブ名を含むため，不要になったら削除してください．

```
n="$(( $(date +%s) * 1000 ))-$$"; d="$HOME/Library/Application Support/claude-arc"; printf dump > "$d/$n.tmp" && mv "$d/$n.tmp" "$d/queue/$n"
```

### ペインの幅について

ペインの幅は自動では変えません．Arc は分割位置をアクセシビリティ経由で公開しておらず，Arc のプロセスだけに送ったマウスイベントも無視されるため，幅を変える唯一の手段は実際のポインタを動かすドラッグの模擬になります．ポインタを奪う動作は避けたいので，幅は手動で区切りをドラッグして調整してください．

### 解除

登録内容は絶対パスを含むため，リポジトリを移動した場合は `native-host/install.sh` を再実行してください．解除するには次を実行します．

```
launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
rm "$HOME/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json"
rm "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.claude.arc.json"  # WITH_CHROME=1 で登録した場合のみ
rm -r "$HOME/Library/Application Support/claude-arc"
rm -f ~/Library/Logs/claude-arc-host.log ~/Library/Logs/claude-arc-splitview.err.log ~/Library/Logs/claude-arc-axdump.txt
```

最後に，システム設定 → プライバシーとセキュリティ → アクセシビリティ の一覧から `/usr/bin/osascript` を削除します（同 → オートメーション にある osascript の System Events の許可も，不要なら外します）．

## 利用前に確認すること

- 生成される拡張機能の権限を確認してください
- 機密情報を扱うページで利用しないでください
- 重要な作業環境や本番環境では利用しないでください
- Claude，Arc，Chrome の仕様変更により動作しなくなる可能性があります

## 免責事項

本拡張機能の利用は自己責任でお願いします．
本拡張機能の利用によって生じたいかなる損害，不具合，データの消失，情報漏えい，アカウント停止，その他の問題についても，作者は一切の責任を負いません．

## ライセンス

現時点ではライセンスを明示していません．
本リポジトリに含まれるのは `scripts/`，`native-host/`，`build.sh` と文書だけであり，公式拡張機能の複製は含まれていません．`build.sh` が生成する `build/` の権利は Anthropic および各コンポーネントの元の著作権者に帰属するため，生成物を再配布しないでください．
明示的な許可なく，本リポジトリの内容を再配布・商用利用しないでください．

---

## English

An unofficial, personal-use set of patches that makes the official "Claude in Chrome" extension run in Arc Browser, which lacks the Side Panel API. You patch your own copy of the official extension locally to produce the Arc build; this repository contains nothing distributed by Anthropic. The generated Claude panel opens as a regular tab or, optionally, in an Arc Split View pane.

> [!WARNING]
> This repository is unofficial and experimental. It is not affiliated with Anthropic, Claude, The Browser Company, or Arc.

![The Claude panel opened in an Arc Split View pane, working on the GitHub page in the neighbouring tab](docs/demo.png)

Left: the tab being worked on. Right: the Claude panel opened in a Split View pane. Instructions given in the panel read and operate the page in the neighbouring tab. The tab being operated shows an orange border and a "Stop Claude" button.

## Overview

This extension is intended to open Claude as an Arc extension and help with browser-based work.

Main use cases include:

- Opening the Claude panel as a regular tab or in an Arc Split View pane
- Assisting browser operations while chatting with Claude
- Using scheduled tasks and notifications
- Using file operations and downloads when needed

## How It Works and What Is Changed

`build.sh` copies the official "Claude in Chrome" extension (extension ID `fcoeoabgfenejglbffodgkkbkcdhcgfn`) installed in Chrome (or Arc) into `build/` and applies the following changes with the three scripts in `scripts/`. Verified against version 1.0.93 of the official extension.

- Because Arc lacks the Side Panel API, the panel page is opened as a regular tab instead
- Display strings such as `Claude in Chrome` are replaced with `Claude in Arc`
- `declarativeNetRequest` rules add CORS headers to `claude.ai/images/*` responses and remove the `Content-Security-Policy` header from iframe (`sub_frame`) responses of `claude.ai` so that claude.ai can be framed inside the panel. Top-level claude.ai tabs are not affected
- Arc never settles the promises of the tab-group APIs (`chrome.tabs.group` and friends), so tab groups are emulated inside the service worker; the panel's initialisation depends on a tab group, and without this every browser action times out
- Pages that were open before the extension loaded get the page-reading helper script injected on demand (the official build asks you to reload such pages)
- Optionally, a bundled native host opens the panel as an Arc Split View pane (see below)

The scripts: `apply_arc_patches.py` applies the manifest changes, the regular-tab fallback, the tab-group emulation, the on-demand script injection, and the network rules. `patch_sender_checks.py` makes the service worker accept messages from the panel even though Arc hosts it in a regular tab instead of a side panel. `rebrand_chrome_strings.py` replaces user-facing "Chrome" wording with "Arc". All of them rewrite files under `build/` only and never touch the official installation.

The generated `build/` is a patched copy of the official extension you obtained yourself. It remains the property of Anthropic and of the respective upstream copyright holders of its components (such as gif.js and the KaTeX fonts). The author of this repository holds rights only over `scripts/`, `native-host/`, `build.sh`, and the Arc-specific modifications; `build/` is excluded from version control by `.gitignore`.

## Important Notes

This extension is intended for developers and experimental use. It is not a general-purpose extension distributed through a public extension store.

The generated `manifest.json` requests powerful permissions, including the following (see `permissions` in `manifest.json` for the full list):

- `host_permissions: ["<all_urls>"]`
- `debugger`
- `tabs`
- `scripting`
- `downloads`
- `nativeMessaging`
- `declarativeNetRequest`
- `webNavigation`
- `notifications`
- `identity`
- `tabGroups`

These permissions may relate to accessing information from pages you browse, controlling browser behavior, observing page navigation, applying network rules, showing notifications, downloading files, OAuth sign-in, and communicating with external processes.
Use this extension only in an environment you control and only after understanding what these permissions allow.

## Installation

### Requirements

- macOS and Arc
- The official "Claude in Chrome" extension installed from the Chrome Web Store in Chrome (or Arc) on the same Mac; `build.sh` copies it from there
- Python 3 (used by `build.sh` and by the Split View native host). Any of `/usr/bin/python3` (Xcode Command Line Tools), the python.org build, or the Homebrew build is fine. `/usr/bin/python3` stops working after an Xcode update until the license is accepted again (`sudo xcodebuild -license accept`); another installed Python is used in that case
- A claude.ai account; the panel requires a paid plan

### Steps

1. Clone this repository locally
2. Run `bash build.sh`. It finds the newest installed official extension and generates the Arc build in `build/`. If it is installed somewhere else, pass the directory: `bash build.sh <official-extension-dir>`
3. Open Arc and enter `arc://extensions` in the address bar
4. Enable "Developer mode" in the top-right corner
5. Click "Load unpacked" and select `build/`
6. Click the Claude icon in the toolbar (Cmd+E also works). The panel opens as a regular tab and asks you to sign in to claude.ai

Because the generated `manifest.json` carries the official public key, the extension ID is the same as the official one regardless of the directory it is loaded from. To open the panel next to the current tab, add the setup in the next section.

When the official extension updates in Chrome, run `bash build.sh` again and reload the extension in `arc://extensions`. The first two scripts locate minified identifiers by exact string match and stop with an `AssertionError` when the upstream code has changed; update the search patterns in the scripts for the new build in that case. The third only skips phrases it cannot find, so check the replacement counts it prints and add any remaining "Chrome" wording to its phrase list.

To uninstall, click "Remove" in `arc://extensions` first and then delete `build/`; deleting the directory first leaves a broken entry in the list. If you registered the Split View integration, also run the removal steps in the next section.

## Opening in Split View (optional)

Because Arc lacks the Side Panel API, the panel opens as a regular tab by default. Registering the bundled native messaging host and launchd agent makes the toolbar icon and Cmd+E open the panel as a Split View pane next to the current tab.

1. In System Settings → Privacy & Security → Accessibility, press "+", use Cmd+Shift+G to enter `/usr/bin/osascript`, add it, and switch it on. This grant applies to `/usr/bin/osascript` itself, not to this project: afterwards any process running as your user can drive the GUI under the same grant by launching `osascript` (through launchd, for example). Revoke it with the removal steps below when you stop using the Split View integration
2. Run `native-host/install.sh` from Terminal. It registers the native host (`native-host/claude-arc-host`, which launches `claude-arc-host.py`) with Arc (`~/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json`), loads the launchd user agent `com.claude.arc.splitview`, and then probes Accessibility and prints the result. On first run macOS asks whether osascript may control System Events; click Allow. To also register the host with Google Chrome for developer testing, run `WITH_CHROME=1 native-host/install.sh`
3. Reload the extension in `arc://extensions` and click the Claude icon

How it works: the host writes only the tab id into `~/Library/Application Support/claude-arc/queue/`; launchd notices it and runs `native-host/split-view.applescript` with `/usr/bin/osascript`. The AppleScript rebuilds the panel URL from the fixed extension id (queue content is never typed as-is), uses System Events to find and click a menu item such as "Add Split View" or "Add Vertical Split View" (falling back to Arc's default shortcut Control+Shift+= when none is found), waits until the new pane's command bar has focus, then pastes the URL from the clipboard and presses Return. The clipboard contents are saved before the paste and restored afterwards, but they are replaced momentarily in between. If no command bar takes focus it types nothing, reports an error, and the extension falls back to a regular tab.

Running AppleScript directly from a child process of Arc does not work reliably, because macOS attributes the Accessibility check to Arc as the responsible process. An `osascript` spawned by launchd is its own responsible process, so the grant for `osascript` applies. Activity is logged to `~/Library/Logs/claude-arc-host.log` (written by both the host and the AppleScript); the stderr of the launchd-spawned `osascript` goes to `~/Library/Logs/claude-arc-splitview.err.log`.

If Split View stops opening (for example after an Arc update), run the following in Terminal. It writes the accessibility tree of Arc's front window (web content excluded) to `~/Library/Logs/claude-arc-axdump.txt`, which shows whether the menu item names or the split structure have changed. It contains window and tab titles, so delete it when no longer needed.

```
n="$(( $(date +%s) * 1000 ))-$$"; d="$HOME/Library/Application Support/claude-arc"; printf dump > "$d/$n.tmp" && mv "$d/$n.tmp" "$d/queue/$n"
```

### About the pane width

The pane width is not adjusted automatically. Arc does not expose the divider position through Accessibility, and mouse events posted only to Arc's process are ignored, so the only way to change the width would be a simulated drag that moves the real pointer. Taking over the pointer is undesirable, so adjust the width by dragging the divider yourself.

### Removal

The registration contains absolute paths, so re-run `native-host/install.sh` after moving the repository. To remove it:

```
launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
rm "$HOME/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json"
rm "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.claude.arc.json"  # only if registered with WITH_CHROME=1
rm -r "$HOME/Library/Application Support/claude-arc"
rm -f ~/Library/Logs/claude-arc-host.log ~/Library/Logs/claude-arc-splitview.err.log ~/Library/Logs/claude-arc-axdump.txt
```

Finally, remove `/usr/bin/osascript` from the list in System Settings → Privacy & Security → Accessibility (and, if no longer needed, revoke osascript's System Events entry under Privacy & Security → Automation as well).

## Before Use

- Review the permissions of the generated extension
- Do not use it on pages that handle sensitive information
- Do not use it in critical work environments or production environments
- It may stop working due to changes in Claude, Arc, or Chrome

## Disclaimer

Use this extension at your own risk.
The author assumes no responsibility for any damage, malfunction, data loss, information leakage, account suspension, or any other issues caused by using this extension.

## License

No license is currently specified.
This repository contains only `scripts/`, `native-host/`, `build.sh`, and documentation; it contains no copy of the official extension. The `build/` directory that `build.sh` generates remains the property of Anthropic and the respective upstream copyright holders, so do not redistribute it.
Do not redistribute or use the contents of this repository commercially without explicit permission.
