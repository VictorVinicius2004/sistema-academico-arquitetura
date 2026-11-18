import os
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
import jwt
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flasgger import Swagger

# Permite importar comum/auth.py tanto rodando localmente quanto no Docker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import requer_papel, JWT_SECRET, ALGORITMO

app = Flask(__name__)
app.config["SWAGGER"] = {
    "title": "EventHub",
    "uiversion": 3,
}
swagger = Swagger(app)

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "identidade.db"))
PAPEIS_VALIDOS = {"admin", "organizador", "participante"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                papel TEXT NOT NULL CHECK (papel IN ('admin', 'organizador', 'participante'))
            )
            """
        )
        # Seed dos 3 perfis com os mesmos IDs do script gerar_token.py (1, 2 e 3)
        usuarios_seed = [
            (1, "Carlos Admin", "admin@ifnmg.edu.br", generate_password_hash("121345"), "admin"),
            (2, "André Organizador", "andre@ifnmg.edu.br", generate_password_hash("andrezinho"), "organizador"),
            (3, "Eric", "eric@ifnmg.edu.br", generate_password_hash("80028922"), "participante"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO usuarios (id, nome, email, senha_hash, papel)
            VALUES (?, ?, ?, ?, ?)
            """,
            usuarios_seed,
        )
        conn.commit()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servico": "identidade"}), 200


@app.post("/auth/login")
def login():
    """
    Autentica um usuário e retorna um token JWT
    ---
    tags:
      - Autenticação
    parameters:
      - in: body
        name: credenciais
        required: true
        schema:
          type: object
          required: [email, senha]
          properties:
            email:
              type: string
              example: ana@aluno.ifnmg.edu.br
            senha:
              type: string
              example: part123
    responses:
      200:
        description: Token JWT gerado com sucesso
      400:
        description: Dados obrigatórios ausentes
      401:
        description: Credenciais inválidas
    """
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not email or not senha:
        return jsonify({"erro": "E-mail e senha são obrigatórios"}), 400

    with get_db() as conn:
        usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()

    if not usuario or not check_password_hash(usuario["senha_hash"], senha):
        return jsonify({"erro": "E-mail ou senha inválidos"}), 401

    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario["id"]),
        "nome": usuario["nome"],
        "email": usuario["email"],
        "papel": usuario["papel"],
        "exp": int((agora + timedelta(hours=24)).timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITMO)

    return jsonify({"token": token}), 200


@app.post("/usuarios")
@requer_papel("admin")
def criar_usuario():
    """
    Cadastra um novo usuário (apenas admin)
    ---
    tags:
      - Usuários
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer <token>
      - in: body
        name: usuario
        required: true
        schema:
          type: object
          required: [nome, email, senha, papel]
          properties:
            nome:
              type: string
              example: João Silva
            email:
              type: string
              example: joao@aluno.ifnmg.edu.br
            senha:
              type: string
              example: senha123
            papel:
              type: string
              enum: [admin, organizador, participante]
    responses:
      201:
        description: Usuário criado
      400:
        description: Dados inválidos
      401:
        description: Token ausente ou inválido
      403:
        description: Acesso restrito ao perfil admin
      409:
        description: E-mail já cadastrado
    """
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""
    papel = (dados.get("papel") or "").strip().lower()

    if not nome or not email or not senha or papel not in PAPEIS_VALIDOS:
        return jsonify({"erro": "Campos nome, email, senha e papel válido são obrigatórios"}), 400

    senha_hash = generate_password_hash(senha)

    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?, ?, ?, ?)",
                (nome, email, senha_hash, papel),
            )
            conn.commit()
            novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"erro": "E-mail já cadastrado"}), 409

    return jsonify({"id": novo_id, "nome": nome, "email": email, "papel": papel}), 201


@app.get("/usuarios")
@requer_papel("admin")
def listar_usuarios():
    """
    Lista todos os usuários cadastrados (apenas admin)
    ---
    tags:
      - Usuários
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer <token>
    responses:
      200:
        description: Lista de usuários
      401:
        description: Token ausente ou inválido
      403:
        description: Acesso restrito ao perfil admin
    """
    with get_db() as conn:
        rows = conn.execute("SELECT id, nome, email, papel FROM usuarios ORDER BY id").fetchall()

    usuarios = [dict(row) for row in rows]
    return jsonify(usuarios), 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)