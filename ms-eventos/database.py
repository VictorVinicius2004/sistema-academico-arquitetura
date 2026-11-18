import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "eventos.db"


def conectar():
    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabela():
    conexao = conectar()

    conexao.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            data TEXT NOT NULL,
            local TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            organizador_id INTEGER NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()


if __name__ == "__main__":
    criar_tabela()
    print("Banco de dados criado com sucesso!")