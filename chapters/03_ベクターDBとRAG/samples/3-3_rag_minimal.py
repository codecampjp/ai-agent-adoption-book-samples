"""3-3 手を動かす：Chromaで最小のRAGを組む（取り込み→検索）。

本書 3-3 節の掲載コードを、そのまま実行できる形にまとめたもの。
RAG の2段階のうち「取り込み（インデックス作成）」と「検索」を動かす。
「生成」は 3-4_rag_with_generation.py を参照。

実行:
    python 3-3_rag_minimal.py

初回実行時は埋め込みモデル（paraphrase-multilingual-MiniLM-L12-v2、約 0.5GB）が
ダウンロードされるため、ネットワーク接続と数分の待ち時間が必要。
"""

import chromadb
from chromadb.utils import embedding_functions


def build_collection() -> "chromadb.api.models.Collection.Collection":
    # 日本語に対応した多言語の埋め込みモデルを指定する。
    # （指定しないと既定の英語中心モデルになり、日本語の意味検索が外す）
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    # メモリ上にChromaを用意し、コレクション（文書の入れ物）を作る
    client = chromadb.Client()
    collection = client.create_collection(name="company_docs", embedding_function=ef)

    # 社内規程を模した文書を登録する。Chromaが自動で埋め込みベクトルを作る
    collection.add(
        documents=[
            "年次有給休暇は入社半年後に10日付与され、勤怠システムから前日までに申請します。",
            "出張旅費や立替経費は、月末締めで翌月10日までに領収書を添付して経費システムへ申請します。",
            "社外秘データは指定の暗号化ストレージに保管し、パスワードは90日ごとに変更してください。",
        ],
        ids=["doc1", "doc2", "doc3"],
        # 文書と同じ順序で出典・版を付ける（すべて架空の教材データ）。
        metadatas=[
            {"source_id": "sample-leave-policy", "version": "v1", "section": "休暇"},
            {"source_id": "sample-expense-policy", "version": "v1", "section": "経費"},
            {"source_id": "sample-security-policy", "version": "v1", "section": "情報管理"},
        ],
    )
    return collection


def main() -> None:
    collection = build_collection()

    queries = [
        "休みを取りたいときの手続きは？",
        "立て替えたお金はどう請求する？",
        "機密情報の保管ルールは？",
    ]
    for q in queries:
        result = collection.query(query_texts=[q], n_results=1)
        print(f"Q: {q}")
        print(f" -> {result['documents'][0][0]}")
        print(f" 出典: {result['metadatas'][0][0]}")


if __name__ == "__main__":
    main()
