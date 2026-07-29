FROM python:3.13-slim

WORKDIR /app

# ── 先装依赖（这层能被缓存，改源码时不用重装）──
COPY pyproject.toml README.md LICENSE ./
COPY pyhids/ ./pyhids/
RUN pip install --no-cache-dir .

# ── 再拷默认配置 ──
COPY config/ ./config/

# ── 把数据指向挂卷点（M5.2 的三个环境变量在这里兑现）──
# TODO(1): DB 文件放 /data/ 下
ENV PYHIDS_DB_PATH=/data/events.db
# TODO(2): 基线文件也放 /data/ 下
ENV PYHIDS_BASELINE_PATH=/data/baseline.json
# TODO(3): 配置放哪？挂出来给用户改，还是烤进镜像？选一个，说理由
ENV PYHIDS_CONFIG_PATH=/app/config/watchlist.yaml

# TODO(4): 端口号 —— 看 cli.py 里 serve 的默认值
EXPOSE 8000

# TODO(5): 容器里必须监听哪个地址？（不是 127.0.0.1，想想为什么）
CMD ["pyhids", "serve", "--host", "0.0.0.0"]
