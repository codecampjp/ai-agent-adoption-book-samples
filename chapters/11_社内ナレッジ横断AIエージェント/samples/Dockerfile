# 第11章サンプル用の保険（本書の手順は venv 直を前提。Docker は必須ではない）
#
#   docker build -t ch11-samples .
#   docker run -it --rm ch11-samples
#   （コンテナ内で）python 11-2_agent_pipeline.py など
#
# すべてオフラインのドライランなので、ネットワークもAPIキーも渡す必要はない。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /work

# 依存を先に入れてレイヤーキャッシュを効かせる
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash"]
