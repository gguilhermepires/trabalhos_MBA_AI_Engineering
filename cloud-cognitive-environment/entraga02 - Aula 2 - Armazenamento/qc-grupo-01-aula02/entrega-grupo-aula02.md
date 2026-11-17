# Entrega 02 — Aula 2 (Storage & Bancos de Dados na Nuvem) — Grupo 01

**Disciplina:** Cloud & Cognitive Environments
**Professor:** Isaías Silva de Britto
**Turma:** 6AIER
**Data de entrega:** a definir (1 dia antes da Aula 3)

## Grupo

| # | Nome completo | GitHub | E-mail FIAP |
|---|---------------|--------|-------------|
| 1 | Cinara Nubia Silva (RM 379045) | — | rm379045@fiap.com.br |
| 2 | Guilherme Augusto Veiga Pires (RM 379110) | gguilhermepires | rm379110@fiap.com.br |
| 3 | Somario Canuto da Silva (RM 379214) | — | rm379214@fiap.com.br |

## Distribuição do trabalho

> Proposta seguindo o rodízio da Aula 1 (quem fez N1 antes assume N2 ou N3). **O grupo deve confirmar ou ajustar esta tabela antes de entregar.**

| Membro | Nível assumido | Item específico |
|--------|----------------|-----------------|
| Somario Canuto da Silva | 🟢 N1 | Exercícios 1.1–1.4 (storage, tiers, relacional vs NoSQL, Secrets Manager e IAM) |
| Cinara Nubia Silva | 🟡 N2 | Exercícios 2.1–2.3 (matriz de decisão e canvas, plano de migração, particionamento DynamoDB) |
| Guilherme Augusto Veiga Pires | 🔴 N3 (bônus) + reflexão | Exercícios 3.1–3.3 (busca híbrida, data lake, benchmark), execução do lab e reflexão coletiva; revisão final |

> ✅ **Executado de verdade** em 17/11/2026 no AWS Academy Learner Lab (região `us-east-1`), via AWS CloudShell e Terraform (`aulas/02-storage-bancos/lab/terraform`). As capturas de tela e os logs estão em `evidencias/` e são citados no texto. A infraestrutura foi destruída no final (`terraform destroy`).
>
> **Sobre os custos:** os valores em US$ vêm da **AWS Pricing Calculator** (prints em `evidencias/`) ou do **arquivo oficial de preços da AWS** (`pricing.us-east-1.amazonaws.com`, a mesma base da calculadora, em us-east-1, preço on-demand). Onde o texto diz "conta do grupo", o preço unitário é oficial e a multiplicação pelo volume foi feita pelo grupo, com as hipóteses de volume explícitas.

---

## 🟢 Nível 1 — Respostas

### Exercício 1.1 — Tipos de Storage

| Cenário | Tipo | Justificativa |
|---------|------|---------------|
| Hospedar imagens de produtos do e-commerce QC (5M de SKUs) | **Object** (S3) | Volume enorme de arquivos imutáveis, servidos por HTTP/CDN, sem precisar de sistema de arquivos. |
| Disco onde roda o sistema operacional de uma VM de banco | **Block** (EBS) | Precisa de baixa latência e IOPS previsível, atrelado a uma única VM. |
| Pasta compartilhada entre 10 VMs de um time de DevOps | **File** (EFS) | É a única opção montável por várias VMs ao mesmo tempo com semântica de arquivos (`/mnt/dados`). |
| Backup mensal de bancos de dados (retenção 7 anos) | **Object** (S3 Glacier Deep Archive) | Acesso raríssimo e retenção longa: custo por GB mais baixo (≈ US$ 0,00099/GB/mês), com lifecycle automático. |
| Storage de modelos `.pkl` do time de ML para serving | **Object** (S3) | Download por HTTP, versionamento de objeto e permissão por prefixo; os modelos são arquivos inteiros. |
| Dump diário de logs de aplicação para análise futura | **Object** (S3, lifecycle Standard → IA → Glacier) | Escrita em lote, leitura eventual por Athena direto no S3; o lifecycle reduz o custo com o tempo. |

### Exercício 1.2 — Tiers de acesso (cálculo)

Volume: 2 TB = 2.048 GB de logs de compras. Calculadora AWS, us-east-1 (prints: `evidencias/1.2-calculadora-s3-standard-2048gb.jpg` e `evidencias/1.2-calculadora-s3-lifecycle-standard-deeparchive.jpg`).

- **a) 100% em S3 Standard:** 2.048 GB × US$ 0,023 = **US$ 47,10/mês** (≈ US$ 565/ano).
- **b) Lifecycle (30 dias em Standard + Deep Archive depois):** em regime estável, 30/365 do volume fica em Standard (≈ 168,3 GB) e o resto em Deep Archive (≈ 1.879,7 GB). A calculadora dá US$ 3,87 (Standard) + US$ 1,89 (Deep Archive) = **US$ 5,76/mês**. O Deep Archive sai um pouco acima da conta simples (US$ 1,86) porque a calculadora inclui o overhead de metadados por objeto.
- **c) Economia anual:** (US$ 47,10 − US$ 5,76) × 12 = **≈ US$ 496/ano** (−88%).

> O que a conta não mostra: o Deep Archive cobra para **ler** (recuperação em até 12 h), tem **permanência mínima de 180 dias** e cobra por objeto transitado de classe (taxa de lifecycle). Para a QC, com centenas de TB, a mesma decisão vale seis dígitos por ano.

### Exercício 1.3 — Relacional vs NoSQL

