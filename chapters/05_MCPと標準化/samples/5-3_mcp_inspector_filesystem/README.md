# 5-3 ハンズオン：MCP Inspector で既存サーバーをのぞく

第5章 5-3 のハンズオン補足。本文では「公開済みの MCP サーバーに確認用ツールでつなぎ、`tools/list`／`tools/call` を目で見る」流れだけを追います。ここでは、実際に動かすための環境構築・起動コマンド・AIアプリ（ホスト）への登録手順をまとめます。**API キーは不要**です。

> 注意：このハンズオンは Node.js とネットワーク取得（`npx`）を伴うため、本書の検証環境では実コマンド起動までは行っていません。コマンド・パッケージ名・既定ポート・設定例は MCP 公式ドキュメント準拠です。最新の手順は公式（modelcontextprotocol.io）で確認してください。

## 使うもの

| 名前 | 役割 | 出典 |
| :-- | :-- | :-- |
| MCP Inspector | MCP サーバーの公開要素（ツール／リソース／プロンプト）を一覧・実行できる公式の確認ツール | modelcontextprotocol.io/docs/tools/inspector |
| `@modelcontextprotocol/server-filesystem` | 指定フォルダ内のファイルを読み書きするツールを公開する公式の参照サーバー | modelcontextprotocol.io/docs/develop/connect-local-servers |

どちらも `npx` 実行時に取得されるため、事前インストールは基本不要です。

## 事前準備：Node.js

`npx` コマンドを使うため Node.js が必要です。未導入なら [Node.js 公式サイト](https://nodejs.org/) から **LTS 版**を入れてください。導入確認：

```bash
node -v   # v20 以降の表示が出ればOK
npx -v
```

## 起動

末尾のパスが「サーバーにアクセスを許すフォルダ」です。**練習用の空フォルダ**を指定します（業務データの入った場所は渡さない）。

```bash
# 練習用フォルダを用意（中にテキストを1〜2個置いておくと確認しやすい）
mkdir -p ~/mcp-test
echo "hello mcp" > ~/mcp-test/sample.txt

# Inspector を起動し、その中で filesystem サーバーを立ち上げて自動接続
npx @modelcontextprotocol/inspector npx -y @modelcontextprotocol/server-filesystem ~/mcp-test
```

少し待つと、ブラウザで Inspector の画面（既定 `http://localhost:6274`）が開きます。サーバーに接続すると、`tools/list` の結果としてツール一覧（ファイル読み取り・一覧・検索・書き込み・編集・移動など）が表示されます。「ファイル読み取り」ツールを選び、引数に `~/mcp-test/sample.txt` を入れて実行すると（`tools/call`）、中身が結果として返ります。

### うまくいかないとき
- ポート競合：`6274` が使用中なら Inspector が別ポートを案内します。ターミナルの表示 URL を開いてください。
- パスエラー：`tools/call` のパスは、起動時に許可したフォルダ（ここでは `~/mcp-test`）の中だけが対象です。

## 発展：Claude Desktop（実際のホスト）から使う

同じ filesystem サーバーは、確認用の Inspector ではなく実際の AI アプリ（ホスト）からも使えます。Claude Desktop の場合、設定ファイル `claude_desktop_config.json` の `mcpServers` に登録します。

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/絶対パス/mcp-test"]
    }
  }
}
```

登録後に Claude Desktop を再起動すると、チャットから「そのフォルダを整理して」のように依頼でき、ファイルを書き換える操作の前にはユーザーの**承認**を求める作りで動きます（第4章「取り消せない操作の前に人間が確認する」がホスト側に組み込まれている例）。設定ファイルの場所など最新手順は MCP 公式の "Connect to local MCP servers" を参照してください。

## 安全上の注意（重要）

filesystem サーバーは、許可フォルダ内を**あなたのユーザー権限で**読み書きします。つまり、あなたが手でできるファイル操作は何でも実行され得ます。許可は練習用の空フォルダだけにとどめ、ホームフォルダ全体や業務データの場所を丸ごと渡さないこと。「MCP サーバーに何を任せると、どこまでの権限を渡すことになるか」を体感する題材でもあります（権限設計の詳細は第14章）。
