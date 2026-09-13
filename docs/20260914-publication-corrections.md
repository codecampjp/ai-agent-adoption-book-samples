# 出版前修正案と検証記録（2026-09-14）

対象：最終ゲラ 2026-08-31版、サンプルの基点 b6e7645。
本文のページ番号は紙面に印字された番号です。PDF原本は変更していません。以下は編集側への差し替え案です。

## 本文の差し替え・追記案

### p.100：最終回答を生成するMessages API呼び出し

`client.messages.create` に必須の `max_tokens` を補います。掲載コードの他の引数は維持し、次の1行を追加してください。

```python
max_tokens=1024,
```

サンプル `4-2_function_calling_minimal.py` にはすでにこの引数が入っています。

### p.116：MCP Inspectorの起動

前提に「Node.js 22.19.0以上」を追加し、再現対象の版を明示します。

```bash
npx -y @modelcontextprotocol/inspector@2.6.0 npx -y @modelcontextprotocol/server-filesystem@2026.8.31 ~/mcp-test
```

起動時に表示されたURLを開き、サーバーの接続スイッチをオンにします。ConnectedになったらToolsを開き、Read Text File（read_text_file）を選択します。pathに練習用ファイルの絶対パスを入れ、Execute Toolで実行してください。

[ツール一覧の実画面](../chapters/05_MCPと標準化/samples/5-3_mcp_inspector_filesystem/images/inspector-tools.png)と[読み取り成功の実画面](../chapters/05_MCPと標準化/samples/5-3_mcp_inspector_filesystem/images/inspector-read-result.png)を追加しました。旧版の画面が紙面に残る場合は、この版の画面との差を確認してください。

### p.175・p.389：uvでのStudio導入

「Python 3.12の仮想環境で、章のrequirementsを導入した後に実行」と明記し、uvを使う手順では次のコマンドに揃えます。

```bash
uv pip install --python .venv -U "langgraph-cli[inmem]"
source .venv/bin/activate
langgraph dev
```

標準venvを使う場合は `python -m pip install -U "langgraph-cli[inmem]"` でも構いません。Windowsの有効化は `.venv\Scripts\activate` です。

追記案：「スクリプト単体のMermaid出力にはAPIキーは不要です。StudioのWeb UI利用ではLangSmithへのサインインと接続設定を行います。LangSmithのAPIキーはLLM用のAPIキーとは別です。」

### p.264〜267：検索結果の共通形式・未確認情報

本文の方針を維持してサンプルを修正しました。`status`、`content`、`source_id`、`updated_at`、`source_url`を保持し、`ok`以外は未確認事項に残します。ダミーデータで実在する出典と誤解されないよう、出典IDを`dummy:`とし、更新日時とURLは`null`です。

### p.285〜287：Worker失敗の扱い

本文の方針を維持して、追加教材の対話スクリプトを修正しました。APIエラー・未完了応答・JSON形式違反では観点と失敗理由、再実行の要否を記録し、他の観点の結果を保持します。「指摘なし」は正常に完了した空配列と区別します。

### p.74：メタデータ付き取り込み

`3-3_rag_minimal.py`に出典ID・版・節を付ける取り込み例と、検索結果のメタデータ出力を追加しました。本文の紹介文は維持できます。

### p.134から参照するDify手順

存在しない画像3点のリンクを外し、文章の手順と未収録の表示を残しました。既存7点の画像は従来の操作例として維持しています。撮影用の編集メモ・PLACEHOLDER表記を整理し、モデルと埋め込み設定、利用枠、実行順序の揺れを説明しました。

## 検証結果

- 通常サンプル43本をAPIキーなしで実行し、すべて正常終了。
- 第12・13章に回帰テスト10件を追加し、全件成功。未知企業、取得失敗、権限不足、不正なツール応答、JSON不正、応答中断、一部Workerの失敗、根拠不一致、空行を含む文書の行番号を確認。
- 対話型・補助スクリプト10本もAPIキーなしで実行し、すべて正常終了。
- 新規のuv仮想環境（Python 3.12.12）で第7章のrequirementsと `langgraph-cli[inmem]` を導入し、Mermaid出力を確認。APIキーを設定しないローカル開発サーバーでも起動とhealth応答を確認し、`react_agent`への擬似在庫照会が「B-200が15個」で完了しました。これはログイン後のStudio GUIの検証とは区別します。導入された主な版は langgraph 1.2.11 / langchain-core 1.6.3 / langgraph-cli 0.4.31 / langgraph-api 0.14.0。
- Markdownのローカルリンク先に欠落なし。
- 第3章の3質問で期待する文書と対応するメタデータが返ることを確認。
- Inspector 2.6.0 / filesystem server 2026.8.31 / Node.js 22.21.1でGUI接続、tools/list、read_text_fileによる「hello mcp」の取得を確認。実画面2枚を収録（1280×720、セッショントークン・アカウント情報なし）。

## Draftを外す前の残件

- Dify 01〜03の再撮影。既存のローカルDify 1.13.3は今回の撮影ブラウザでは読み込み中で止まり、設定済みプロバイダー・アップロード済み文書・処理完了の状態を確認できませんでした。架空の設定画面や処理完了画像は作っていません。
- LangSmith Studioのログイン後GUI・実モデルAPIでの最終動作確認。今回、API料金の発生する呼び出しは行っていません。
- Windows/Linux、およびPython 3.10/3.11での再検証。今回の実行環境はmacOS / Python 3.12です。
- 読者向け公開設定：2026-09-14のGitHub API照会で本リポジトリはprivateでした。公開日までに、書籍掲載URLから匿名の読者が閲覧できることを確認してください。このPRでは公開設定を変更していません。
- 本文差し替え案の編集側反映と、再出力したPDFの確認。

## 参照した公式情報

- [MCP Inspector（Node.js要件・起動）](https://modelcontextprotocol.io/docs/tools/inspector)
- [LangSmithのローカル開発手順](https://docs.langchain.com/langsmith/local-dev-testing)

パッケージ版とGUIは今回の実環境でも確認しています。残件を検証済みとは扱わず、Draftのレビュー対象として残します。
