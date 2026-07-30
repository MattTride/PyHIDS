FROM python:3.13-slim

WORKDIR /app

# ── 先装依赖（这层能被缓存，改源码时不用重装）──
COPY pyproject.toml README.md LICENSE ./
COPY pyhids/ ./pyhids/
RUN pip install --no-cache-dir .

# ── 再拷默认配置 ──
COPY config/ ./config/

# ── 把数据指向挂卷点（M5.2 的三个环境变量在这里兑现）──
ENV PYHIDS_DB_PATH=/data/events.db
ENV PYHIDS_BASELINE_PATH=/data/baseline.json
ENV PYHIDS_CONFIG_PATH=/app/config/watchlist.yaml

# ── 非 root 用户：被攻破时限制影响范围 ──
# UID 固定成 1000，方便宿主机 chown 挂卷目录（Linux 上按 UID 匹配，与用户名无关）
RUN useradd --create-home --uid 1000 pyhids \
    && mkdir -p /data \
    && chown -R pyhids:pyhids /data /app
USER pyhids

EXPOSE 8000

# ── 健康检查：容器"活着"不等于"能服务" ──
# 基础镜像里没有 curl，用 Python 标准库发请求，避免为此多装一个包
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/events?limit=1', timeout=4).status == 200 else sys.exit(1)"

CMD ["pyhids", "serve", "--host", "0.0.0.0"]
