import os
from functools import wraps
import jwt
from flask import request, jsonify, g

JWT_SECRET = os.getenv("JWT_SECRET", "40028922funkdoyudiquevaidaplaystation3")
ALGORITMO = "HS256"


def extrair_e_validar_token(auth_header: str):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Falta Token ou errado")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Token vazio")

    payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITMO])

    # Garante compatibilidade com a regra do PyJWT (sub como texto)
    if "sub" not in payload or not isinstance(payload["sub"], str):
        raise ValueError("Token inválido")

    return payload


def requer_papel(*papeis_permitidos):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            try:
                payload = extrair_e_validar_token(auth_header)
            except jwt.ExpiredSignatureError:
                return jsonify({"erro": "Token expirado"}), 401
            except (jwt.InvalidTokenError, ValueError) as exc:
                return jsonify({"erro": f"Não autorizado: {str(exc)}"}), 401

            g.usuario = payload

            if papeis_permitidos and payload.get("papel") not in papeis_permitidos:
                return jsonify({"erro": "Acesso negado"}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator