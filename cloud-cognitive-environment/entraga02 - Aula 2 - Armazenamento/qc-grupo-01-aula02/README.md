# Entrega 02 — Aula 02 (Storage & Bancos de Dados) — Grupo 01

Conteúdo deste ZIP:

- `entrega-grupo-aula02.md`: documento principal (N1, N2, N3 e reflexão), com a execução do lab.
- `canvas-decisao.md`: o canvas de decisão dos 9 domínios da QC (N2, Ex. 2.1).
- `diagramas/arquitetura-qc-aula02.png`: diagrama da camada de dados (fonte em `.svg`).
- `terraform/`: o código do lab (S3, RDS PostgreSQL 16, Secrets Manager, DynamoDB, Athena), executado **sem alterações**.
- `scripts/`: `buscar_hibrido.py` (Ex. 3.1, vetor + full-text com RRF) e `benchmark_busca.py` (Ex. 3.3).
- `evidencias/`: capturas de tela de cada passo do lab e do console AWS; `evidencias/logs/` guarda a saída de texto de cada comando.

## Como foi executado (AWS Learner Lab, AWS CloudShell, `us-east-1`)

```bash
cd ~/aie-cloud/aulas/02-storage-bancos/lab/terraform
export PATH="$HOME/bin:$PATH"
export DB_PASSWORD=$(openssl rand -hex 16)        # gerada na hora; não fica em arquivo
terraform init
terraform apply -auto-approve -var="db_password=$DB_PASSWORD"

source ~/aie-cloud/aulas/02-storage-bancos/lab/qc.sh
qc carga catalogo ; qc athena "..."               # Lab 1
qc lake gera ; qc lake cura ; qc lake compara     # Lab 1B
qc carga produtos ; qc sql "..."                  # Lab 2
qc carga reviews                                  # Lab 3A
qc indexa ; qc busca "..."                        # Lab 3B

# (o qc instala as dependências sozinho, em /tmp/venv-qc)
python buscar_hibrido.py "Dell Inspiron" "algo para trabalhar em pé" "presente para quem gosta de correr"   # Ex. 3.1
DDB_TABLE=<tabela-de-reviews> python benchmark_busca.py "cadeira ergonômica para dor lombar"                 # Ex. 3.3

terraform destroy -auto-approve -var="db_password=$DB_PASSWORD"   # sempre ao final
```

Os dois scripts leem a connection string do **Secrets Manager** (variável `SECRET_ID`, exportada pelo `source qc.sh`); nenhum segredo está no código.
O `benchmark_busca.py` cria uma tabela temporária no DynamoDB (`<tabela>-bench`) e a apaga no final.

Nenhum segredo está no código. Não inclua `terraform.tfstate*`, `.terraform/`, `.env` nem `*.pem` no ZIP.
