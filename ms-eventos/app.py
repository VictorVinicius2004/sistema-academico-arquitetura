
import sys
from pathlib import Path

from flask import Flask, request, jsonify, g

# Localiza a raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO))

from database import conectar, criar_tabela
from comum.auth import requer_papel


app = Flask(__name__)

# Garante que a tabela de eventos exista
criar_tabela()


@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "mensagem": "Microsserviço de Eventos funcionando!"
    }), 200


# CADASTRAR EVENTO
@app.route("/eventos", methods=["POST"])
@requer_papel("organizador")
def cadastrar_evento():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados do evento em formato JSON"}), 400

    campos_obrigatorios = [
        "titulo",
        "descricao",
        "data",
        "local"
    ]

    for campo in campos_obrigatorios:
        if not dados.get(campo):
            return jsonify({
                "erro": f"O campo {campo} é obrigatório"
            }), 400

    # O ID do organizador vem do token JWT
    try:
        organizador_id = int(g.usuario["sub"])
    except (ValueError, TypeError):
        return jsonify({"erro": "Identificação do organizador inválida"}), 401

    conexao = conectar()

    cursor = conexao.execute("""
        INSERT INTO eventos
        (titulo, descricao, data, local, organizador_id)
        VALUES (?, ?, ?, ?, ?)
    """, (
        dados["titulo"],
        dados["descricao"],
        dados["data"],
        dados["local"],
        organizador_id
    ))

    conexao.commit()
    evento_id = cursor.lastrowid
    conexao.close()

    return jsonify({
        "mensagem": "Evento cadastrado com sucesso!",
        "id": evento_id,
        "status": "pendente"
    }), 201


# LISTAR EVENTOS APROVADOS
@app.route("/eventos", methods=["GET"])
@requer_papel()
def listar_eventos():
    conexao = conectar()

    eventos = conexao.execute("""
        SELECT * FROM eventos
        WHERE status = 'aprovado'
        ORDER BY data
    """).fetchall()

    conexao.close()

    lista_eventos = [dict(evento) for evento in eventos]

    return jsonify(lista_eventos), 200


# BUSCAR EVENTO POR ID
@app.route("/eventos/<int:id>", methods=["GET"])
@requer_papel()
def buscar_evento(id):
    conexao = conectar()

    evento = conexao.execute(
        "SELECT * FROM eventos WHERE id = ?",
        (id,)
    ).fetchone()

    conexao.close()

    if evento is None:
        return jsonify({
            "erro": "evento não encontrado"
        }), 404

    return jsonify(dict(evento)), 200


# EDITAR EVENTO
@app.route("/eventos/<int:id>", methods=["PUT"])
@requer_papel("organizador")
def editar_evento(id):
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados para edição em formato JSON"}), 400

    campos_obrigatorios = [
        "titulo",
        "descricao",
        "data",
        "local"
    ]

    for campo in campos_obrigatorios:
        if not dados.get(campo):
            return jsonify({
                "erro": f"O campo {campo} é obrigatório"
            }), 400

    try:
        organizador_id = int(g.usuario["sub"])
    except (ValueError, TypeError):
        return jsonify({"erro": "Identificação do organizador inválida"}), 401

    conexao = conectar()

    evento = conexao.execute(
        "SELECT * FROM eventos WHERE id = ?",
        (id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        return jsonify({"erro": "evento não encontrado"}), 404

    # Verifica se o evento pertence ao organizador autenticado
    if evento["organizador_id"] != organizador_id:
        conexao.close()
        return jsonify({"erro": "Você não pode editar eventos de outro organizador"}), 403

    conexao.execute("""
        UPDATE eventos
        SET titulo = ?, descricao = ?, data = ?, local = ?
        WHERE id = ?
    """, (
        dados["titulo"],
        dados["descricao"],
        dados["data"],
        dados["local"],
        id
    ))

    conexao.commit()
    conexao.close()

    return jsonify({
        "mensagem": "Evento atualizado com sucesso!"
    }), 200


# APROVAR EVENTO
@app.route("/eventos/<int:id>/aprovar", methods=["PATCH"])
@requer_papel("admin")
def aprovar_evento(id):
    conexao = conectar()

    evento = conexao.execute(
        "SELECT * FROM eventos WHERE id = ?",
        (id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        return jsonify({"erro": "evento não encontrado"}), 404

    conexao.execute(
        "UPDATE eventos SET status = 'aprovado' WHERE id = ?",
        (id,)
    )

    conexao.commit()
    conexao.close()

    return jsonify({
        "mensagem": "Evento aprovado com sucesso!"
    }), 200


# RELATÓRIO DE EVENTOS
@app.route("/eventos/relatorio", methods=["GET"])
@requer_papel("admin")
def relatorio_eventos():
    conexao = conectar()

    resultados = conexao.execute("""
        SELECT status, COUNT(*) AS quantidade
        FROM eventos
        GROUP BY status
    """).fetchall()

    conexao.close()

    relatorio = {
        "pendente": 0,
        "aprovado": 0,
        "rejeitado": 0
    }

    for resultado in resultados:
        relatorio[resultado["status"]] = resultado["quantidade"]

    return jsonify(relatorio), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)