| Caso de uso | Banco | Justificativa |
|-------------|-------|---------------|
| Carrinho de compras ativo do usuário | **NoSQL** (DynamoDB) | Acesso por chave (`cliente_id`), esquema variável, escrita frequente e expiração com TTL. |
| Catálogo de produtos (SKU, preço, estoque) | **Relacional** (RDS PostgreSQL) | Esquema fixo, joins com categorias e integridade do estoque (transação). |
| Reviews dos clientes (texto livre + score) | **NoSQL** (DynamoDB) | Documento sem esquema rígido, lido sempre por `produto_id`. |
| "Encontre produtos similares a este" | **Vector DB** (pgvector) | Similaridade semântica entre embeddings, no mesmo banco do catálogo. |
| Histórico de pedidos para faturamento | **Relacional** (RDS PostgreSQL) | Transações ACID e consistência: envolve dinheiro. |
| Sessão do usuário (chave-valor, expira em 30 min) | **NoSQL** (DynamoDB com TTL) | Chave-valor com expiração nativa; ElastiCache só se a latência de sub-milissegundo for crítica. |
| Logs de comportamento de navegação | **NoSQL** ou, melhor, **S3 + Athena** | Volume de bilhões de eventos, escrita append-only, análise em lote (não precisa de índice transacional). |

### Exercício 1.4 — Secrets Manager e IAM

Todos os ARNs abaixo seguem o padrão do lab: segredo `qc-aula02-<sufixo>/postgres`.

| Perfil | Ações IAM no Secrets Manager | Justificativa |
|--------|------------------------------|---------------|
| Você (dev e ops do lab) | `secretsmanager:*` em `arn:aws:secretsmanager:us-east-1:<conta>:secret:qc-aula02-*` | Controle total, mas só do prefixo do projeto. Nunca `Resource: "*"` em produção. |
| Lambda que consulta `t_produtos` | `secretsmanager:GetSecretValue` no ARN do segredo, na **execution role** da função | Só ler, só aquele segredo; sem chaves de acesso dentro da função. |
| Engenheiro de segurança (audita sem ver valores) | `secretsmanager:ListSecrets`, `DescribeSecret`, `GetResourcePolicy` | Vê metadados, rotação e política, **sem** `GetSecretValue`. |
| Pipeline de CI/CD que cria e rotaciona segredos | `CreateSecret`, `PutSecretValue`, `RotateSecret`, `TagResource` no prefixo do projeto, via role assumida por OIDC | Escreve, mas não precisa ler o valor; credencial temporária, sem chave de longa duração. |
| Time de FinOps (custo sem ver valores) | Nenhuma ação no Secrets Manager; `ce:Get*` (Cost Explorer) filtrado pela tag `projeto` | O custo do segredo aparece no Cost Explorer, sem acesso ao serviço. |

