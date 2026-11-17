"""
Aula 2 / Exercício 3.1 — Busca híbrida: vetor (pgvector) + full-text (tsvector) no mesmo PostgreSQL.

Roda as 3 buscas (palavra, vetor, híbrida com Reciprocal Rank Fusion) e imprime o top 3 de cada.
RRF: score = soma de 1 / (60 + posição) entre os rankings.

Uso (no CloudShell, depois do `source qc.sh` e do `qc indexa`):
    python buscar_hibrido.py "Dell Inspiron" "algo para trabalhar em pé" "presente para quem gosta de correr"

Variável de ambiente:
    SECRET_ID — segredo com a connection string (o `source qc.sh` exporta)
"""

import os
import sys

import boto3
import psycopg
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE_MODELO = os.environ.get("FASTEMBED_CACHE", "/tmp/fastembed")
K_RRF = 60
LIMITE = 10  # candidatos por ranking antes de fundir
TOP = 3      # quantos mostrar

DDL = [
    # coluna full-text em português, gerada a partir de nome + descrição (exercício 3.1, passo 1)
    """ALTER TABLE produtos_vetor ADD COLUMN IF NOT EXISTS tsv tsvector
       GENERATED ALWAYS AS (to_tsvector('portuguese', nome || ' ' || coalesce(descricao,''))) STORED""",
    "CREATE INDEX IF NOT EXISTS produtos_tsv ON produtos_vetor USING gin (tsv)",
]

SQL_PALAVRA = """
SELECT id FROM produtos_vetor
WHERE tsv @@ plainto_tsquery('portuguese', %s)
ORDER BY ts_rank(tsv, plainto_tsquery('portuguese', %s)) DESC
LIMIT %s
"""
SQL_VETOR = "SELECT id FROM produtos_vetor ORDER BY embedding <=> %s LIMIT %s"


def connection_string():
    secret_id = os.environ.get("SECRET_ID") or sys.exit("SECRET_ID vazio. Rode o source do qc.sh.")
    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]


def rrf(*rankings):
    """Funde listas de ids (já ordenadas) com Reciprocal Rank Fusion."""
    pontos = {}
    for ranking in rankings:
        for posicao, id_ in enumerate(ranking, start=1):
            pontos[id_] = pontos.get(id_, 0.0) + 1.0 / (K_RRF + posicao)
    return sorted(pontos, key=pontos.get, reverse=True)


def nomes(conn, ids):
    if not ids:
        return {}
    linhas = conn.execute("SELECT id, nome, preco FROM produtos_vetor WHERE id = ANY(%s)", (ids,)).fetchall()
    return {i: (n, p) for i, n, p in linhas}


def mostrar(titulo, ids, info):
    print(f"  {titulo}")
    if not ids:
        print("     (nenhum resultado)")
    for pos, i in enumerate(ids[:TOP], start=1):
        nome, preco = info[i]
        print(f"     {pos}. {nome}  (R$ {preco})")


def main():
    if len(sys.argv) < 2:
        sys.exit('Uso: python buscar_hibrido.py "consulta 1" "consulta 2" ...')
    with psycopg.connect(connection_string(), connect_timeout=15, autocommit=True) as conn:
        for comando in DDL:
            conn.execute(comando)
        register_vector(conn)
        modelo = TextEmbedding(model_name=MODELO, cache_dir=CACHE_MODELO)
        for consulta in sys.argv[1:]:
            vetor = next(modelo.embed([consulta]))
            por_palavra = [r[0] for r in conn.execute(SQL_PALAVRA, (consulta, consulta, LIMITE))]
            por_vetor = [r[0] for r in conn.execute(SQL_VETOR, (vetor, LIMITE))]
            hibrido = rrf(por_palavra, por_vetor)
            info = nomes(conn, list(set(por_palavra + por_vetor)))
            print(f'\nConsulta: "{consulta}"')
            mostrar("Palavra (full-text, português)", por_palavra, info)
            mostrar("Vetor (pgvector, sentido)", por_vetor, info)
            mostrar("Híbrido (RRF = Σ 1/(60+posição))", hibrido, info)


if __name__ == "__main__":
    main()
