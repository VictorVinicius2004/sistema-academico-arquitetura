# Servico de Notificacao - porta 5002
# Recebe destinatario e mensagem e "envia" (por enquanto so escreve no log).
# Nao depende de nada do dominio de eventos, entao outros sistemas podem usar.

import os
import sys

from flask import Flask, request, jsonify
from flasgger import Swagger

# precisa disso pra conseguir importar o comum/auth.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import requer_papel  # noqa: E402

app = Flask(__name__)
app.config["SWAGGER"] = {"title": "EventHub - Notificação", "uiversion": 3}
Swagger(app)  # documentacao em /apidocs


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "notificacao"}), 200


@app.post("/notificacoes")
@requer_papel("admin", "organizador", "participante")
def criar_notificacao():
    """
    Registra o envio de uma notificação (e-mail simulado: só escreve no log)
    ---
    tags:
      - Notificação
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer <token>
      - in: body
        name: notificacao
        required: true
        schema:
          type: object
          required: [destinatario, mensagem]
          properties:
            destinatario:
              type: string
              example: eric@ifnmg.edu.br
            mensagem:
              type: string
              example: Inscrição confirmada no evento Semana de SI
    responses:
      201:
        description: Notificação registrada
        schema:
          type: object
          properties:
            status:
              type: string
              example: registrada
      400:
        description: Faltou destinatario ou mensagem
      401:
        description: Token ausente, inválido ou expirado
    """
    dados = request.get_json(silent=True) or {}
    destinatario = dados.get("destinatario")
    mensagem = dados.get("mensagem")

    if not destinatario or not mensagem:
        return jsonify({"erro": "destinatario e mensagem são obrigatórios"}), 400

    # nao manda email de verdade, so mostra no log
    # flush pra aparecer na hora no docker compose logs
    print(f"[NOTIFICAÇÃO] Para: {destinatario} | Mensagem: {mensagem}", flush=True)

    return jsonify({"status": "registrada"}), 201


if __name__ == "__main__":
    # 0.0.0.0 pra aceitar conexao de outros containers
    app.run(host="0.0.0.0", port=5002, debug=True)