Política mínima da Lambda (exemplo):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:us-east-1:<conta>:secret:qc-aula02-*/postgres-*"
  }]
}
```

---

## 🟡 Nível 2 — Respostas + Implementação

### Exercício 2.1 — Modelagem de dados da QC (matriz de decisão + canvas)

Custos em US$/mês, us-east-1, on-demand, com as **hipóteses de volume** da coluna "Hipótese". Preços unitários do arquivo oficial de preços da AWS (a mesma base da calculadora): RDS PostgreSQL `db.m5.large` Multi-AZ US$ 0,356/h e `db.r6g.xlarge` Multi-AZ US$ 0,899/h (730 h/mês), disco RDS Multi-AZ US$ 0,23/GB; DynamoDB on-demand US$ 0,625 por milhão de escritas, US$ 0,125 por milhão de leituras e US$ 0,25/GB acima de 25 GB; Firehose US$ 0,029/GB (ingestão) + US$ 0,018/GB (conversão para Parquet); S3 Standard US$ 0,023/GB; SageMaker `ml.m5.large` US$ 0,115/h. O valor do RDS `db.m5.large` Multi-AZ (US$ 259,88) foi conferido também na própria AWS Pricing Calculator (print `evidencias/2.3-aws-01-rds-postgres-multiaz-300gb.jpg`).

| Domínio | Serviço AWS | Tipo / configuração | Hipótese de volume | US$/mês | Justificativa |
|---------|-------------|---------------------|--------------------|---------|---------------|
| Produtos | **RDS PostgreSQL** + pgvector | `db.m5.large` Multi-AZ, 100 GB | 5 M SKUs, ~100 GB | 282,88 | Esquema fixo, joins com categoria, integridade de estoque (ACID); o pgvector guarda o embedding na mesma linha. |
| Clientes | **DynamoDB** (on-demand) | PK `cliente_id`, GSI por e-mail | 50 M perfis × ~2 KB = ~100 GB; 300 M leituras e 5 M escritas/mês | 43,75 | Acesso quase sempre por chave; o perfil muda pouco e escala sem gerenciar servidor. |
| Pedidos | **RDS PostgreSQL** | `db.r6g.xlarge` Multi-AZ, 500 GB | 10 M pedidos/mês, 12 meses quentes (o resto vai para S3/Athena) | 771,27 | Criticidade transacional: ACID, chaves estrangeiras e failover automático (Multi-AZ). |
| Carrinhos | **DynamoDB** com TTL | on-demand, PK `cliente_id` | ~500 k ativos × 2 KB = 1 GB; 50 M escritas e 150 M leituras/mês | 71,88 | Esquema variável, leitura rápida e expiração em 24 h pelo TTL (sem job de limpeza). |
| Reviews | **DynamoDB** | PK `produto_id`, SK `review_id` | 30 M × 1 KB = ~30 GB; 3 M escritas e 100 M leituras/mês | 9,38 | Texto livre lido por produto; o sentimento é calculado depois (Aula 4). |
| Busca de produtos | **pgvector no RDS de produtos** (híbrida: vetor + full-text) | mesmo `db.m5.large` | 5 M vetores | 0,00 (já no RDS de Produtos) | Mantém preço exato e sentido no mesmo SQL; OpenSearch só se o volume ou a latência exigirem (ver 3.1). |
| Sessões | **DynamoDB** com TTL | on-demand, PK `session_id`, TTL 30 min | ~1 M ativas; 100 M escritas e 300 M leituras/mês | 81,25 | Chave-valor com expiração nativa; ElastiCache só se precisarmos de sub-milissegundo. |
| Histórico de navegação | **Kinesis Data Firehose → S3 (Parquet) → Athena** | Parquet particionado por dia | 3 bilhões de eventos × 0,5 KB = ~1,5 TB/mês (1.536 GB); Parquet ≈ 300 GB | 79,25 (1º mês) | Bilhões de eventos append-only: lake barato, consultado só em lote (Athena, US$ 5/TB lido). |
| Modelos ML | **S3** + **SageMaker endpoint** | 10 GB de artefatos; 1 × `ml.m5.large` 24×7 | recomendação, churn | 84,18 | Artefatos versionados no S3; o endpoint serve a inferência. |
| **Total** | | | | **≈ US$ 1.424/mês (≈ US$ 17 mil/ano)** | |

Observações:

- **Pedidos e Produtos são 79% do custo** (US$ 1.054 de US$ 1.424): são os dois bancos relacionais Multi-AZ. O restante, NoSQL e lake, custa pouco porque cobra por uso.
- **Atenção ao dimensionamento do catálogo:** 5 M de embeddings de 384 dimensões ocupam ≈ 7,2 GiB; o `db.m5.large` tem 8 GiB de RAM, então o índice HNSW não cabe confortavelmente em memória. Para manter a busca rápida, o ideal é o `db.r6g.xlarge` (32 GiB, US$ 0,899/h Multi-AZ), **≈ + US$ 396/mês** sobre o valor da tabela (ver 3.3). Mantivemos o `db.m5.large` na tabela por ser o dimensionamento mínimo.
- **Não incluído:** tráfego de rede, backups acima do espaço gratuito, CloudWatch, Athena (US$ 5/TB lido), OpenSearch, e a camada de cache (CloudFront/ElastiCache).
- O free tier de 25 GB do DynamoDB vale por conta e região, não por tabela; a conta separada por domínio deixa o custo um pouco acima do real.

**Diagrama da camada de dados:** `diagramas/arquitetura-qc-aula02.png` (fonte em `.svg`).

#### Canvas de decisão (resumo; preenchido por domínio em `canvas-decisao.md`)

Pergunta que cada dado responde, quem lê e consistência exigida:

| Domínio | Pergunta que responde | Quem lê | Consistência | Onde mora |
|---------|----------------------|---------|--------------|-----------|
| Produtos | "Qual o preço e o estoque desta cadeira?" | Agentes, frontend, backoffice | Forte (estoque é dinheiro) | RDS PostgreSQL + pgvector |
| Clientes | "Quem é este cliente e onde entrego?" | Checkout, agentes | Eventual na leitura; forte na escrita do endereço | DynamoDB |
| Pedidos | "O que o cliente comprou e quanto devo faturar?" | Faturamento, suporte, analytics | Forte (ACID) | RDS PostgreSQL |
| Carrinhos | "O que há no carrinho agora?" | Frontend, agentes | Eventual (expira em 24 h) | DynamoDB + TTL |
| Reviews | "O que os clientes acham deste produto?" | Frontend, agentes, ML | Eventual | DynamoDB |
| Busca | "Quais produtos combinam com o que o cliente descreveu?" | Agentes, frontend | Eventual | pgvector (híbrido) |
| Sessões | "Este usuário está logado?" | API Gateway/Lambda | Eventual (30 min) | DynamoDB + TTL |
| Navegação | "O que os clientes clicam antes de comprar?" | Analistas, ML | Eventual, em lote | S3 + Athena |
| Modelos ML | "Qual versão do modelo está em produção?" | Serviço de inferência | Forte na publicação | S3 + SageMaker |

### Exercício 2.2 — Plano de migração de dados (12 meses)

Situação atual: Oracle on-premise de **8 TB** (produtos + pedidos + clientes); **50 TB** de imagens em NAS; **~200 TB** de logs históricos em fita (compliance fiscal).

**a) Os 6 Rs por repositório**

| Repositório | R | Por quê |
|-------------|---|---------|
| Oracle 8 TB | **Replatform** (Oracle → PostgreSQL gerenciado) | Elimina a licença Oracle; o esquema é convertido (AWS SCT) e os dados migrados (DMS). Rehost em RDS for Oracle manteria o custo de licença. |
| 50 TB de imagens (NAS) | **Rehost** (lift-and-shift para S3) | Arquivos não mudam: copiar como estão e servir por CloudFront. |
| 200 TB de logs em fita | **Replatform** + **Retire** parcial | Migrar o que a lei exige guardar para S3 Glacier Deep Archive; o que já passou da retenção fiscal é descartado (Retire). |

**b) Serviços AWS e custo recorrente**

| Repositório | Serviço | Conta (preço oficial, us-east-1) | US$/mês |
|-------------|---------|----------------------------------|---------|
| Oracle 8 TB | RDS PostgreSQL Multi-AZ (dados quentes) + S3 (histórico frio) | Já no Ex. 2.1 (Produtos + Pedidos); 8 TB em disco Multi-AZ custaria 8.192 GB × US$ 0,23 = US$ 1.884; por isso o histórico antigo vai para S3/Athena. | ver 2.1 |
| 50 TB de imagens | S3 Standard (hoje) → S3 Standard-IA com lifecycle | 51.200 GB × US$ 0,023 = **US$ 1.177,60** em Standard | 1.177,60 |
| 200 TB de logs | S3 Glacier Deep Archive | 204.800 GB × US$ 0,00099 = **US$ 202,75** | 202,75 |

**c) Como migrar sem downtime**

- **Banco (Oracle → PostgreSQL):** AWS SCT converte esquema e código; o **AWS DMS** faz carga inicial e depois **replicação contínua (CDC)**, mantendo o Oracle ativo. O *cutover* é um fim de semana: congelar escritas, esperar o lag chegar a zero, apontar a aplicação para o RDS, manter o Oracle por alguns dias como plano de rollback.
- **Imagens:** **AWS DataSync** copia do NAS para o S3 de forma incremental (nova passada só envia o que mudou), em paralelo com a operação. Dá para trocar o endpoint das imagens por CloudFront no final.
- **Fitas (200 TB):** pela rede levaria meses; usar **AWS Snowball Edge** (transporte físico) ou Storage Gateway (fita virtual) e jogar direto em Deep Archive. A taxa por job do Snowball não foi simulada.

**d) Custo de transferência dos 50 TB de imagens**

- **Entrar na AWS é grátis** (transferência de entrada: US$ 0). Há só o custo do **DataSync: US$ 0,0125/GB**, ou seja, 51.200 GB × 0,0125 = **US$ 640 (uma vez)**.
- **Sair depois não é grátis.** Transferência para a Internet (preço oficial): primeiros 100 GB/mês grátis; até 10 TB a US$ 0,09/GB; próximos 40 TB a US$ 0,085/GB. Para 50 TB: (10.240 − 100) × 0,09 + 40.960 × 0,085 = US$ 912,60 + US$ 3.481,60 = **≈ US$ 4.394**. É o custo de uma eventual saída (lock-in) e justifica manter o formato dos arquivos aberto.

**e) LGPD: onde ficam os dados de brasileiros**

- A LGPD **não obriga** a guardar os dados no Brasil, mas a transferência internacional exige base legal (art. 33: país com nível adequado de proteção, cláusulas-padrão, consentimento específico, etc.).
- Recomendação para a QC: **região `sa-east-1` (São Paulo)** para dados pessoais de clientes (Clientes, Pedidos, Reviews com identificação), o que também reduz latência; `us-east-1` só para dados sem identificação ou com base legal documentada. Criptografia em repouso (KMS), segredos no Secrets Manager e registro de acesso (CloudTrail).
- Observação: o lab usa `us-east-1` porque o Learner Lab restringe regiões; em produção, a escolha da região é uma decisão de conformidade, não só de preço.

**Cronograma (12 meses)**

| Mês | Marco |
|-----|-------|
| 1–2 | Descoberta, SCT (avaliação do esquema), landing zone (contas, rede, KMS), região `sa-east-1` |
| 3–5 | Imagens: DataSync em lote contínuo → S3; troca do endpoint para CloudFront |
| 4–8 | Banco: conversão de esquema, DMS com CDC, testes de carga e de regressão |
| 7–10 | Fitas: Snowball Edge para Deep Archive; descarte do que passou da retenção |
| 9 | *Cutover* do banco (fim de semana, fora do fechamento do mês) |
| 10–12 | Estabilização, desligamento do Oracle e do NAS, revisão de custo |

### Exercício 2.3 — Particionamento no DynamoDB

Tabela `reviews`: partição `produto_id`, ordenação `review_id` (a mesma do lab).

**a) Por que NÃO seriam boas chaves de partição**

- **`review_id` sozinho:** (1) a consulta do agente é "reviews **do produto X**", e com `review_id` na partição cada review fica numa partição diferente, então seria preciso um **Scan** para juntar as de um produto; (2) não dá para ordenar ou paginar por produto; (3) a chave é única por review, então cada partição guardaria um item só, e o acesso ao produto viraria N leituras individuais (caro).
- **`score` (1–5):** (1) **cardinalidade 5**: no máximo 5 valores de partição, então toda a tabela fica concentrada em poucas partições (*hot partition*); (2) o padrão de acesso nunca é "todas as reviews de nota 4", então a chave não responde a nenhuma pergunta do agente.
- **`data_da_review` (timestamp):** (1) escritas sempre vão para a **partição "de hoje"** (hot partition de escrita), enquanto as antigas ficam ociosas; (2) as consultas são por produto, não por dia, então exigiria Scan.

**b) Por que `produto_id` funciona, e o problema**

Funciona porque o acesso é por produto: a consulta `Query` com `produto_id = X` lê só uma partição, ordenada por `review_id`. O problema é a **hot partition**: um produto muito popular (um *best-seller* ou um produto viral) concentra leituras e escritas numa única chave e pode estourar os limites de uma partição (≈ 3.000 RCU e 1.000 WCU por segundo). Mitigações: *write sharding* (`produto_id#0..N` e juntar na leitura), cache (DAX/CloudFront) ou on-demand.

