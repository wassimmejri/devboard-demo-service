import os
import time
import socket
from flask import Flask, jsonify, request, Response
import requests

app = Flask(__name__)

# ── Configuration injectée par DevBoard ──
SERVICE_NAME = os.getenv("SERVICE_NAME", "demo-service")
SERVICE_ROLE = os.getenv("SERVICE_ROLE", "generic")
CURRENCY     = os.getenv("CURRENCY", "EUR")
API_KEY      = os.getenv("PAYMENT_API_KEY", "")
DEPENDS_ON   = [d.strip() for d in os.getenv("DEPENDS_ON", "").split(",") if d.strip()]
DEP_PORT     = os.getenv("DEP_PORT", "5000")
APP_VERSION  = os.getenv("APP_VERSION", "v1")

ROLE_ICONS = {"payment": "💳", "order": "🧾", "notification": "🔔", "generic": "📦"}


@app.route("/health")
def health():
    return jsonify(status="healthy", service=SERVICE_NAME), 200


@app.route("/")
def index():
    icon      = ROLE_ICONS.get(SERVICE_ROLE, "📦")
    secret_ok = bool(API_KEY)

    deps_html = "".join(
        f'<span class="chip chip--dep">🔗 {d}</span>' for d in DEPENDS_ON
    ) or '<span class="muted">no dependency</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SERVICE_NAME}</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@600;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    min-height: 100vh;
    background: #020810;
    color: #e0f4ff;
    font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; justify-content: center;
    padding: 32px;
    background-image:
      linear-gradient(rgba(0,180,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,180,255,0.03) 1px, transparent 1px);
    background-size: 44px 44px;
  }}
  .card {{
    width: 100%; max-width: 620px;
    background: rgba(8,20,48,0.72);
    backdrop-filter: blur(18px);
    border: 1px solid rgba(0,180,255,0.18);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 24px 64px rgba(0,0,0,0.6), 0 0 40px rgba(0,150,255,0.08);
  }}
  .card::before {{
    content: ''; display: block; height: 2px;
    background: linear-gradient(90deg, transparent 5%, #015a72 30%, #00b8d9 50%, #015a72 70%, transparent 95%);
  }}
  .head {{ padding: 26px 28px 20px; border-bottom: 1px solid rgba(0,140,255,0.10); }}
  .head__top {{ display: flex; align-items: center; gap: 14px; }}
  .avatar {{
    width: 52px; height: 52px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px;
    background: rgba(0,180,255,0.08);
    border: 1px solid rgba(0,180,255,0.22);
  }}
  h1 {{
    font-family: 'Syne', sans-serif; font-size: 24px; font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, #e0f4ff, #00e5ff);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .role {{ font-size: 11px; color: #2e5a72; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 3px; }}
  .status {{
    margin-left: auto; display: inline-flex; align-items: center; gap: 7px;
    padding: 5px 12px; border-radius: 20px;
    background: rgba(0,230,118,0.10); border: 1px solid rgba(0,230,118,0.28);
    color: #00e676; font-size: 11px; font-weight: 700;
  }}
  .dot {{ width: 7px; height: 7px; border-radius: 50%; background: #00e676; animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; box-shadow:0 0 0 0 rgba(0,230,118,.5) }} 50% {{ opacity:.5; box-shadow:0 0 0 6px rgba(0,230,118,0) }} }}
  .version {{
    display: inline-block; margin-top: 14px;
    padding: 4px 12px; border-radius: 8px;
    background: rgba(0,200,255,0.08); border: 1px solid rgba(0,200,255,0.22);
    color: #00e5ff; font-size: 13px; font-weight: 700;
  }}
  .body {{ padding: 22px 28px 26px; }}
  .label {{
    font-size: 10px; color: #2e5a72; text-transform: uppercase;
    letter-spacing: 0.12em; margin: 18px 0 9px; font-weight: 700;
  }}
  .label:first-child {{ margin-top: 0; }}
  .row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; margin-bottom: 6px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(0,140,255,0.10);
    border-radius: 9px; font-size: 12px;
  }}
  .key {{ color: #7ab0cc; font-weight: 700; }}
  .val {{ color: #e0f4ff; }}
  .val--secret {{ color: #a78bfa; letter-spacing: 2px; }}
  .badge {{ font-size: 10px; padding: 2px 8px; border-radius: 5px; margin-left: 8px; }}
  .badge--cm {{ background: rgba(0,180,255,0.10); color: #00b8d9; border: 1px solid rgba(0,180,255,0.22); }}
  .badge--sec {{ background: rgba(167,139,250,0.12); color: #a78bfa; border: 1px solid rgba(167,139,250,0.28); }}
  .chip {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 11px; margin: 0 6px 6px 0; border-radius: 20px;
    background: rgba(0,180,255,0.07); border: 1px solid rgba(0,180,255,0.20);
    color: #00b8d9; font-size: 11px;
  }}
  .muted {{ color: #2e5a72; font-size: 11px; }}
  .pod {{
    margin-top: 20px; padding: 12px 14px;
    background: rgba(0,0,0,0.28); border: 1px solid rgba(0,140,255,0.10);
    border-radius: 9px; font-size: 11px; color: #7ab0cc;
    display: flex; align-items: center; gap: 8px;
  }}
  .links {{ display: flex; gap: 8px; margin-top: 20px; flex-wrap: wrap; }}
  .links a {{
    padding: 8px 15px; border-radius: 9px; text-decoration: none;
    background: rgba(0,180,255,0.08); border: 1px solid rgba(0,180,255,0.22);
    color: #00b8d9; font-size: 11px; font-weight: 700;
    transition: all .18s;
  }}
  .links a:hover {{ background: rgba(0,180,255,0.16); border-color: #00e5ff; color: #00e5ff; }}
  .foot {{
    padding: 14px 28px; border-top: 1px solid rgba(0,140,255,0.10);
    background: rgba(0,0,0,0.20);
    font-size: 10px; color: #2e5a72; text-align: center; letter-spacing: 0.06em;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="head">
      <div class="head__top">
        <div class="avatar">{icon}</div>
        <div>
          <h1>{SERVICE_NAME}</h1>
          <div class="role">{SERVICE_ROLE} service</div>
        </div>
        <span class="status"><span class="dot"></span>RUNNING</span>
      </div>
      <span class="version">{APP_VERSION}</span>
    </div>

    <div class="body">
      <div class="label">Injected configuration</div>

      <div class="row">
        <span class="key">SERVICE_NAME</span>
        <span><span class="val">{SERVICE_NAME}</span><span class="badge badge--cm">ConfigMap</span></span>
      </div>
      <div class="row">
        <span class="key">SERVICE_ROLE</span>
        <span><span class="val">{SERVICE_ROLE}</span><span class="badge badge--cm">ConfigMap</span></span>
      </div>
      <div class="row">
        <span class="key">CURRENCY</span>
        <span><span class="val">{CURRENCY}</span><span class="badge badge--cm">ConfigMap</span></span>
      </div>
      <div class="row">
        <span class="key">PAYMENT_API_KEY</span>
        <span>
          <span class="{'val val--secret' if secret_ok else 'muted'}">{'••••••••••••' if secret_ok else 'not set'}</span>
          {'<span class="badge badge--sec">K8s Secret</span>' if secret_ok else ''}
        </span>
      </div>

      <div class="label">Dependencies</div>
      <div>{deps_html}</div>

      <div class="pod">🖥️ pod : {socket.gethostname()}</div>

      <div class="links">
        <a href="/pay">/pay</a>
        <a href="/order">/order</a>
        <a href="/health">/health</a>
        <a href="/load?seconds=5">/load</a>
      </div>
    </div>

    <div class="foot">DEVBOARD · NEXT STEP IT · deployed via Jenkins &amp; Kaniko on Kubernetes</div>
  </div>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/pay")
def pay():
    return jsonify(
        service=SERVICE_NAME,
        action="payment_processed",
        amount=200.90,
        currency=CURRENCY,
        pod=socket.gethostname(),
        version=APP_VERSION
    )


@app.route("/order")
def order():
    downstream = []
    for dep in DEPENDS_ON:
        try:
            r = requests.get(f"http://{dep}:{DEP_PORT}/pay", timeout=3)
            downstream.append({"dependency": dep, "status": r.status_code, "response": r.json()})
        except Exception as e:
            downstream.append({"dependency": dep, "error": str(e)})
    return jsonify(
        service=SERVICE_NAME,
        action="order_created",
        pod=socket.gethostname(),
        downstream=downstream
    )


@app.route("/load")
def load():
    seconds = float(request.args.get("seconds", 10))
    end = time.time() + seconds
    while time.time() < end:
        sum(i * i for i in range(5000))
    return jsonify(service=SERVICE_NAME, pod=socket.gethostname(), burned=seconds)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
