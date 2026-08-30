"""12-7 営業商談準備エージェント ── Synthesizer を含む全体パイプラインの実行エントリー。

本文 12-7（Synthesizerが調査結果を束ねる）から参照される実行ファイル。
パイプラインの実体は、同じフォルダの 12-2_agent_pipeline.py
（本文 12-2〜12-7 を1本につないだ完全版）にあり、このスクリプトは
それをそのまま実行する。

12-7 で説明している Synthesizer と HITL②（最終レビュー）は、
12-2_agent_pipeline.py の「--- Synthesizer ＋ HITL②（12-7）---」の
セクション（synthesizer 関数と review_draft ノード）に対応する。
コードを読むときはそちらを開くとよい。

実行（12-2_agent_pipeline.py と同じ4経路の自動デモが動く）:
    python 12-7_agent_pipeline.py

APIキー・ネットワークは不要（検索は擬似データ、計画・統合は擬似モデル）。
"""

import runpy
from pathlib import Path

TARGET = Path(__file__).with_name("12-2_agent_pipeline.py")


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
