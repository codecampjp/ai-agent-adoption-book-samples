"""12-2 コンパイル済みグラフをMermaid形式で書き出す。

APIキーとネットワークは不要。12-2_agent_pipeline.pyのbuild_graph()を読み込み、
LangGraphが持つノードとエッジを12-2_agent_pipeline.mmdへ出力する。
"""

from pathlib import Path
import importlib.util
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def main():
    module_name = "chapter12_agent_pipeline"
    module_path = HERE / "12-2_agent_pipeline.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"モジュールを読み込めません: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    graph = module.build_graph()
    mermaid = graph.get_graph().draw_mermaid()
    output = HERE / "12-2_agent_pipeline.mmd"
    output.write_text(mermaid, encoding="utf-8")
    print(f"出力: {output.name}")


if __name__ == "__main__":
    main()
