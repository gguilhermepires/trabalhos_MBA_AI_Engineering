# Entrega Aula 03 — Serverless & Containers (Quantum Commerce)

Documento principal: **`entrega-grupo-aula03.md`** (respostas de N1, N2 e do bônus N3).

## Conteúdo do ZIP

| Caminho | O que é |
|---|---|
| `entrega-grupo-aula03.md` | Respostas de todos os exercícios, com links para as evidências |
| `canvas-compute.md` | Canvas de compute da QC (2.1), 5 cargas com custo da calculadora AWS |
| `function/v3-frete/` | Código da Lambda: catálogo (S3) + `GET /frete` (2.2) + filtro `preco_max` (3.1) |
| `terraform/observabilidade.tf` | Alarme CloudWatch sobre `Errors` da Lambda (2.3c) |
| `terraform/containers-evolucao.tf` | Job agendado, sizing, segredo e auto scaling do Fargate (3.4); complementa o `containers.tf` do lab |
| `evidencias/` | Uma pasta por exercício: saídas da AWS CLI, `ab`, logs, prints e a calculadora |

## Como rodar o que foi entregue

Pré-requisitos: Learner Lab iniciado e o Terraform do lab aplicado (`lab/terraform`).

```bash
# Função (v3): empacotar e publicar na Lambda do lab
cd function/v3-frete && zip -q ../v3.zip lambda_function.py
aws lambda update-function-code --function-name <FUNCTION_NAME> --zip-file fileb://../v3.zip

# Testes (troque pela sua Function URL)
curl "${FUNCTION_URL}frete?origem=01001000&destino=20040020&peso=2.5"
curl "${FUNCTION_URL}produtos?categoria=moveis&preco_max=1500"

# Terraform: copiar os .tf para lab/terraform e rodar plan/apply
cp ../terraform/*.tf <caminho-do-lab>/terraform/ && terraform plan
```

## Avisos honestos sobre as evidências

- O **`terraform plan`** do exercício 3.3 é o resultado **esperado**, não uma saída real (o Terraform não foi executado; o desvio foi demonstrado pela AWS CLI).
- Os `.tf` de `terraform/` **não foram aplicados com Terraform**; os recursos equivalentes foram exercitados pela AWS CLI e depois removidos.
- Os benchmarks (3.2) rodaram de um Mac, **não do CloudShell**, então as latências absolutas incluem rede.
- A Function URL pública da `demo-estoque` (3.3) **não foi criada** (bloqueada pelo modo automático do Claude Code usado no trabalho).
- O `Dockerfile` corrigido (1.4) foi buildado e testado localmente (`evidencias/1.4-dockerfile/`).
- Os recursos criados para os exercícios foram apagados (`evidencias/LIMPEZA-executada.txt`).
