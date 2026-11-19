import os
import sys
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, g

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comum.auth import requer_papel

app = Flask(__name__)

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "certificados.db"))
URL_INSCRICOES = os.getenv("URL_INSCRICOES", "http://localhost:5005")
SIMULADO = os.getenv("SIMULADO") == "1"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS certificados (
                codigo TEXT PRIMARY KEY,
                inscricao_id INTEGER UNIQUE NOT NULL,
                evento_id INTEGER NOT NULL,
                nome_participante TEXT NOT NULL,
                data_emissao TEXT NOT NULL
            )
        """)
    conn.close()


init_db()


def buscar_inscricao(inscricao_id, token):
    """Retorna (dados, status_http). 502 = ms-inscricoes fora do ar."""
    if SIMULADO:
        base = {"id": inscricao_id, "evento_id": 7, "usuario_id": 3,
                "status": "ativa", "presente": True}
        if inscricao_id == 999:
            return None, 404
        if inscricao_id == 16:
            base["presente"] = False
        elif inscricao_id == 17:
            base["status"] = "cancelada"
        elif inscricao_id == 18:
            base["usuario_id"] = 99
        return base, 200

    try:
        resp = requests.get(
            f"{URL_INSCRICOES}/inscricoes/{inscricao_id}",
            headers={"Authorization": token},
            timeout=3,
        )
    except requests.RequestException:
        return None, 502

    if resp.status_code == 200:
        return resp.json(), 200
    return None, resp.status_code


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "ms-certificados"}), 200


@app.post("/certificados")
@requer_papel("participante")
def emitir_certificado():
    dados = request.get_json(silent=True) or {}
    inscricao_id = dados.get("inscricao_id")

    if not isinstance(inscricao_id, int) or isinstance(inscricao_id, bool):
        return jsonify({"erro": "inscricao_id é obrigatório e deve ser um número"}), 400

    inscricao, status_http = buscar_inscricao(
        inscricao_id, request.headers.get("Authorization", "")
    )

    if status_http == 404:
        return jsonify({"erro": "inscrição não encontrada"}), 404
    if status_http == 502:
        return jsonify({"erro": "serviço de inscrições indisponível"}), 502
    if status_http != 200 or not inscricao:
        return jsonify({"erro": "erro ao consultar serviço de inscrições"}), 502

    if inscricao.get("usuario_id") != int(g.usuario["sub"]):
        return jsonify({"erro": "esta inscrição não pertence a você"}), 403

    if inscricao.get("status") != "ativa":
        return jsonify({"erro": "inscrição cancelada"}), 400
    if inscricao.get("presente") is not True:
        return jsonify({"erro": "presença não registrada"}), 400

    codigo = uuid.uuid4().hex[:12].upper()
    evento_id = inscricao["evento_id"]
    nome = g.usuario.get("nome", "Participante")
    data_emissao = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO certificados (codigo, inscricao_id, evento_id, "
                "nome_participante, data_emissao) VALUES (?, ?, ?, ?, ?)",
                (codigo, inscricao_id, evento_id, nome, data_emissao),
            )
    except sqlite3.IntegrityError:
        return jsonify({"erro": "certificado já emitido para esta inscrição"}), 409
    finally:
        conn.close()

    return jsonify({
        "codigo": codigo,
        "inscricao_id": inscricao_id,
        "evento_id": evento_id,
        "nome_participante": nome,
        "data_emissao": data_emissao,
    }), 201


@app.get("/certificados/<string:codigo>")
@requer_papel("admin", "organizador", "participante")
def consultar_certificado(codigo):
    conn = get_db()
    cert = conn.execute(
        "SELECT * FROM certificados WHERE codigo = ?", (codigo.upper(),)
    ).fetchone()
    conn.close()

    if not cert:
        return jsonify({"erro": "certificado não encontrado"}), 404
    return jsonify(dict(cert)), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5006)