**c) "Todas as reviews de um cliente específico"**

Criar um **Global Secondary Index (GSI)** com partição `cliente_id` e ordenação `data_da_review` (projetando só os atributos necessários). O GSI é uma cópia mantida pelo DynamoDB, com sua própria capacidade, e permite `Query` por cliente sem Scan. O custo é escrita dobrada (cada review é gravada na tabela e no índice) e consistência **eventual** no GSI.

**d) Estimativa: um produto com 50.000 reviews de ~400 bytes**

- 50.000 × 400 B = 20.000.000 B ≈ **19,1 MiB** na coleção do produto (cada review é um item separado, com sua `review_id`).
- **Limite de 400 KB por item:** cada review (400 B, + overhead de nomes de atributos) fica muito abaixo do limite. Mas, **se alguém guardasse as 50.000 reviews dentro de um único item** (lista), seriam 19,1 MiB, ou **≈ 49 vezes o limite** de 400 KB, e o item seria rejeitado. Por isso uma review = um item.
- **Limite de 10 GB por valor de chave de partição** (vale quando a tabela tem *Local Secondary Index*): 19,1 MiB é **≈ 0,19% de 10 GB**. Cabe com enorme folga; o limite só preocuparia com cerca de 25 milhões de reviews de 400 B no mesmo produto.

