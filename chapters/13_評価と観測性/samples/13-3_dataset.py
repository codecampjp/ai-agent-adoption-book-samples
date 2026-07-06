"""13-3 評価データセットの中身を見る（オフライン）

本文 13-3 の「入力＋期待する観点」の組を、そのまま表示する。正常系だけでなく
「弾くべきケース」（権限のない機密／存在しない情報）も含まれていることを確認する。
"""

from __future__ import annotations

from _common import DATASET


def main():
    print("=== 評価データセット（入力＋期待する観点）===")
    for case in DATASET:
        exp = case["expected"]
        kind = "弾くべきケース" if exp["must_refuse"] else "正常系"
        print(f"\n[{case['id']}] ({kind}) 権限={case['role']}")
        print(f"  入力      : {case['input']}")
        print(f"  期待の観点: 引用必須={exp['must_cite']} / 断るべき={exp['must_refuse']}")
        print(f"  期待の道筋: {' → '.join(exp['trajectory'])}")
    print(f"\n合計 {len(DATASET)} 件（正常系＋弾くべきケースを両方含む）")


if __name__ == "__main__":
    main()
