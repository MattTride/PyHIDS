"""
pyhids.web - 事件仪表盘的Web应用
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from pyhids.store import max_event_id, query_events

app = FastAPI(title="PyHIDS Dashboard")

# SSE 轮询数据库的间隔（秒）。这不是前端轮询 —— 前端只是挂着一条连接等推送。
STREAM_POLL_SECONDS = 1.0

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>PyHIDS Dashboard</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #f4f4f4; }
    .critical { color: #c0392b; font-weight: bold; }
    .warning { color: #e67e22; }
    .filters { margin-bottom: 1rem; }
    .filters label { margin-right: 1rem; }
    .pager { margin-top: 1rem; display: flex; align-items: center; gap: 1rem; }
    .pager button:disabled { opacity: .4; cursor: not-allowed; }
    #status { margin-left: auto; font-size: .85rem; color: #666; }
    #status.live::before { content: "● "; color: #27ae60; }
    #status.down::before { content: "● "; color: #c0392b; }
  </style>
</head>
<body>
  <h1>🛡️ PyHIDS 事件仪表盘</h1>
  <div class="filters">
    <label>来源:
      <select id="source-filter">
        <option value="">全部</option>
        <option value="file_integrity">file_integrity</option>
        <option value="ssh_brute_force">ssh_brute_force</option>
        <option value="privilege_escalation">privilege_escalation</option>
      </select>
    </label>
    <label>等级:
      <select id="severity-filter">
        <option value="">全部</option>
        <option value="critical">critical</option>
        <option value="warning">warning</option>
        <option value="info">info</option>
      </select>
    </label>
    <label>每页:
      <select id="page-size">
        <option value="20">20</option>
        <option value="50" selected>50</option>
        <option value="100">100</option>
      </select>
    </label>
  </div>
  <table>
    <thead>
      <tr><th>时间</th><th>来源</th><th>等级</th><th>摘要</th></tr>
    </thead>
    <tbody id="events"></tbody>
  </table>
  <div class="pager">
    <button id="prev">← 上一页</button>
    <span id="page-info">第 1 页</span>
    <button id="next">下一页 →</button>
    <span id="status">连接中…</span>
  </div>

  <script>
    let offset = 0;

    const $ = (id) => document.getElementById(id);
    const pageSize = () => parseInt($('page-size').value, 10);

    async function load() {
      const params = new URLSearchParams();
      const source = $('source-filter').value;
      const severity = $('severity-filter').value;
      if (source) params.set('source', source);
      if (severity) params.set('severity', severity);
      params.set('limit', pageSize());
      params.set('offset', offset);

      const res = await fetch('/api/events?' + params.toString());
      const events = await res.json();

      const tbody = $('events');
      tbody.replaceChildren();
      for (const e of events) {
        const row = document.createElement('tr');
        for (const value of [e.detected_at, e.source, e.severity, e.summary]) {
          const cell = document.createElement('td');
          cell.textContent = String(value ?? '');
          row.appendChild(cell);
        }
        if (['critical', 'warning', 'info'].includes(e.severity)) {
          row.children[2].classList.add(e.severity);
        }
        tbody.appendChild(row);
      }

      $('page-info').textContent = `第 ${offset / pageSize() + 1} 页`;
      $('prev').disabled = offset === 0;
      // 拿到的行数不足一页，说明没有下一页了
      $('next').disabled = events.length < pageSize();
    }

    // ── 分页 ──
    $('prev').onclick = () => { offset = Math.max(0, offset - pageSize()); load(); };
    $('next').onclick = () => { offset += pageSize(); load(); };

    // 改筛选条件或每页条数都要回到第一页，否则可能停在一个空页上
    for (const id of ['source-filter', 'severity-filter', 'page-size']) {
      $(id).addEventListener('change', () => { offset = 0; load(); });
    }

    // ── SSE：服务端有新事件才推，不再定时空轮询 ──
    const stream = new EventSource('/api/stream');
    stream.onmessage = (msg) => {
      $('status').textContent = '实时连接中';
      $('status').className = 'live';
      // 只有停在第一页时才自动刷新，否则会把正在翻页的用户拽走
      if (offset === 0) load();
    };
    stream.onerror = () => {
      $('status').textContent = '连接中断，重连中…';
      $('status').className = 'down';
    };

    load();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/api/events")
def api_events(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    source: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    """返回事件，最新在前。offset 用于分页。"""
    events = query_events(limit=limit, offset=offset, source=source, severity=severity)

    return [
        {
            "detected_at": e.detected_at.isoformat(),
            "source": e.source,
            "severity": e.severity,
            "summary": e.summary,
            "payload": e.payload,
        }
        for e in events
    ]


async def cursor_stream():
    """产出 SSE 消息：连上先推一次当前游标，之后只在出现新事件时推。

    这是个无限生成器 —— 客户端断开时由 Starlette 关闭它。写成模块级函数（而不是
    藏在路由里的闭包）是为了能在测试里直接拿 anext() 取一条就 aclose()，
    不用起 HTTP 连接去等一个永不结束的响应。
    """
    last_id = max_event_id()
    yield f"data: {json.dumps({'max_id': last_id})}\n\n"

    while True:
        await asyncio.sleep(STREAM_POLL_SECONDS)
        current_id = max_event_id()
        if current_id != last_id:
            last_id = current_id
            yield f"data: {json.dumps({'max_id': current_id})}\n\n"
        else:
            # 以 ':' 开头的是 SSE 注释行，前端会忽略；作用是防止
            # 反向代理因长时间无数据而掐断连接
            yield ": keep-alive\n\n"


@app.get("/api/stream")
async def api_stream() -> StreamingResponse:
    """Server-Sent Events：库里出现新事件时推一条消息，前端收到就重新拉数据。

    只推游标（当前最大 id），不推事件内容 —— 这样筛选和分页逻辑全留在前端已有的
    load() 里，不用在推送通道里重复实现一遍。
    """
    return StreamingResponse(
        cursor_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