### Evidência da execução no lab (Labs 1, 1B, 2, 3A e 3B)

Executado no CloudShell com `terraform apply` (17 recursos) e o atalho `qc` do lab. Os prints citados estão em `evidencias/`; os logs de texto em `evidencias/logs/`.

| Lab | O que foi feito | Resultado | Evidência |
|-----|-----------------|-----------|-----------|
| Apply | S3, RDS PostgreSQL 16, Secrets Manager, DynamoDB on-demand, Athena | 17 recursos criados (RDS em 5 min 5 s) | `00-…preflight-ok`, `01-terraform-apply-completo-17-recursos`, `logs/01-terraform-apply.log` |
| 1 | `produtos.csv` no S3 + lifecycle + Athena sobre o CSV | Objeto de 2.075 bytes, criptografia AES256; regra `logs-lifecycle`: Standard-IA em 30 dias, Glacier em 90, expira em 365; Athena devolveu as 6 categorias lendo 2.075 bytes | `04-lab1-s3-objeto-e-lifecycle`, `05-lab1-athena-sql-no-csv`, `13-console-s3-bucket` |
| 1B | 200 mil pedidos: CSV (`raw/`) × Parquet particionado por mês (`curated/`) | `raw/` 12,6 MiB, `curated/` 2,4 MiB; a mesma consulta leu **12,63 MB no CSV e 23,2 KB no Parquet (557× menos)** | `06-lab1b-lake-csv-vs-parquet`, `16-console-athena-consultas` |
| 2 | Catálogo no RDS pelo Secrets Manager | 20 produtos; mesmas 6 categorias e médias do Athena; o código só usa o nome do segredo | `07-lab2-rds-produtos-e-segredo`, `14-console-rds-disponivel`, `15-console-secrets-manager` |
| 3A | 30 reviews no DynamoDB | `Query` por `produto_id = 5`: **2 itens lidos, 0,5 RCU**; `Scan` com `contains()`: **30 itens lidos, 2,0 RCU**, para achar 5 | `08-lab3a-dynamodb-query-vs-scan`, `17-console-dynamodb-30-itens` |
| 3B | Embeddings (MiniLM multilíngue, 384 dim.) + pgvector com índice HNSW | 20 produtos indexados; busca por palavra × sentido (ver 3.1) | `09-lab3b-busca-palavra-vs-sentido` |

> **Achado do Lab 1:** o objeto aparece com classe `None` no `head-object`: é como a API mostra a classe Standard (a classe padrão não vem preenchida).

---

## 🔴 Nível 3 — Bônus

### Exercício 3.1 — Busca híbrida: vetor + full-text no mesmo PostgreSQL

Implementado em `scripts/buscar_hibrido.py` e executado no CloudShell contra o RDS do lab (`evidencias/10-ex31-busca-hibrida-rrf.jpg`, `evidencias/logs/10-ex31-busca-hibrida.log`). O script cria a coluna `tsv tsvector` (português, gerada de `nome || descricao`) com índice GIN, roda as duas buscas e funde os rankings com **RRF** (`Σ 1/(60 + posição)`).

Top 3 de cada modo (20 produtos no catálogo):

| Consulta | Palavra (full-text) | Vetor (pgvector) | Híbrido (RRF) |
|----------|---------------------|------------------|---------------|
| "Dell Inspiron" | 1. Notebook Dell Inspiron 15 | 1. Notebook Dell Inspiron 15 · 2. Tênis Adidas Ultraboost 23 · 3. Smartphone Samsung Galaxy S24 | 1. Notebook Dell Inspiron 15 · 2. Tênis Adidas Ultraboost 23 · 3. Smartphone Samsung Galaxy S24 |
| "algo para trabalhar em pé" | (nenhum resultado) | 1. Cadeira Home Office Confortável · 2. Mesa de Escritório com Regulagem de Altura · 3. Cadeira Ergonômica DXRacer | igual ao vetor |
| "presente para quem gosta de correr" | (nenhum resultado) | 1. Cadeira Gamer Vermelha · 2. Tênis Adidas Ultraboost 23 · 3. Tênis Nike Air Zoom Pegasus 40 | igual ao vetor |

**Reflexão**

