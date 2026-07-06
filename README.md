# ai-agent-samples-verify

書籍『AIエージェント導入を任されたら読む本』（`202609_nikkei-ai-agent`）の
各章サンプルコードを **動作確認するための独立リポジトリ**。

本体 vault（`MyDailyTasksFrom20260130`）の外に置き、実行時に生成される
`.venv/` や埋め込みモデルのキャッシュ、Chroma DB などで vault を汚さないようにする。

## 由来

サンプルの元は以下（こちらが正）。動作確認で原稿を直す必要が出たら、元に反映すること。

```
MyDailyTasksFrom20260130/textbooks/202609_nikkei-ai-agent/chapters/<章>/samples/
```

このリポジトリへは `.venv/` `__pycache__/` `.chroma/` を除いてコピーしている。

## 構成

```
chapters/
  03_ベクターDBとRAG/samples/
  04_ツール連携とFunction Calling/samples/
  ...
  16_知識ベース運用とETL/samples/
```

各章 `samples/` に `README.md`（実行手順）・`requirements.txt`・サンプル `.py` が入っている。

## 動作確認の方針

- **オフライン（APIキー不要）で完走できるドライラン**をまず全章確認する。
- **APIキーが要る本番モード**（Anthropic / deepeval / promptfoo 等）は、
  キー設定後にあらためて実行する。

各章の詳しい実行手順・期待出力は、その章の `samples/README.md` を参照。

## セットアップの目安（uv 推奨）

章ごとに独立の venv を作る（依存が章で異なるため）。

```bash
cd "chapters/07_LangGraphの最小セット/samples"
uv venv --python 3.12
uv pip install --python .venv -r requirements.txt
.venv/bin/python 7-2_minimal_graph.py
```

標準ライブラリのみで動く章（13/14/15/16、および 04/06 のドライラン）は
依存インストール不要（Python 3.10+ の venv があればよい）。
