# Claude in Arc

[日本語](#日本語) | [English](#english)

## 日本語

Arc ブラウザ上で Claude をサイドパネルとして扱いやすくするための，個人利用向け Chrome 拡張機能です．

> [!WARNING]
> このリポジトリは非公式・実験的なものです．Anthropic，Claude，The Browser Company，Arc とは関係ありません．

## 概要

この拡張機能は，Arc の拡張機能として Claude を開き，ブラウザ内での作業を補助することを目的としています．

主な用途は次の通りです．

- Claude を Arc のサイドパネルとして開く
- Claude と会話しながらブラウザ操作を補助する
- タスクのスケジュール実行や通知を利用する
- 必要に応じてファイル操作やダウンロード機能を利用する

## ベースとなる公式拡張機能と更新手順

本リポジトリは，公式の「Claude in Chrome」拡張機能（バージョン 1.0.93）のビルド済みバンドルに，Arc 向けの変更を加えたものです．主な変更点は次の通りです．

- Arc に Side Panel API が無いため，サイドパネルの代わりに拡張機能ページを通常タブとして開く
- `Claude in Chrome` 等の表示文言を `Claude in Arc` に置換する
- `claude.ai` の画像に対する CORS ヘッダー付与と，フレーム表示のための CSP ヘッダー除去を `declarativeNetRequest` で行う
- 任意で，同梱のネイティブホストにより Arc の Split View としてパネルを開く（後述）

公式拡張機能が更新された場合は，Chrome にインストールされた新しいビルドを作業ディレクトリへ複製し，`scripts/apply_arc_patches.py <作業ディレクトリ>`，`scripts/patch_sender_checks.py <作業ディレクトリ>`，`scripts/rebrand_chrome_strings.py <作業ディレクトリ>` をこの順に実行してから，その内容で本リポジトリを置き換えます．2 つ目は，サイドパネルを通常タブで代替している Arc 版でも service worker がパネルからのメッセージを受け付けるようにする修正です．3 つ目は，画面に表示される「Chrome」の表記を「Arc」に置き換えます．

## 注意事項

この拡張機能は開発者向け・検証用途のものです．公開ストアで配布される一般利用向け拡張機能ではありません．

また，`manifest.json` では以下のような強い権限を要求します．

- `host_permissions: ["<all_urls>"]`
- `debugger`
- `tabs`
- `scripting`
- `downloads`
- `nativeMessaging`
- `declarativeNetRequest`

これらの権限は，閲覧中のページ情報へのアクセス，ブラウザ操作，ネットワークルールの適用，ダウンロード，外部プロセス連携などに関係します．
内容を理解したうえで，自分の管理下にある環境でのみ利用してください．

## インストール

1. このリポジトリをローカルに clone する
2. Arc を開き，アドレスバーに `arc://extensions` と入力する
3. 右上の「デベロッパーモード」を有効化する
4. 「パッケージ化されていない拡張機能を読み込む」をクリックする
5. このリポジトリのディレクトリを選択する
6. ツールバーの Claude アイコンをクリックする（Cmd+E でも開く）．パネルは通常タブとして開き，claude.ai へのサインインを求められる

ビルド工程はありません．clone したディレクトリをそのまま読み込めば動作します．`manifest.json` に公開鍵が含まれているため，拡張機能 ID はどのディレクトリから読み込んでも同じです．隣のペインに開きたい場合は次節の設定を追加してください．

### 前提条件

- Arc（macOS 版で確認）．拡張機能本体はこれだけで動きます
- claude.ai のアカウント．パネルは有料プランを要求します
- Split View 連携を使う場合は macOS と Python 3（`python3` コマンド．Xcode Command Line Tools か python.org 版）

## Split View で開く（任意）

Arc には Side Panel API が無いため，既定ではパネルを通常タブとして開きます．同梱のネイティブメッセージングホストと launchd エージェントを登録すると，ツールバーのアイコンや Cmd+E で，現在のタブの隣に Split View としてパネルを開きます．

1. システム設定 → プライバシーとセキュリティ → アクセシビリティ で「＋」を押し，Cmd+Shift+G で `/usr/bin/osascript` を指定して追加し，オンにする．
2. ターミナルで `native-host/install.sh` を実行する．ネイティブホスト（`native-host/claude-arc-host.py`）が Arc に登録され，launchd ユーザーエージェント `com.claude.arc.splitview` が読み込まれる．続けてアクセシビリティの検査が走り，結果が表示される．初回は「osascript が System Events を制御することを許可しますか」という確認が出るので許可する．
3. `arc://extensions` で拡張機能を再読み込みし，Claude アイコンをクリックする．

仕組みは次の通りです．ホストはタブ ID だけを `~/Library/Application Support/claude-arc/queue/` に書き，launchd がそれを検知して `/usr/bin/osascript` で `native-host/split-view.applescript` を実行します．AppleScript はパネルの URL を固定の拡張機能 ID から組み立て直し（キューの内容をそのまま入力することはしない），System Events で Arc のメニュー項目「Add Split View」などを探してクリックします．新しいペインの入力欄にフォーカスが移ったことを確認してから，URL をクリップボード経由で貼り付けて Return を送ります．入力欄が見つからなければ何も入力せずエラーを返し，拡張機能は通常タブで開きます．

Arc の子プロセスから直接 AppleScript を実行すると，macOS はアクセシビリティ権限を Arc に帰属させて判定するため，許可が安定して効きません．launchd から起動した `osascript` は自分自身が責任元になるので，`osascript` への許可がそのまま適用されます．動作の記録は `~/Library/Logs/claude-arc-host.log` に残ります．

登録内容は絶対パスを含むため，リポジトリを移動した場合は `native-host/install.sh` を再実行してください．解除するには次を実行します．

```
launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
rm "$HOME/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json"
rm "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.claude.arc.json"
rm -r "$HOME/Library/Application Support/claude-arc"
```

## 利用前に確認すること

- 拡張機能の権限を確認してください
- 機密情報を扱うページで利用しないでください
- 重要な作業環境や本番環境では利用しないでください
- Claude，Arc，Chrome の仕様変更により動作しなくなる可能性があります

## 免責事項

本拡張機能の利用は自己責任でお願いします．
本拡張機能の利用によって生じたいかなる損害，不具合，データの消失，情報漏えい，アカウント停止，その他の問題についても，作者は一切の責任を負いません．

## ライセンス

現時点ではライセンスを明示していません．
明示的な許可なく，本リポジトリの内容を再配布・商用利用しないでください．

---

## English

This is a Chrome extension for personal use that makes Claude easier to use as a side panel in Arc Browser.

> [!WARNING]
> This repository is unofficial and experimental. It is not affiliated with Anthropic, Claude, The Browser Company, or Arc.

## Overview

This extension is intended to open Claude as an Arc extension and help with browser-based work.

Main use cases include:

- Opening Claude as an Arc side panel
- Assisting browser operations while chatting with Claude
- Using scheduled tasks and notifications
- Using file operations and downloads when needed

## Upstream Extension and Update Procedure

This repository is the built bundle of the official "Claude in Chrome" extension (version 1.0.93) with Arc-specific modifications applied:

- Because Arc lacks the Side Panel API, the panel page is opened as a regular tab instead
- Display strings such as `Claude in Chrome` are replaced with `Claude in Arc`
- `declarativeNetRequest` rules add CORS headers to `claude.ai` images and remove the CSP header so that the page can be framed
- Optionally, a bundled native host opens the panel as an Arc Split View pane (see below)

When the official extension is updated, copy the new build installed in Chrome into a working directory, run `scripts/apply_arc_patches.py <working-directory>`, `scripts/patch_sender_checks.py <working-directory>`, and `scripts/rebrand_chrome_strings.py <working-directory>` in that order, and replace the contents of this repository with the result. The second script makes the service worker accept messages from the panel even though Arc hosts it in a regular tab instead of a side panel. The third replaces user-facing "Chrome" wording with "Arc".

## Important Notes

This extension is intended for developers and experimental use. It is not a general-purpose extension distributed through a public extension store.

The `manifest.json` requests powerful permissions, including:

- `host_permissions: ["<all_urls>"]`
- `debugger`
- `tabs`
- `scripting`
- `downloads`
- `nativeMessaging`
- `declarativeNetRequest`

These permissions may relate to accessing information from pages you browse, controlling browser behavior, applying network rules, downloading files, and communicating with external processes.
Use this extension only in an environment you control and only after understanding what these permissions allow.

## Installation

1. Clone this repository locally
2. Open Arc and enter `arc://extensions` in the address bar
3. Enable "Developer mode" in the top-right corner
4. Click "Load unpacked"
5. Select this repository directory
6. Click the Claude icon in the toolbar (Cmd+E also works). The panel opens as a regular tab and asks you to sign in to claude.ai

There is no build step: the cloned directory can be loaded as is. Because `manifest.json` contains the public key, the extension ID is the same regardless of the directory it is loaded from. To open the panel next to the current tab, add the setup in the next section.

### Requirements

- Arc (tested on macOS). The extension itself needs nothing else
- A claude.ai account; the panel requires a paid plan
- For the Split View integration: macOS and Python 3 (the `python3` command, from Xcode Command Line Tools or python.org)

## Opening in Split View (optional)

Because Arc lacks the Side Panel API, the panel opens as a regular tab by default. Registering the bundled native messaging host and launchd agent makes the toolbar icon and Cmd+E open the panel as a Split View pane next to the current tab.

1. In System Settings → Privacy & Security → Accessibility, press "+", use Cmd+Shift+G to enter `/usr/bin/osascript`, add it, and switch it on.
2. Run `native-host/install.sh` from Terminal. It registers the native host (`native-host/claude-arc-host.py`) with Arc, loads the launchd user agent `com.claude.arc.splitview`, and then probes Accessibility and prints the result. On first run macOS asks whether osascript may control System Events; click Allow.
3. Reload the extension in `arc://extensions` and click the Claude icon.

How it works: the host writes only the tab id into `~/Library/Application Support/claude-arc/queue/`; launchd notices it and runs `native-host/split-view.applescript` with `/usr/bin/osascript`. The AppleScript rebuilds the panel URL from the fixed extension id (queue content is never typed as-is), uses System Events to find and click Arc's "Add Split View" menu item, waits until the new pane's command bar has focus, then pastes the URL from the clipboard and presses Return. If no command bar takes focus it types nothing, reports an error, and the extension falls back to a regular tab.

Running AppleScript directly from a child process of Arc does not work reliably, because macOS attributes the Accessibility check to Arc as the responsible process. An `osascript` spawned by launchd is its own responsible process, so the grant for `osascript` applies. Activity is logged to `~/Library/Logs/claude-arc-host.log`.

The registration contains absolute paths, so re-run `native-host/install.sh` after moving the repository. To remove it:

```
launchctl bootout "gui/$(id -u)/com.claude.arc.splitview"
rm ~/Library/LaunchAgents/com.claude.arc.splitview.plist
rm "$HOME/Library/Application Support/Arc/NativeMessagingHosts/com.claude.arc.json"
rm "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.claude.arc.json"
rm -r "$HOME/Library/Application Support/claude-arc"
```

## Before Use

- Review the extension permissions
- Do not use it on pages that handle sensitive information
- Do not use it in critical work environments or production environments
- It may stop working due to changes in Claude, Arc, or Chrome

## Disclaimer

Use this extension at your own risk.
The author assumes no responsibility for any damage, malfunction, data loss, information leakage, account suspension, or any other issues caused by using this extension.

## License

No license is currently specified.
Do not redistribute or use the contents of this repository commercially without explicit permission.
