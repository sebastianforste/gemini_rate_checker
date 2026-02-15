import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Load directory of the script to find .env
SCRIPT_DIR = Path(__file__).parent.resolve()
load_dotenv(SCRIPT_DIR / ".env")

# API Key securely loaded from .env
API_KEY = os.getenv('GEMINI_API_KEY')
HISTORY_FILE = SCRIPT_DIR / "gemini_rate_history.json"
REPORT_FILE = SCRIPT_DIR / "gemini_rate_check_results.html"

def classify_model_response(status_code: int) -> tuple[bool, str]:
    """Convert an HTTP status code into a normalized check outcome."""
    if status_code == 200:
        return True, "OK"
    if status_code == 429:
        return False, "Rate Limit (429)"
    return False, f"Error {status_code}"

def extract_testable_models(api_payload: dict[str, Any]) -> list[str]:
    """Return Gemini model names that support generateContent and are not Gemma."""
    models = api_payload.get("models", [])
    selected: list[str] = []
    for model in models:
        model_name = model.get("name", "")
        methods = model.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        if "gemma" in model_name.lower():
            continue
        selected.append(model_name)
    return selected

def serialize_results(results: list[tuple[bool, str, str]]) -> list[dict[str, Any]]:
    """Convert tuple results into JSON-friendly dictionaries."""
    return [
        {
            "success": success,
            "model": model_name,
            "status": status,
        }
        for success, model_name, status in results
    ]

def save_history(results):
    """Save the run results to a persistent JSON history file."""
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "success": sum(1 for r in results if r[0]),
        "details": [{"model": r[1], "status": r[2], "success": r[0]} for r in results]
    }
    
    history.append(entry)
    
    # Keep last 50 runs
    history = history[-50:]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"History updated: {HISTORY_FILE}")

