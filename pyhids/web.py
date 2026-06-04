"""
pyhids.web - 事件仪表盘的Web应用
"""
from __future__ import annotations
from fastapi import FastAPI
from pyhids.store import query_events
from fastapi.responses import HTMLResponse

app = FastAPI(title="PyHIDS Dashboard")
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
  </style>
</head>
<body>
  <h1>🛡️ PyHIDS 事件仪表盘</h1>
  <table>
    <thead>
      <tr><th>时间</th><th>来源</th><th>等级</th><th>摘要</th></tr>
    </thead>
    <tbody id="events"></tbody>
  </table>
  <script>
    async function load() {
      const res = await fetch('/api/events');
      const events = await res.json();
      const tbody = document.getElementById('events');
      tbody.innerHTML = '';
      for (const e of events) {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${e.detected_at}</td><td>${e.source}</td>`
                      + `<td class="${e.severity}">${e.severity}</td><td>${e.summary}</td>`;
        tbody.appendChild(row);
      }
    }
    load();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML
@app.get("/api/events")
def api_events(limit: int = 50, source: str | None =None) -> list[dict]:
    """返回最近的事件，最新在前"""
    events = query_events(limit=limit, source=source)
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