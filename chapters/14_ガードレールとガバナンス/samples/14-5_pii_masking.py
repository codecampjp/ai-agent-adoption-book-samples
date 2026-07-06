"""14-5 データ漏洩対策 ── PII検出とマスキング（オフライン）

決まった形式（メール・電話・カード番号）を正規表現で検出し、種類ラベルへ置換する。
本番では Microsoft Presidio（Analyzer＝NER併用で氏名等も検出／Anonymizer＝置換・伏字・
マスク・ハッシュ・暗号化）に置き換える。正規表現だけでは氏名等を取りこぼす点に注意。
"""

from __future__ import annotations

from _common import mask_pii


def main():
    samples = [
        "田中太郎さんの連絡先は tanaka@example.com、電話 090-1234-5678 です。",
        "決済カード 4111 1111 1111 1111 を登録しました。",
        "山田さんに折り返し連絡してください。",   # 氏名のみ＝正規表現では取りこぼす
    ]
    print("=== PII 検出とマスキング ===")
    for text in samples:
        masked, found = mask_pii(text)
        print(f"  原文  : {text}")
        print(f"  マスク: {masked}")
        print(f"  検出種別: {found if found else '（正規表現では検出できず＝取りこぼし例）'}")
        print()


if __name__ == "__main__":
    main()
