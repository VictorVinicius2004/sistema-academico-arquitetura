# Serviço de Notificação (porta 5002) — Integrante 4
# Recebe um destinatário e uma mensagem, "envia" (escreve no log) e responde 201.
#
# É um serviço SOA: genérico e reutilizável. Ele NÃO sabe o que é "evento" ou
# "inscrição"; só recebe destinatario + mensagem. Qualquer sistema poderia usá-lo.

import os
import sys

from flask import Flask, request, jsonify
from flasgger import Swagger

# O comum/auth.py fica UMA pasta acima desta. Quando rodamos
# "python notificacao/app.py", o Python só procura módulos dentro de notificacao/,
# então adicionamos a pasta raiz do projeto na lista de lugares onde ele procura.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import requer_papel  # noqa: E402  (import depois do sys.path, de propósito)

app = Flask(__name__)
app.config["SWAGGER"] = {"title": "EventHub — Notificação", "uiversion": 3}
Swagger(app)  # cria a página http://localhost:5002/apidocs a partir das docstrings


# Rota de saúde: só serve para conferir se o serviço está de pé (sem token).
@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "notificacao"}), 200


# Rota principal: POST /notificacoes
# A ordem dos decorators importa: primeiro o Flask registra a rota, e o
# @requer_papel "embrulha" a função, conferindo o token ANTES de ela rodar.
@app.post("/notificacoes")
@requer_papel("admin", "organizador", "participante")  # qualquer usuário autenticado
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
    dados = request.get_json(silent=True) or {}   # lê o JSON que veio no pedido
    destinatario = dados.get("destinatario")
    mensagem = dados.get("mensagem")

    # Se faltar algum campo, o pedido está errado: 400
    if not destinatario or not mensagem:
        return jsonify({"erro": "destinatario e mensagem são obrigatórios"}), 400

    # "Envia" a notificação: só escreve no terminal (não manda e-mail de verdade).
    # flush=True faz a linha aparecer na hora no "docker compose logs".
    print(f"[NOTIFICAÇÃO] Para: {destinatario} | Mensagem: {mensagem}", flush=True)

    return jsonify({"status": "registrada"}), 201


if __name__ == "__main__":
    # 0.0.0.0 = aceita conexões vindas de fora do computador/container
    # (no Docker, o Orquestrador está em OUTRO container).
    app.run(host="0.0.0.0", port=5002, debug=True)