1. **Em qual consulta cada modo falhou, e por quê?**
   - **Palavra:** falhou nas duas perguntas em linguagem natural ("trabalhar em pé", "presente para quem gosta de correr") e acertou o nome exato ("Dell Inspiron"). O `plainto_tsquery` exige **todos** os termos (AND) e nenhum produto tem "pé", "correr" ou "presente" escritos; busca por palavra não entende sinônimo.
   - **Vetor:** acertou o nome exato no 1º lugar, mas os lugares 2 e 3 são lixo (similaridade 0,37: o vetor sempre devolve K resultados, mesmo sem nada parecido). Em "trabalhar em pé", o 1º é uma cadeira e a **Mesa com Regulagem de Altura**, que é a resposta certa, ficou em 2º. Em "presente para quem gosta de correr", o 1º é uma **Cadeira Gamer** (similaridade 0,38, baixa), à frente dos tênis. Um agente que usasse o top 1 sem filtro responderia errado.
   - **Híbrido:** no nosso teste **não melhorou**: com o full-text vazio, o RRF devolve exatamente o ranking do vetor. Ele só ajuda quando os dois rankings têm candidatos. Por isso o próximo ajuste seria trocar o `plainto_tsquery` (AND) por `websearch_to_tsquery`/OR com expansão de termos, e descartar resultados vetoriais abaixo de um limiar de similaridade (≈ 0,45). **Não rodamos essa variação**, porque o ambiente do lab foi destruído em seguida; é uma hipótese a validar.
2. **Modelo de embedding em produção:** o lab usa o MiniLM multilíngue local (384 dimensões, `fastembed`), bom para aprender e sem custo por chamada. Em produção usaríamos o **Amazon Titan Text Embeddings V2** ou o **Cohere Embed Multilingual**, no Bedrock, escolhendo por **recall@k medido em um conjunto de ~50 perguntas reais em português** (não por *benchmark* de inglês). A dimensão do vetor define o tamanho do índice: 5 M de SKUs × 384 dim. × 4 B ≈ 7,2 GiB só de vetores (com 1.024 dim., ≈ 19 GiB).
3. **Manter os embeddings atualizados:** pipeline incremental: evento do S3 (`ObjectCreated` em `catalogo/`) ou do próprio banco (CDC) → fila SQS (com DLQ) → Lambda que gera o embedding e faz `INSERT … ON CONFLICT (id) DO UPDATE`. Guardar a versão do modelo na linha: ao trocar de modelo, re-embedar em lote e alternar o índice, porque vetores de modelos diferentes não se comparam.
4. **Quando trocar o pgvector:** por **Amazon OpenSearch Service** quando o volume passar de dezenas de milhões de vetores, ou for preciso alto QPS, facetas, BM25 + vetor nativos e filtros complexos; por **Bedrock Knowledge Bases** quando o conteúdo forem documentos (PDF, FAQ) e quisermos chunking, sincronização com o S3 e RAG gerenciado com pouco código. Enquanto o dado for relacional (preço, estoque, categoria) e o volume couber no RDS, o pgvector evita um segundo sistema para manter consistente.

### Exercício 3.2 — O data lake da QC em camadas

**1. Camadas**

| Camada | O que entra / de onde | Formato e organização | Quem lê, e por quê |
|--------|----------------------|-----------------------|--------------------|
| `raw/` | Pedidos (export/CDC do RDS), cliques (Firehose), logs de compra e de aplicação, exatamente como chegam | CSV/JSON originais, imutáveis, prefixo por fonte e data de chegada | **Só** a ingestão e engenharia de dados (reprocessamento e auditoria). Tem dado pessoal (`cliente_id`, CPF): acesso mínimo por LGPD. |
| `curated/` | Raw limpo: tipos corretos, sem duplicata, PII removido ou pseudonimizado | **Parquet + Snappy**, particionado por **ano e mês** (a coluna que quase toda consulta filtra) | Analistas no **Athena**, painéis de BI e agentes (via Athena/Glue). Sem PII, por isso leitura ampla. |
| `consumo/` (opcional) | Agregados prontos (faturamento por categoria e mês) | Parquet pequeno ou tabela materializada | Painéis e agentes de relatório; é o que responde em segundos sem varrer o lake. |

No lab: `raw/pedidos/pedidos.csv` (12,6 MiB, um arquivo) e `curated/pedidos/mes=AAAA-MM/` (13 objetos, 2,4 MiB), criados por `qc lake gera` e `qc lake cura` (CTAS no Athena).

**2. DDL e consulta da camada curated**

A tabela real criada pelo CTAS do lab (`SHOW CREATE TABLE qc.pedidos_curated`, print `evidencias/12-ex32-lake-ddl-parquet-e-tamanhos.jpg`): Parquet com compressão `SNAPPY`, `PARTITIONED BY (mes string)`, `LOCATION s3://…/curated/pedidos/`. Para os logs de compra da QC (o formato e o particionamento são a parte importante):

```sql
CREATE EXTERNAL TABLE qc.logs_compras (
  pedido_id string, produto_id int, valor decimal(10,2), ts timestamp
)
PARTITIONED BY (ano int, mes int)
STORED AS PARQUET
LOCATION 's3://<bucket>/curated/logs_compras/';

-- carrega as partições existentes (ou usar partition projection)
MSCK REPAIR TABLE qc.logs_compras;

SELECT mes, COUNT(*) AS pedidos, SUM(valor) AS receita
FROM qc.logs_compras WHERE ano = 2026
GROUP BY mes ORDER BY mes;
```

A consulta só lê as pastas `ano=2026/` e as colunas `mes` e `valor` (Parquet é colunar): é isso que derruba o custo.

