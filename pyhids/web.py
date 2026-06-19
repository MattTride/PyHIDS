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
    .filters { margin-bottom: 1rem; }
    .filters label { margin-right: 1rem; }
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
  </div>
  <table>
    <thead>
      <tr><th>时间</th><th>来源</th><th>等级</th><th>摘要</th></tr>
    </thead>
    <tbody id="events"></tbody>
  </table>
  <script>
    async function load() {
      const source = document.getElementById('source-filter').value;
      const severity = document.getElementById('severity-filter').value;
      const params = new URLSearchParams();
      if (source) params.set('source', source);
      if (severity) params.set('severity', severity);

      const res = await fetch('/api/events?' + params.toString());
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
    document.getElementById('source-filter').addEventListener('change', load);
    document.getElementById('severity-filter').addEventListener('change', load);
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML
@app.get("/api/events")
def api_events(limit: int = 50, source: str | None = None, severity: str | None = None) -> list[dict]:
    """返回最近的事件，最新在前"""
    events = query_events(limit=limit, source=source, severity=severity)
    
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