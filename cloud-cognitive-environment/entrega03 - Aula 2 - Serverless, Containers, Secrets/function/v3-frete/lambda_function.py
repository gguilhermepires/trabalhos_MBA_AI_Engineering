"""
Lambda HTTP da Quantum Commerce — versão v3 (N2.2): catálogo no S3 + cálculo de frete.

Rotas novas:
    GET /produtos?categoria=moveis&preco_max=1500  → filtro por preço máximo (N3.1)
    GET /frete?origem=01001000&destino=20040020&peso=2.5  → {valor_brs, prazo_dias, ...}

Lê catalogo/produtos.csv do bucket S3 desta aula. SEM credenciais no código:
o boto3 usa a credencial temporária da execution role da função (no Learner
Lab, a LabRole), entregue pela própria Lambda em variáveis de ambiente.

Variáveis de ambiente (configuradas pelo Terraform):
    BUCKET_NAME — bucket do catálogo
    CSV_KEY     — chave do CSV (padrão: catalogo/produtos.csv)
"""
import csv
import json
import logging
import os

import boto3  # já vem no runtime Python da Lambda — não precisa empacotar

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET = os.environ["BUCKET_NAME"]
CSV_KEY = os.environ.get("CSV_KEY", "catalogo/produtos.csv")

# Cliente criado FORA do handler: reaproveitado entre invocações "quentes"
_s3 = boto3.client("s3")


def resposta(corpo: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(corpo, ensure_ascii=False),
    }


def carregar_produtos():
    """Baixa o CSV do S3 e converte em lista de dicts."""
    obj = _s3.get_object(Bucket=BUCKET, Key=CSV_KEY)
    rows = list(csv.DictReader(obj["Body"].read().decode("utf-8").splitlines()))
    for r in rows:
        r["id"] = int(r["id"])
        r["preco"] = float(r["preco"])
        r["estoque"] = int(r["estoque"])
    return rows


def listar_produtos(params: dict) -> dict:
    """GET /produtos?categoria=moveis&nome=cadeira (no Lab 2: &preco_max=1500)"""
    logger.info("Endpoint /produtos chamado")
    try:
        produtos = carregar_produtos()
    except Exception as e:  # noqa: BLE001 — devolve o erro em JSON para o lab
        logger.exception("Falha ao carregar produtos do S3")
        return resposta({"erro": f"falha ao acessar o S3: {e!s}"}, 500)

    categoria = (params.get("categoria") or "").lower().strip()
    nome = (params.get("nome") or "").lower().strip()

    resultado = produtos
    if categoria:
        resultado = [p for p in resultado if p["categoria"].lower() == categoria]
    if nome:
        resultado = [p for p in resultado if nome in p["nome"].lower()]
    preco_max = (params.get("preco_max") or "").replace(",", ".").strip()
    if preco_max:
        try:
            limite = float(preco_max)
        except ValueError:
            return resposta({"erro": "preco_max deve ser um número"}, 400)
        resultado = [p for p in resultado if p["preco"] <= limite]
    return resposta({"total": len(resultado), "produtos": resultado})


# ---------------------------------------------------------------------------
# Tool 2: cálculo de frete (determinístico, sem estado, sem S3)
# Faixas pela região do CEP (1º dígito): mesma região, vizinha ou distante.
# ---------------------------------------------------------------------------
PESO_MIN_KG, PESO_MAX_KG = 0.1, 30.0
FAIXAS = {  # nome: (base R$, R$ por kg, prazo em dias)
    "mesma_regiao": (12.00, 3.00, 2),
    "regiao_vizinha": (22.00, 4.00, 4),
    "regiao_distante": (35.00, 5.00, 7),
}


def _cep(valor):
    """Aceita 01001-000 ou 01001000; devolve 8 dígitos ou None."""
    digitos = "".join(c for c in (valor or "") if c.isdigit())
    return digitos if len(digitos) == 8 else None


def calcular_frete(params: dict) -> dict:
    """GET /frete?origem=01001000&destino=20040020&peso=2.5"""
    origem, destino = _cep(params.get("origem")), _cep(params.get("destino"))
    if not origem or not destino:
        return resposta({"erro": "origem e destino devem ser CEPs com 8 dígitos"}, 400)
    try:
        peso = float((params.get("peso") or "").replace(",", "."))
    except ValueError:
        return resposta({"erro": "peso deve ser um número em kg"}, 400)
    if not PESO_MIN_KG <= peso <= PESO_MAX_KG:
        return resposta({"erro": f"peso deve estar entre {PESO_MIN_KG} e {PESO_MAX_KG} kg"}, 400)

    distancia = abs(int(origem[0]) - int(destino[0]))
    faixa = "mesma_regiao" if distancia == 0 else "regiao_vizinha" if distancia == 1 else "regiao_distante"
    base, por_kg, prazo = FAIXAS[faixa]
    logger.info("frete faixa=%s peso=%s", faixa, peso)
    return resposta({
        "origem": origem, "destino": destino, "peso_kg": peso, "faixa": faixa,
        "valor_brl": round(base + por_kg * peso, 2), "prazo_dias": prazo,
    })


def lambda_handler(event, context):
    caminho = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}

    if caminho == "/health":
        return resposta({"status": "ok", "service": "qc-catalogo", "source": "s3"})
    if caminho in ("/", "/produtos"):
        return listar_produtos(params)
    if caminho == "/frete":
        return calcular_frete(params)
    return resposta({"erro": f"rota {caminho} não existe", "rotas": ["/produtos", "/frete", "/health"]}, 404)
