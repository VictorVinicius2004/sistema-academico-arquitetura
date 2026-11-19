# Orquestrador - porta 5003
# Faz o fluxo da inscricao: busca o evento, cria a inscricao, notifica e confirma.
# Nao tem banco, quem guarda a inscricao e o ms-inscricoes.
#
# Com SIMULADO=1 ele finge as respostas do ms-eventos e do ms-inscricoes
# (usei pra testar antes dos servicos ficarem prontos). A notificacao e sempre a real.

import os
import sys

import requests
from flask import Flask, request, jsonify, g
from flasgger import Swagger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import requer_papel  # noqa: E402

app = Flask(__name__)
app.config["SWAGGER"] = {"title": "EventHub - Orquestrador", "uiversion": 3}
Swagger(app)

# no docker essas variaveis apontam pro nome do servico (ex: http://ms-eventos:5004)
URL_EVENTOS = os.getenv("URL_EVENTOS", "http://localhost:5004")
URL_INSCRICOES = os.getenv("URL_INSCRICOES", "http://localhost:5005")
URL_NOTIFICACAO = os.getenv("URL_NOTIFICACAO", "http://localhost:5002")

SIMULADO = os.getenv("SIMULADO") == "1"
TIMEOUT = 3  # segundos


class ServicoIndisponivel(Exception):
    pass


def cabecalho_token():
    # repassa o token do participante, porque cada servico valida o token tambem
    return {"Authorization": request.headers["Authorization"]}


def chamar(metodo, url, nome_servico, **kwargs):
    # retorna (status, json). se der erro de rede ou nao vier json, levanta ServicoIndisponivel
    try:
        r = requests.request(metodo, url, headers=cabecalho_token(), timeout=TIMEOUT, **kwargs)
        return r.status_code, r.json()
    except (requests.RequestException, ValueError) as exc:
        raise ServicoIndisponivel(nome_servico) from exc


def buscar_evento(evento_id):
    if SIMULADO:
        # 7 = aprovado, 8 = pendente, 9 = aprovado mas ja inscrito (409), outro = 404
        if evento_id in (7, 8, 9):
            return 200, {"id": evento_id, "titulo": "Semana de SI", "descricao": "...",
                         "data": "2026-12-01", "local": "Auditório",
                         "status": "pendente" if evento_id == 8 else "aprovado",
                         "organizador_id": 2}
        return 404, {"erro": "evento não encontrado"}

    return chamar("GET", f"{URL_EVENTOS}/eventos/{evento_id}", "ms-eventos")


def criar_inscricao(evento_id, usuario_id):
    if SIMULADO:
        if evento_id == 9:
            return 409, {"erro": "participante já inscrito neste evento"}
        return 201, {"id": 15, "evento_id": evento_id, "usuario_id": usuario_id,
                     "status": "ativa", "presente": False}

    return chamar("POST", f"{URL_INSCRICOES}/inscricoes", "ms-inscricoes",
                  json={"evento_id": evento_id, "usuario_id": usuario_id})


def notificar(destinatario, mensagem):
    # se a notificacao falhar so retorna False, a inscricao continua valendo (ADR-004)
    try:
        status, _ = chamar("POST", f"{URL_NOTIFICACAO}/notificacoes", "notificacao",
                           json={"destinatario": destinatario, "mensagem": mensagem})
        return status == 201
    except ServicoIndisponivel:
        return False


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "orquestrador", "simulado": SIMULADO}), 200


@app.post("/inscricoes")
@requer_papel("participante")
def inscrever():
    """
    Inscrição orquestrada: confere o evento, grava a inscrição e notifica o participante
    ---
    tags:
      - Orquestrador
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer <token de participante>
      - in: body
        name: inscricao
        required: true
        schema:
          type: object
          required: [evento_id]
          properties:
            evento_id:
              type: integer
              example: 7
    responses:
      201:
        description: Inscrição confirmada (notificado=false se a Notificação falhou)
        schema:
          type: object
          properties:
            inscricao_id:
              type: integer
              example: 15
            evento_id:
              type: integer
              example: 7
            status:
              type: string
              example: confirmada
            notificado:
              type: boolean
              example: true
      400:
        description: Faltou evento_id ou o evento não está aprovado
      401:
        description: Token ausente, inválido ou expirado
      403:
        description: Só participantes podem se inscrever
      404:
        description: Evento não encontrado
      409:
        description: Participante já inscrito neste evento
      503:
        description: ms-eventos ou ms-inscricoes fora do ar
    """
    dados = request.get_json(silent=True) or {}
    evento_id = dados.get("evento_id")
    # True/False tambem passam no isinstance(int), por isso o segundo teste
    if not isinstance(evento_id, int) or isinstance(evento_id, bool):
        return jsonify({"erro": "evento_id (número) é obrigatório"}), 400

    # usuario e email vem do token, pra ninguem inscrever outra pessoa
    usuario_id = int(g.usuario["sub"])
    email = g.usuario["email"]

    try:
        # 1. evento existe e esta aprovado?
        status, evento = buscar_evento(evento_id)
        if status == 404:
            return jsonify({"erro": "evento não encontrado"}), 404
        if status != 200:
            raise ServicoIndisponivel("ms-eventos")
        if evento.get("status") != "aprovado":
            return jsonify({"erro": "evento não aprovado"}), 400

        # 2. cria a inscricao
        status, inscricao = criar_inscricao(evento_id, usuario_id)
        if status == 409:
            return jsonify({"erro": "participante já inscrito neste evento"}), 409
        if status != 201:
            raise ServicoIndisponivel("ms-inscricoes")

    except ServicoIndisponivel as exc:
        return jsonify({"erro": f"serviço indisponível: {exc}"}), 503

    # 3. notifica (se falhar, notificado = False)
    titulo = evento.get("titulo", f"#{evento_id}")
    notificado = notificar(email, f"Inscrição confirmada no evento {titulo}")

    # 4. confirma
    return jsonify({
        "inscricao_id": inscricao["id"],
        "evento_id": evento_id,
        "status": "confirmada",
        "notificado": notificado,
    }), 201


if __name__ == "__main__":
    print(f"Orquestrador iniciando (SIMULADO={'sim' if SIMULADO else 'não'})", flush=True)
    app.run(host="0.0.0.0", port=5003, debug=True)
