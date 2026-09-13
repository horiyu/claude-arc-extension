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

公式拡張機能が更新された場合は，Chrome にインストールされた新しいビルドを作業ディレクトリへ複製し，`scripts/apply_arc_patches.py <作業ディレクトリ>` と `scripts/patch_sender_checks.py <作業ディレクトリ>` をこの順に実行してから，その内容で本リポジトリを置き換えます．後者は，サイドパネルを通常タブで代替している Arc 版でも service worker がパネルからのメッセージを受け付けるようにする修正です．

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
6. ツールバーの Claude アイコンをクリックする
7. 必要に応じて Split View などでサイドパネルとして利用する

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

When the official extension is updated, copy the new build installed in Chrome into a working directory, run `scripts/apply_arc_patches.py <working-directory>` followed by `scripts/patch_sender_checks.py <working-directory>`, and replace the contents of this repository with the result. The second script makes the service worker accept messages from the panel even though Arc hosts it in a regular tab instead of a side panel.

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
6. Click the Claude icon in the toolbar
7. Use it as a side panel with Split View if desired

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