def generate_html_report(latest_results):
    """Generate the cinematic HTML report showing full history with interactive details."""
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except Exception as e:
            print(f"Error loading history for report: {e}")
    
    # Sort history by newest first
    history = sorted(history, key=lambda x: x['timestamp'], reverse=True)
    
    total_runs = len(history)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate global stats
    total_checks = sum(h['total'] for h in history)
    total_successes = sum(h['success'] for h in history)
    avg_uptime = (total_successes / total_checks * 100) if total_checks > 0 else 0

    # Prepare historical data for JS
    history_json = json.dumps(history)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset='utf-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Rate Dashboard</title>
    <style>
        :root {{ --bg: #09090b; --card-bg: #18181b; --border: #27272a; --text: #e4e4e7; --text-muted: #a1a1aa; --primary: #3b82f6; --success: #4ade80; --error: #f87171; --warning: #f59e0b; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 40px; max-width: 1000px; margin: 0 auto; line-height: 1.5; }}
        h1, h2, h3 {{ color: #fff; margin-bottom: 20px; }}
        h1 {{ text-align: center; margin-bottom: 5px; }}
        .meta {{ text-align: center; color: var(--text-muted); font-size: 0.9em; margin-bottom: 40px; letter-spacing: 0.5px; }}
        
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .stat-box {{ background: var(--card-bg); padding: 20px; border-radius: 12px; border: 1px solid var(--border); text-align: center; transition: all 0.2s; }}
        .stat-box:hover {{ transform: translateY(-2px); border-color: var(--primary); box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #fff; margin-bottom: 4px; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
        
        .section-header {{ display: flex; align-items: center; justify-content: space-between; margin-top: 40px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
        
        table {{ border-collapse: separate; border-spacing: 0; width: 100%; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--card-bg); margin-bottom: 30px; }}
        th, td {{ padding: 14px 20px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #27272a; color: #fff; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: #222226; }}
        
        .status-badge {{ display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
        .status-success {{ background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); }}
        .status-fail {{ background: rgba(239, 68, 68, 0.1); color: var(--error); border: 1px solid rgba(239, 68, 68, 0.2); }}
        
        .model-name {{ font-family: 'Monaco', 'Consolas', monospace; color: var(--text); font-size: 13px; }}
        .timestamp {{ color: var(--text-muted); font-family: monospace; font-size: 12px; }}
        
        .history-grid {{ display: grid; gap: 10px; }}
        .history-row {{ display: flex; align-items: center; background: var(--card-bg); padding: 12px 20px; border-radius: 8px; border: 1px solid var(--border); justify-content: space-between; cursor: pointer; transition: all 0.2s; position: relative; overflow: hidden; }}
        .history-row:hover {{ border-color: var(--primary); background: #1f1f23; padding-left: 25px; }}
        .history-row::before {{ content: '→'; position: absolute; left: 8px; opacity: 0; color: var(--primary); transition: all 0.2s; }}
        .history-row:hover::before {{ opacity: 1; }}
        
        .history-stats {{ display: flex; gap: 20px; font-size: 13px; align-items: center; }}
        .uptime-bar-container {{ height: 4px; background: var(--border); border-radius: 2px; width: 100px; margin-left: 10px; overflow: hidden; }}
        .uptime-bar {{ height: 100%; background: var(--success); transition: width 0.5s ease-out; }}
        
        /* Modal / Details Styles */
        #detailsOverlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); display: none; z-index: 100; padding: 40px; overflow-y: auto; }}
        .modal-content {{ background: var(--bg); border: 1px solid var(--border); border-radius: 16px; width: 100%; max-width: 800px; margin: 0 auto; padding: 30px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }}
        .close-btn {{ position: absolute; top: 20px; right: 20px; background: var(--border); color: #fff; border: none; padding: 8px 15px; border-radius: 8px; cursor: pointer; font-weight: bold; }}
        .close-btn:hover {{ background: #3f3f46; }}

        @media (max-width: 600px) {{
            body {{ padding: 20px; }}
            .stats {{ grid-template-columns: 1fr 1fr; }}
            .history-stats {{ flex-direction: column; gap: 5px; align-items: flex-end; }}
            #detailsOverlay {{ padding: 10px; }}
        }}
    </style>
    </head>
    <body>
        <h1>Gemini Rate Dashboard</h1>
        <div class="meta">System Health Overview &bull; Last Update: {date_str}</div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" style="color: var(--primary)">{total_runs}</div>
                <div class="stat-label">Total Runs</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: var(--success)">{avg_uptime:.1f}%</div>
                <div class="stat-label">Global Success Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: var(--warning)">{total_checks}</div>
                <div class="stat-label">Total Requests</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{len(latest_results)}</div>
                <div class="stat-label">Models Monitored</div>
            </div>
        </div>

        <div class="section-header">
            <h2>Latest Deployment Results</h2>
            <div class="timestamp">Last Checked: {datetime.now().strftime("%H:%M:%S")}</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th width="120">Status</th>
                    <th>Model Endpoint</th>
                    <th>Signal Message</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Sort latest results: Success (True) first
    sorted_latest = sorted(latest_results, key=lambda x: x[0], reverse=True)
    for success, name, msg in sorted_latest:
        status_class = "status-success" if success else "status-fail"
        status_text = "Operational" if success else "Error"
        html_content += f"""
                <tr>
                    <td><span class="status-badge {status_class}">{status_text}</span></td>
                    <td class="model-name">{name}</td>
                    <td style="color: {'var(--success)' if success else 'var(--error)'}">{msg}</td>
                </tr>
        """
        
    html_content += f"""
            </tbody>
        </table>

        <div class="section-header">
            <h2>Historical Timeline</h2>
            <div class="timestamp">Click any row to see full results</div>
        </div>

        <div class="history-grid">
    """
    
    for idx, entry in enumerate(history):
        ts_raw = entry['timestamp']
        ts = datetime.fromisoformat(ts_raw).strftime("%b %d, %H:%M:%S")
        success_pct = (entry['success'] / entry['total'] * 100) if entry['total'] > 0 else 0
        row_color = "var(--success)" if success_pct > 90 else "var(--warning)" if success_pct > 50 else "var(--error)"
        
        html_content += f"""
            <div class="history-row" onclick="viewDetails({idx})">
                <div class="timestamp">{ts}</div>
                <div class="history-stats">
                    <span style="color: var(--text-muted)">Models: <b>{entry['total']}</b></span>
                    <span style="color: {row_color}">Success: <b>{entry['success']}</b></span>
                    <div style="display: flex; align-items: center;">
                        <span style="color: {row_color}; font-weight: bold; min-width: 45px; text-align: right;">{success_pct:.0f}%</span>
                        <div class="uptime-bar-container">
                            <div class="uptime-bar" style="width: {success_pct}%; background: {row_color}"></div>
                        </div>
                    </div>
                </div>
            </div>
        """

    html_content += f"""
        </div>

        <div id="detailsOverlay">
            <div class="modal-content">
                <button class="close-btn" onclick="closeDetails()">ESC / Close</button>
                <h2 id="modalTitle">Run Details</h2>
                <div id="modalMeta" class="meta" style="text-align: left; margin-bottom: 20px;"></div>
                <div id="modalTableContainer"></div>
            </div>
        </div>

        <div style="text-align: center; margin-top: 40px; color: #52525b; font-size: 12px; border-top: 1px solid var(--border); padding-top: 20px;">
            &copy; 2026 Antigravity Gemini Intelligence Monitoring Unit
        </div>

        <script>
            const historyData = {history_json};
            const overlay = document.getElementById('detailsOverlay');
            const title = document.getElementById('modalTitle');
            const meta = document.getElementById('modalMeta');
            const container = document.getElementById('modalTableContainer');

            function formatDate(isoStr) {{
                const d = new Date(isoStr);
                return d.toLocaleString();
            }}

            function viewDetails(index) {{
                const run = historyData[index];
                if (!run) return;

                title.innerText = "Run Details: " + formatDate(run.timestamp);
                meta.innerText = `Operational: ${{run.success}} / ${{run.total}} Models`;
                
                let html = `<table>
                    <thead>
                        <tr>
                            <th width="120">Status</th>
                            <th>Model</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>`;
                
                // Sort details: failures first to highlight issues
                const sortedDetails = [...run.details].sort((a,b) => (a.success === b.success) ? 0 : a.success ? 1 : -1);

                sortedDetails.forEach(d => {{
                    const statusClass = d.success ? 'status-success' : 'status-fail';
                    const statusText = d.success ? 'Operational' : 'Error';
                    const msgColor = d.success ? 'var(--success)' : 'var(--error)';
                    html += `<tr>
                        <td><span class="status-badge ${{statusClass}}">${{statusText}}</span></td>
                        <td class="model-name">${{d.model}}</td>
                        <td style="color: ${{msgColor}}">${{d.status}}</td>
                    </tr>`;
                }});

                html += '</tbody></table>';
                container.innerHTML = html;
                overlay.style.display = 'block';
                document.body.style.overflow = 'hidden';
            }}

            function closeDetails() {{
                overlay.style.display = 'none';
                document.body.style.overflow = 'auto';
            }}

            window.addEventListener('keydown', (e) => {{ if(e.key === 'Escape') closeDetails(); }});
            overlay.addEventListener('click', (e) => {{ if(e.target === overlay) closeDetails(); }});
        </script>
    </body>
    </html>
    """
    
    with open(REPORT_FILE, "w") as f:
        f.write(html_content)
    print(f"Interactive history dashboard generated: {REPORT_FILE}")

def run_check(json_out: Path | None = None, write_html: bool = True):
    if not API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in .env file.")
        return

    print("🚀 Starting Gemini Model Rate Checker...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    results = []
    
    try:
        response = requests.get(list_url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Error fetching models: {response.status_code} - {response.text}")
            return
        
        data = response.json()
        model_names = extract_testable_models(data)
        print(f"📦 Found {len(data.get('models', []))} models. Testing {len(model_names)} endpoints...\n")

        for model_name in model_names:
            print(f"🔍 Testing: {model_name}...", end=" ", flush=True)

            generate_url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": "Hello"}]}]
            }

            try:
                res = requests.post(
                    generate_url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=10
                )
                success, msg = classify_model_response(res.status_code)
                results.append((success, model_name, msg))

                if success:
                    print("✅ OK")
                elif res.status_code == 429:
                    print("⏳ 429")
                else:
                    print(f"❌ {msg}")

            except Exception as e:
                results.append((False, model_name, f"Exception: {str(e)}"))
                print("❌ Exception")

            time.sleep(0.5)

        print("\n📊 Run complete.")
        save_history(results)
        if write_html:
            generate_html_report(results)

        if json_out:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": datetime.now().isoformat(),
                "total": len(results),
                "success": sum(1 for success, _, _ in results if success),
                "results": serialize_results(results),
            }
            with open(json_out, "w") as f:
                json.dump(payload, f, indent=2)
            print(f"JSON report generated: {json_out}")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Gemini model availability and rate-limit status.")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional file path for structured JSON output.",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip generating the HTML dashboard output.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    run_check(json_out=args.json_out, write_html=not args.no_html)

if __name__ == "__main__":
    main()