**3. Custo no Athena (US$ 5 por TB lido)**

Razão medida no lab (`qc lake compara`): a pergunta "faturamento por categoria em setembro" leu **12,63 MB no CSV (arquivo inteiro) e 23,2 KB no Parquet (557× menos)**. Essa razão já inclui ler **1 mês de 12**. Na QC a consulta lê **1 ano de 3** (1/3 dos dados em vez de 1/12, ou seja, 4× mais partições), então ajustamos a razão para ≈ 557 ÷ 4 ≈ **139×**.

| Cenário (30 TB de CSV) | Dado lido por consulta | Custo por consulta | 100 consultas/dia (3.000/mês) |
|------------------------|------------------------|--------------------|-------------------------------|
| CSV sem partição | 30 TB | 30 × US$ 5 = **US$ 150,00** | **US$ 450.000/mês** |
| Parquet por ano/mês (razão ajustada 139×) | ≈ 220 GB | ≈ **US$ 1,08** | **≈ US$ 3.230/mês** |
| Parquet, razão do lab sem ajuste (557×, só como limite inferior) | ≈ 55 GB | ≈ US$ 0,27 | ≈ US$ 810/mês |

O formato e a partição cortam a conta em ≈ 99%. O ajuste de 4× é nossa hipótese (as partições de 3 anos têm o mesmo tamanho); o resultado real depende de quantas colunas a consulta lê.

**4. Redshift Serverless e lakehouse (Iceberg): quando valem a pena**

- **Athena sobre o lake (curated em Parquet):** vale enquanto o uso for esporádico ou de volume moderado, porque paga por TB lido e não há servidor. Como no lab, a conta cai quando o dado está bem particionado.
- **Amazon Redshift Serverless:** passa a valer quando há **muita concorrência e consultas repetidas** (painéis de BI com dezenas de usuários), *joins* pesados e SLA de latência: cobra por capacidade (RPU-hora) e mantém o dado em armazenamento colunar otimizado, com cache. Quando o custo de 100+ consultas/dia no Athena passa o de uma capacidade reservada, é o ponto de virada. Não simulamos o preço do Redshift Serverless.
- **Lakehouse (tabelas Apache Iceberg no S3):** vale quando é preciso **UPDATE/DELETE por linha** (CDC dos pedidos, e o direito de eliminação da LGPD), **evolução de esquema** e *time travel*. Parquet puro é só de anexar (reescrever uma partição para apagar um cliente). É o caminho do case da Junto Seguros: Iceberg no S3, consultado por Athena/Redshift, sem copiar o dado para um data warehouse.

### Exercício 3.3 — Benchmark: RDS × DynamoDB × pgvector

Pergunta do agente: **"cadeira ergonômica para dor lombar"**. Script `scripts/benchmark_busca.py`, executado no CloudShell contra o RDS e o DynamoDB do lab (10 consultas por opção, `time.perf_counter()`; `evidencias/11-ex33-benchmark-rds-dynamodb-pgvector.jpg` e `evidencias/logs/11-ex33-benchmark.log`). Para o DynamoDB o script cria uma tabela temporária com os 20 produtos, faz `Scan` com `contains()` e a apaga no final.

| Opção | Latência média (mín–máx) | Top 3 | Qualidade |
|-------|--------------------------|-------|-----------|
| **(a) RDS PostgreSQL** `ILIKE '%palavra%'` | **0,9 ms** (0,5–3,1) | Cadeira Ergonômica DXRacer · Tênis Nike Air Zoom Pegasus 40 · Cadeira Gamer Vermelha | Acha a cadeira certa, mas traz um **tênis** (a palavra "para" bate em "para correr"). Não entende sentido: "dor lombar" não acha "coluna". |
| **(b) DynamoDB** `Scan` + `contains()` | **210,6 ms** (8,6–**1.014,8**) | Cadeira Gamer Vermelha · Tênis Adidas Ultraboost 23 · Tênis Nike Air Zoom Pegasus 40 | **Pior:** sem ordenação por relevância (devolve na ordem das chaves) e com o mesmo ruído do `ILIKE`. Leu os 20 itens: **2,0 RCU por consulta**. |
| **(c) pgvector** (sentido) | **14,0 ms** (13,1–15,6), incluindo gerar o embedding da pergunta | Cadeira Ergonômica DXRacer · Cadeira Gamer Vermelha · Cadeira Home Office Confortável | **Melhor:** as 3 são cadeiras e a mais adequada está em 1º; entende o sentido, não depende da palavra. |

**Por que o `Scan` do DynamoDB não escala:** o DynamoDB não tem busca por texto; `contains()` é só um filtro aplicado **depois** de ler a tabela inteira, e o custo e a latência crescem com o tamanho da tabela, não com o resultado. Com 20 itens já foram 2,0 RCU. A alternativa seria um índice externo (OpenSearch) alimentado por DynamoDB Streams.

**Custo de 1 M de consultas/mês** (preços oficiais da AWS, us-east-1):

