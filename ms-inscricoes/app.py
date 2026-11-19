import os
import sys
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g

#importando o comum/auth.py 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for path in (BASE_DIR, ROOT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from comum.auth import requer_papel

app = Flask(__name__)
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "inscricoes.db"))

#criando a conexão e criação da tabela isolada 

def get_db():
    ponte = sqlite3.connect(DB_PATH)
    ponte.row_factory = sqlite3.Row
    return ponte

def init_db():
    with get_db() as ponte:
        ponte.execute(
            """
            CREATE TABLE IF NOT EXISTS inscricoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ativa',
                presente INTEGER NOT NULL DEFAULT 0,
                data TEXT NOT NULL
            )
            """
        )
        ponte.commit()

#formatação do retorno da resposta 

def formatar_inscricao(linha):
    return {
        "id": linha["id"],
        "evento_id": linha["evento_id"],
        "usuario_id": linha["usuario_id"],
        "status": linha["status"],
        "presente": bool(linha["presente"]),
        "data": linha["data"],
    }

@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "ms-inscricoes"}), 200

@app.post("/inscricoes")
@requer_papel("participante")
def criar_inscricao():
    dados = request.get_json(silent=True) or {}
    evento_id = dados.get("evento_id")
    usuario_id = dados.get("usuario_id")

    if evento_id is None or usuario_id is None:
        return jsonify({"erro": "evento_id e usuario_id são obrigatórios"}), 400

    if not isinstance(evento_id, int) or not isinstance(usuario_id, int):
        return jsonify({"erro": "evento_id e usuario_id devem ser numéricos"}), 400

#confere se o id do usuario do corpo é o mesmo dono do token

    if usuario_id != int(g.usuario["sub"]):
        return jsonify({"erro": "Acesso negado: usuario_id diferente do token"}), 403

    with get_db() as ponte:
        #bloqueia se já tiver inscrição ativa no mesmo evento
        ativa = ponte.execute(
            """
            SELECT id FROM inscricoes
            WHERE evento_id = ? AND usuario_id = ? AND status = 'ativa'
            """,
            (evento_id, usuario_id),
        ).fetchone()

        if ativa:
            return jsonify({"erro": "participante já inscrito neste evento"}), 409

        agora = datetime.now(timezone.utc).isoformat()
        cursor = ponte.execute(
            """
            INSERT INTO inscricoes (evento_id, usuario_id, status, presente, data)
            VALUES (?, ?, 'ativa', 0, ?)
            """,
            (evento_id, usuario_id, agora),
        )
        ponte.commit()

        nova = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return jsonify(formatar_inscricao(nova)), 201


@app.get("/inscricoes/<int:id>")
@requer_papel("participante", "organizador", "admin")
def detalhar_inscricao(id):
    with get_db() as ponte:
        inscricao = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (id,),
        ).fetchone()

    if not inscricao:
        return jsonify({"erro": "inscrição não encontrada"}), 404


    if g.usuario.get("papel") == "participante":
        if inscricao["usuario_id"] != int(g.usuario["sub"]):
            return jsonify({"erro": "Acesso negado"}), 403

    return jsonify(formatar_inscricao(inscricao)), 200


@app.delete("/inscricoes/<int:id>")
@requer_papel("participante")
def cancelar_inscricao(id):
    with get_db() as ponte:
        inscricao = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (id,),
        ).fetchone()

        if not inscricao:
            return jsonify({"erro": "inscrição não encontrada"}), 404

        if inscricao["usuario_id"] != int(g.usuario["sub"]):
            return jsonify({"erro": "Acesso negado: inscrição de outro participante"}), 403

        if inscricao["status"] == "cancelada":
            return jsonify({"erro": "inscrição já está cancelada"}), 400

        #não apaga a nada, apenas altera o status para cancelada
        ponte.execute(
            "UPDATE inscricoes SET status = 'cancelada' WHERE id = ?",
            (id,),
        )
        ponte.commit()

        atualizada = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (id,),
        ).fetchone()

    return jsonify(formatar_inscricao(atualizada)), 200


@app.get("/inscricoes")
@requer_papel("organizador", "admin")
def listar_inscritos():
    evento_id = request.args.get("evento_id", type=int)
    if evento_id is None:
        return jsonify({"erro": "parâmetro evento_id é obrigatório"}), 400

    with get_db() as ponte:
        linhas = ponte.execute(
            "SELECT * FROM inscricoes WHERE evento_id = ?",
            (evento_id,),
        ).fetchall()

    return jsonify([formatar_inscricao(linha) for linha in linhas]), 200


@app.patch("/inscricoes/<int:id>/presenca")
@requer_papel("organizador")
def registrar_presenca(id):
    with get_db() as ponte:
        inscricao = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (id,),
        ).fetchone()

        if not inscricao:
            return jsonify({"erro": "inscrição não encontrada"}), 404

        if inscricao["status"] == "cancelada":
            return jsonify({"erro": "não é possível registrar presença em inscrição cancelada"}), 400

        ponte.execute(
            "UPDATE inscricoes SET presente = 1 WHERE id = ?",
            (id,),
        )
        ponte.commit()

        atualizada = ponte.execute(
            "SELECT * FROM inscricoes WHERE id = ?",
            (id,),
        ).fetchone()

    return jsonify(formatar_inscricao(atualizada)), 200

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)