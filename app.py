import os
import time
import socket
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# ── Configuration injectée par DevBoard (variables d'environnement) ──
SERVICE_NAME = os.getenv("SERVICE_NAME", "demo-service")
SERVICE_ROLE = os.getenv("SERVICE_ROLE", "generic")
CURRENCY     = os.getenv("CURRENCY", "EUR")
API_KEY      = os.getenv("PAYMENT_API_KEY", "")
DEPENDS_ON   = [d.strip() for d in os.getenv("DEPENDS_ON", "").split(",") if d.strip()]
DEP_PORT     = os.getenv("DEP_PORT", "5000")


@app.route("/health")
def health():
    """Sonde de disponibilité utilisée par Kubernetes et par DevBoard."""
    return jsonify(status="healthy", service=SERVICE_NAME), 200


@app.route("/")
def index():
    """Page d'accueil : expose la configuration réellement injectée."""
    return jsonify({
        "service": SERVICE_NAME,
        "role":    SERVICE_ROLE,
        "pod":     socket.gethostname(),
        "config": {
            "CURRENCY":        CURRENCY,
            "PAYMENT_API_KEY": "**** (secret injected)" if API_KEY else "(not set)",
            "DEPENDS_ON":      DEPENDS_ON,
        }
    })


@app.route("/pay")
def pay():
    """Simule un paiement."""
    return jsonify(
        service=SERVICE_NAME,
        action="payment_processed",
        amount=70.90,
        currency=CURRENCY,
        pod=socket.gethostname(),
        version="v4"
    )


@app.route("/order")
def order():
    """Crée une commande en appelant réellement les services dont il dépend."""
    downstream = []
    for dep in DEPENDS_ON:
        try:
            r = requests.get(f"http://{dep}:{DEP_PORT}/pay", timeout=3)
            downstream.append({
                "dependency": dep,
                "status":     r.status_code,
                "response":   r.json()
            })
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
    """Brûle du CPU pendant N secondes — sert à déclencher l'autoscaling HPA."""
    seconds = float(request.args.get("seconds", 10))
    end = time.time() + seconds
    while time.time() < end:
        sum(i * i for i in range(5000))
    return jsonify(service=SERVICE_NAME, pod=socket.gethostname(), burned=seconds)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
