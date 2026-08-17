"""15-4 権限最小化とツールスコープ ── 通っても、できることを絞る（オフライン）

役割ごとに使ってよいツールを絞り、許可外の呼び出しを弾く。不可逆な操作は自動実行させず
HITL（15-7）へ回す対象になる。本番では実際のツール認可（第4・8章）に置き換える。
"""

from __future__ import annotations

from _common import TOOL_SCOPES, IRREVERSIBLE_TOOLS, check_tool_scope


def main():
    tools = ["search_docs", "read_crm", "send_email", "delete_doc"]
    roles = ["engineer", "sales", "hr"]

    print("=== ツールごとの権限スコープ（○=許可／×=拒否）===")
    header = "role".ljust(10) + "".join(t.ljust(14) for t in tools)
    print(header)
    for role in roles:
        row = role.ljust(10)
        for tool in tools:
            allowed = check_tool_scope(role, tool)
            mark = "○" if allowed else "×"
            if tool in IRREVERSIBLE_TOOLS:
                mark += "(不可逆)"
            row += mark.ljust(13)
        print(row)

    print("\n=== 許可外ツールの拒否 ===")
    role, tool = "engineer", "send_email"
    if not check_tool_scope(role, tool):
        print(f"  {role} は {tool} を使えません（最小権限で拒否）。")
        if tool in IRREVERSIBLE_TOOLS:
            print("  かつ不可逆な操作なので、実行するなら人間の承認（HITL）が要ります。")


if __name__ == "__main__":
    main()
