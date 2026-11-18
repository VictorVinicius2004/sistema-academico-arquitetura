
from flask import Flask, request, jsonify

from database import conectar, criar_tabela

app = Flask(__name__)

criar_tabela()


@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "mensagem": "Microsserviço de Eventos funcionando!"
    })


@app.route("/eventos", methods=["POST"])
def cadastrar_evento():
    dados = request.get_json()

    if not dados:
        return jsonify({"erro": "Envie os dados do evento"}), 400

    campos_obrigatorios = [
        "titulo",
        "descricao",
        "data",
        "local",
        "organizador_id"
    ]

    for campo in campos_obrigatorios:
        if campo not in dados or not dados[campo]:
            return jsonify({
                "erro": f"O campo {campo} é obrigatório"
            }), 400

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
        dados["organizador_id"]
    ))

    conexao.commit()

    evento_id = cursor.lastrowid
    conexao.close()

    return jsonify({
        "mensagem": "Evento cadastrado com sucesso!",
        "id": evento_id,
        "status": "pendente"
    }), 201


@app.route("/eventos", methods=["GET"])
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

@app.route("/eventos/<int:id>", methods=["GET"])
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


@app.route("/eventos/<int:id>", methods=["PUT"])
def editar_evento(id):
    dados = request.get_json()

    if not dados:
        return jsonify({"erro": "Envie os dados para edição"}), 400

    campos_obrigatorios = [
        "titulo",
        "descricao",
        "data",
        "local"
    ]

    for campo in campos_obrigatorios:
        if campo not in dados or not dados[campo]:
            return jsonify({
                "erro": f"O campo {campo} é obrigatório"
            }), 400

    conexao = conectar()

    evento = conexao.execute(
        "SELECT * FROM eventos WHERE id = ?",
        (id,)
    ).fetchone()

    if evento is None:
        conexao.close()
        return jsonify({"erro": "evento não encontrado"}), 404

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


@app.route("/eventos/<int:id>/aprovar", methods=["PATCH"])
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


@app.route("/eventos/relatorio", methods=["GET"])
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