| Opção | Conta | US$/mês |
|-------|-------|---------|
| (a) RDS `ILIKE` | Roda no RDS que já existe para o catálogo (Ex. 2.1: `db.m5.large` Multi-AZ = US$ 259,88 + disco). 1 M de consultas/mês é ≈ 0,4 consulta/s: custo marginal ≈ 0. Com 5 M de SKUs o `ILIKE '%x%'` varre a tabela; precisaria de índice `pg_trgm` (não medido). | ≈ 0 marginal |
| (b) DynamoDB `Scan` | **No lab (20 itens):** 1 M × 2,0 RCU = 2 M RCU × US$ 0,125/M = **US$ 0,25**. **Na QC (5 M de SKUs ≈ 5 GB):** cada `Scan` lê 5 GB ÷ 8 KB (leitura eventual) = 655.360 RRU × US$ 0,125/M = US$ 0,082 por consulta; × 1 M = **≈ US$ 81.920** (e segundos de latência por consulta). | 0,25 (lab) · ≈ 81.920 (QC) |
| (c) pgvector | Mesmo RDS do catálogo; o embedding da pergunta roda no próprio serviço (no teste, na CPU do CloudShell, incluído nos 14 ms). Marginal ≈ 0. **Dimensionamento:** 5 M de vetores de 384 dim. ≈ 7,2 GiB; para manter o índice HNSW em memória o ideal é `db.r6g.xlarge` (32 GiB, US$ 0,899/h Multi-AZ), **+ ≈ US$ 396/mês** sobre o `db.m5.large`. Com Titan/Cohere no Bedrock há ainda o custo por token (não simulado). | ≈ 0 marginal (+ ≈ 396 de dimensionamento) |

**Recomendação para o agente de busca da QC:** **pgvector no RDS, em modo híbrido** (3.1). Foi o mais relevante (cadeiras no top 3), com 14 ms de latência, reaproveita o RDS que já guarda preço e estoque (um único SQL traz sentido e filtro de preço) e custa cerca de zero por consulta. O `ILIKE` é rápido e barato, mas erra o sentido e traz ruído. O DynamoDB não serve para busca de produtos: é a pior latência e o pior custo à medida que a tabela cresce. Revisitar o OpenSearch se o catálogo passar de dezenas de milhões de itens ou o QPS exigir.

---

## Reflexão coletiva

**O que o grupo aprendeu de mais importante nesta aula?**
Que **a escolha do banco é a escolha da pergunta que o dado consegue responder barato**. No lab, a mesma tabela de reviews respondeu "reviews do produto 5" lendo 2 itens (0,5 RCU) e "reviews com a palavra *embalagem*" lendo todos os 30 (2,0 RCU), e o custo dessa diferença cresce com a tabela. O mesmo vale para o lake: a mesma consulta leu 12,63 MB em CSV e 23,2 KB em Parquet particionado (557× menos), e na escala da QC (30 TB, 100 consultas/dia) isso separa ≈ US$ 450 mil de ≈ US$ 3 mil por mês. Aprendemos também que busca por sentido não é mágica: o pgvector colocou uma cadeira gamer à frente de tênis em "presente para quem gosta de correr", e nossa busca híbrida não melhorou quando o full-text voltou vazio.

**Como isso se conecta com a arquitetura cloud de uma plataforma agentic?**
Um agente só é tão bom quanto o dado que consegue recuperar. O agente da QC precisa de preço e estoque exatos (RDS), de contexto lido por produto (DynamoDB), de busca por significado (pgvector) e de histórico barato para aprender (S3 + Athena), tudo atrás de **permissões mínimas por role**. Segregar a senha no Secrets Manager muda o modelo de segurança: o código do agente só carrega o *nome* do segredo, a senha não vai para o Git, e quem lê é decidido pela política (a role da função), com auditoria e rotação. Para agentes, que executam código e podem vazar contexto, isso é a diferença entre um segredo comprometido e um segredo que nunca esteve no código.

**Que decisão arquitetural vocês fariam diferente se começassem hoje?**
(1) Medir a qualidade da busca **antes** de escolher o modelo e o banco, com um conjunto de perguntas reais em português e um limiar de similaridade, em vez de confiar no top 1. (2) Desenhar o lake em camadas (`raw`, `curated`, `consumo`) e o particionamento desde o primeiro dia. (3) Escolher a região pela LGPD (`sa-east-1` para dado pessoal), não só por preço. (4) Dimensionar o RDS com o índice vetorial em mente (RAM), o que muda o custo do catálogo em ≈ US$ 396/mês.

### Uma linha do trabalho de cada membro (canvas)

> **Pendente do grupo:** a rubrica pede **um dado real do trabalho de cada membro, anonimizado**. Não inventamos esses dados; cada membro preenche a sua linha (ver também `canvas-decisao.md`).

| Membro | Dado | Que pergunta responde | Volume e crescimento | Pode errar? | Quem lê / credencial | Custo/mês | Onde mora hoje — e onde deveria morar |
|--------|------|-----------------------|----------------------|-------------|----------------------|-----------|---------------------------------------|
| Cinara Nubia Silva | _a preencher_ | | | | | | |
| Guilherme Augusto Veiga Pires | _a preencher_ | | | | | | |
| Somario Canuto da Silva | _a preencher_ | | | | | | |

---

## Artefatos do ZIP

- `canvas-decisao.md`: o canvas preenchido (9 domínios), usado no Ex. 2.1.
- `diagramas/arquitetura-qc-aula02.png` e `.svg`: camada de dados da QC (Ex. 2.1).
- `terraform/`: código IaC do lab (S3, RDS, Secrets Manager, DynamoDB, Athena), executado sem alterações.
- `scripts/`: `buscar_hibrido.py` (Ex. 3.1) e `benchmark_busca.py` (Ex. 3.3).
- `evidencias/`: 21 capturas de tela e `evidencias/logs/` com a saída de cada comando do lab.
- Endpoint ativo: **nenhum** (o ambiente foi destruído com `terraform destroy` ao final).
