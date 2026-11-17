"""
Aula 2 / Exercício 3.3 — Benchmark: RDS (ILIKE) × DynamoDB (Scan com contains) × pgvector.

Pergunta do agente: "cadeira ergonômica para dor lombar".
Mede a latência média (time.perf_counter) de 10 consultas em cada opção e mostra o top 3 (qualidade).

O DynamoDB não tem busca por texto nativa: o script cria uma tabela temporária com os mesmos produtos
(`<dynamodb_table>-bench`), faz Scan com contains() e a APAGA no final.

Uso (CloudShell, depois do `qc indexa`):
    python benchmark_busca.py "cadeira ergonômica para dor lombar"
"""

import os
import statistics
import sys
import time

import boto3
import psycopg
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE_MODELO = os.environ.get("FASTEMBED_CACHE", "/tmp/fastembed")
N = 10


def connection_string():
    secret_id = os.environ.get("SECRET_ID") or sys.exit("SECRET_ID vazio. Rode o source do qc.sh.")
    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]


def medir(fn):
    """Roda N vezes, devolve (média_ms, mínimo_ms, máximo_ms, último_resultado)."""
    tempos, resultado = [], None
    for _ in range(N):
        t0 = time.perf_counter()
        resultado = fn()
        tempos.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(tempos), min(tempos), max(tempos), resultado


def main():
    consulta = (sys.argv[1] if len(sys.argv) > 1 else "cadeira ergonômica para dor lombar").strip()
    palavras = [p for p in consulta.lower().split() if len(p) > 3]
    tabela_base = os.environ.get("DDB_TABLE") or sys.exit("DDB_TABLE vazio (nome da tabela de reviews do lab).")
    tabela_bench = f"{tabela_base}-bench"

    with psycopg.connect(connection_string(), connect_timeout=15, autocommit=True) as conn:
        register_vector(conn)
        produtos = conn.execute("SELECT id, nome, descricao, categoria, preco FROM produtos_vetor ORDER BY id").fetchall()

        # (a) RDS PostgreSQL com ILIKE '%palavra%'
        def rds_ilike():
            cond = " OR ".join(["nome ILIKE %s OR descricao ILIKE %s"] * len(palavras))
            args = [x for p in palavras for x in (f"%{p}%", f"%{p}%")]
            return [r[0] for r in conn.execute(f"SELECT nome FROM produtos_vetor WHERE {cond} ORDER BY id LIMIT 3", args)]

        # (c) pgvector (o embedding da consulta é gerado dentro da medição: é o custo real de cada pergunta)
        modelo = TextEmbedding(model_name=MODELO, cache_dir=CACHE_MODELO)
        next(modelo.embed(["aquecimento"]))  # aquece o modelo, fora da medição

        def pgvector():
            vetor = next(modelo.embed([consulta]))
            return [r[0] for r in conn.execute("SELECT nome FROM produtos_vetor ORDER BY embedding <=> %s LIMIT 3", (vetor,))]

        # (b) DynamoDB: tabela temporária + Scan com contains()
        ddb = boto3.client("dynamodb")
        ddb.create_table(
            TableName=tabela_bench,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "N"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.get_waiter("table_exists").wait(TableName=tabela_bench)
        try:
            for i, nome, desc, cat, preco in produtos:
                ddb.put_item(TableName=tabela_bench, Item={
                    "id": {"N": str(i)}, "nome": {"S": nome}, "descricao": {"S": desc or ""},
                    "categoria": {"S": cat}, "preco": {"N": str(preco)}})

            consumo = {"rcu": 0.0, "lidos": 0}

            def ddb_scan():
                achados, kwargs = [], {}
                filtro = " OR ".join(f"contains(nome, :p{i}) OR contains(descricao, :p{i})" for i in range(len(palavras)))
                valores = {f":p{i}": {"S": p} for i, p in enumerate(palavras)}
                while True:
                    r = ddb.scan(TableName=tabela_bench, FilterExpression=filtro,
                                 ExpressionAttributeValues=valores, ReturnConsumedCapacity="TOTAL", **kwargs)
                    achados += [i["nome"]["S"] for i in r["Items"]]
                    consumo["rcu"] = r["ConsumedCapacity"]["CapacityUnits"]
                    consumo["lidos"] = r["ScannedCount"]
                    if "LastEvaluatedKey" not in r:
                        return achados[:3]
                    kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]

            resultados = {}
            for nome_modo, fn in (("RDS ILIKE", rds_ilike), ("DynamoDB Scan contains()", ddb_scan), ("pgvector (sentido)", pgvector)):
                resultados[nome_modo] = medir(fn)

            print(f'\nConsulta: "{consulta}"  (palavras usadas nas buscas por texto: {palavras})')
            print(f"{'Modo':28s} {'média ms':>9s} {'mín ms':>8s} {'máx ms':>8s}  top 3")
            for modo, (media, mn, mx, res) in resultados.items():
                top = " | ".join(res) if res else "(nenhum resultado)"
                print(f"{modo:28s} {media:9.1f} {mn:8.1f} {mx:8.1f}  {top}")
            print(f"\nDynamoDB Scan: leu {consumo['lidos']} itens e consumiu {consumo['rcu']} RCU por consulta "
                  f"(a tabela do lab tem {len(produtos)} itens; o custo cresce com o tamanho da tabela inteira)")
        finally:
            ddb.delete_table(TableName=tabela_bench)
            print(f"\n(tabela temporária {tabela_bench} apagada)")


if __name__ == "__main__":
    main()
