import os
import sys
import jwt
import requests
from flask import Flask, request, jsonify, Response

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import extrair_e_validar_token

app = Flask(__name__)

URL_IDENTIDADE = os.getenv("URL_IDENTIDADE", "http://localhost:5001")
URL_NOTIFICACAO = os.getenv("URL_NOTIFICACAO", "http://localhost:5002")
URL_ORQUESTRADOR = os.getenv("URL_ORQUESTRADOR", "http://localhost:5003")
URL_EVENTOS = os.getenv("URL_EVENTOS", "http://localhost:5004")
URL_INSCRICOES = os.getenv("URL_INSCRICOES", "http://localhost:5005")
URL_CERTIFICADOS = os.getenv("URL_CERTIFICADOS", "http://localhost:5006")


def resolver_destino(path: str, method: str):
    if path == "auth" or path.startswith("auth/") or path == "usuarios" or path.startswith("usuarios/"):
        return URL_IDENTIDADE
    if path == "eventos" or path.startswith("eventos/"):
        return URL_EVENTOS
    if path == "inscricoes" and method == "POST":
        return URL_ORQUESTRADOR
    if path == "inscricoes" or path.startswith("inscricoes/"):
        return URL_INSCRICOES
    if path == "certificados" or path.startswith("certificados/"):
        return URL_CERTIFICADOS
    return None


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "api-gateway"}), 200


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(path: str):
    rota_publica = path == "auth/login" and request.method == "POST"

    if not rota_publica:
        auth_header = request.headers.get("Authorization", "")
        try:
            extrair_e_validar_token(auth_header)
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Token expirado"}), 401
        except (jwt.InvalidTokenError, ValueError) as exc:
            return jsonify({"erro": f"Não autorizado: {str(exc)}"}), 401

    destino_base = resolver_destino(path, request.method)
    if not destino_base:
        return jsonify({"erro": "Rota não encontrada no API Gateway"}), 404

    url_destino = f"{destino_base}/{path}"

    headers_repasse = {}
    if "Authorization" in request.headers:
        headers_repasse["Authorization"] = request.headers["Authorization"]
    if "Content-Type" in request.headers:
        headers_repasse["Content-Type"] = request.headers["Content-Type"]

    try:
        resp = requests.request(
            method=request.method,
            url=url_destino,
            params=request.args,
            headers=headers_repasse,
            data=request.get_data(),
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return jsonify({"erro": "Serviço de destino indisponível"}), 502

    content_type = resp.headers.get("Content-Type", "application/json")
    return Response(resp.content, status=resp.status_code, content_type=content_type)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)