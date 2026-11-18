import os
import sys
from datetime import datetime, timedelta, timezone
import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from comum.auth import JWT_SECRET, ALGORITMO

perfis = [
    {"sub": "1", "nome": "Carlos Admin", "email": "admin@ifnmg.edu.br", "papel": "admin"},
    {"sub": "2", "nome": "André Organizador", "email": "andre@ifnmg.edu.br", "papel": "organizador"},
    {"sub": "3", "nome": "Eric", "email": "eric@ifnmg.edu.br", "papel": "participante"},
]

exp = int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
for u in perfis:
    token = jwt.encode({**u, "exp": exp}, JWT_SECRET, algorithm=ALGORITMO)
    print(f"{u['papel'].upper()} (sub={u['sub']}):\n{token}\n")