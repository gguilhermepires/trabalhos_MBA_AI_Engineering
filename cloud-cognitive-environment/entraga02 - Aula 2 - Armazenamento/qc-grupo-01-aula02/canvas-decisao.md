# Canvas de decisão de dados — Quantum Commerce

**Grupo:** 01 · **Entrega 02 · N2**

Uma linha por dado. As colunas são as perguntas que decidem onde ele mora; a última é a decisão. Custos em US$/mês, `us-east-1`, preço on-demand, com preços unitários do arquivo oficial de preços da AWS (a mesma base da [calculadora AWS](https://calculator.aws)); as contas e hipóteses de volume estão no Exercício 2.1 de `entrega-grupo-aula02.md`.

## Os 9 domínios da QC

| Dado | Que pergunta responde | Volume e crescimento | Pode errar? | Quem lê / credencial | Custo/mês | Onde mora e por quê |
|------|-----------------------|----------------------|-------------|----------------------|-----------|---------------------|
| Reviews | O que os clientes acham deste produto? | ~30M textos (+3M/mês) | Sim (minutos) | Agente de atendimento, pela role | 9,38 | **DynamoDB**: sempre lido por produto (partition key `produto_id`). Não usaríamos RDS: sem joins e sem esquema rígido. |
| Produtos (5M SKUs) | Qual o preço e o estoque desta cadeira? | 5M SKUs, ~100 GB, crescimento lento | **Não** (estoque envolve dinheiro) | Agentes, frontend e backoffice; role + segredo no Secrets Manager | 282,88 | **RDS PostgreSQL Multi-AZ** (+ pgvector): esquema fixo, joins com categoria e integridade de estoque. Não usaríamos DynamoDB: precisamos de transação e de joins. |
| Clientes (~50M) | Quem é este cliente e onde entrego? | ~50M perfis × 2 KB = ~100 GB | Leitura: sim; endereço: não | Checkout e agentes, pela role | 43,75 | **DynamoDB** (PK `cliente_id`, GSI por e-mail): acesso quase sempre por chave. Não usaríamos RDS: seria um banco enorme só para buscas por chave. |
| Pedidos (~10M/mês) | O que o cliente comprou e quanto devo faturar? | ~10M/mês (~30 GB/mês); 12 meses quentes (500 GB) | **Não** (ACID, dinheiro) | Faturamento, suporte e analytics, por roles distintas | 771,27 | **RDS PostgreSQL Multi-AZ**: transações e chaves estrangeiras; o histórico antigo vai para S3/Athena. Não usaríamos DynamoDB: faturamento exige joins e garantias ACID. |
| Carrinhos ativos (~500k) | O que há no carrinho agora? | ~500k ativos × 2 KB = ~1 GB; 50M escritas/mês | Sim (expira em 24 h) | Frontend e agentes, pela role | 71,88 | **DynamoDB com TTL**: esquema variável, leitura rápida, expiração nativa. Não usaríamos RDS: escrita alta e dado descartável. |
| Busca de produtos | Quais produtos combinam com o que o cliente descreveu? | 5M vetores de 384 dim. (~7,2 GiB) | Sim (eventual) | Agentes e frontend, via o mesmo RDS | 0 (no RDS de Produtos; ≈ +396 se o índice exigir `db.r6g.xlarge`) | **pgvector no RDS (híbrido, com full-text)**: preço exato e sentido no mesmo SQL. Não usaríamos DynamoDB (sem busca por texto: Scan custa ≈ US$ 82 mil/mês a 1M consultas); OpenSearch só em escala maior. |
| Sessões (~1M) | Este usuário está logado? | ~1M ativas; 100M escritas/mês | Sim (30 min) | API Gateway/Lambda, pela role | 81,25 | **DynamoDB com TTL**: chave-valor com expiração nativa. ElastiCache só se precisarmos de sub-milissegundo. |
| Histórico de navegação | O que os clientes clicam antes de comprar? | ~3 bilhões de eventos/mês (~1,5 TB) | Sim (lote) | Analistas e ML, no Athena | 79,25 (1º mês) | **Kinesis Firehose → S3 (Parquet, partição ano/mês) → Athena**: append-only e analítico. No lab: 557× menos bytes lidos que em CSV. Não usaríamos RDS nem DynamoDB. |
| Modelos de ML | Qual versão do modelo está em produção? | ~10 GB de artefatos | Não na publicação | Time de ML e o endpoint, por role | 84,18 | **S3 + SageMaker endpoint** (`ml.m5.large`): artefatos versionados no S3. Não usaríamos EFS/EBS: são arquivos inteiros, baixados por HTTP. |
| **Total** | | | | **≈ 1.424** | |

## Uma linha do trabalho de vocês

> **Casos fictícios (empresa LogiFrio, a mesma do Ex. 2.3 da Entrega 01):** os dados abaixo são hipóteses criadas para o exercício, não dados reais do trabalho de cada membro. Os preços unitários vêm do arquivo oficial de preços da AWS (us-east-1, on-demand). Cada membro pode trocar a sua linha por um dado real anonimizado.

| Membro | Dado | Que pergunta responde | Volume e crescimento | Pode errar? | Quem lê / credencial | Custo/mês | Onde mora hoje — e onde deveria morar |
|--------|------|-----------------------|----------------------|-------------|----------------------|-----------|---------------------------------------|
| Cinara Nubia Silva | Notas fiscais (XML) | "Mostre a nota fiscal da compra X" e auditoria fiscal | ~2 M notas/mês × 20 KB = 40 GB/mês; guardar 5 anos (~2,4 TB) | Não (compliance), mas a leitura é rara | Fiscal e suporte, por role de leitura | ≈ 3,3 no 5º ano (40 GB em Standard × US$ 0,023 + 2.360 GB em Deep Archive × US$ 0,00099) | Servidor de arquivos local → **S3 com lifecycle** (Standard 30 dias, depois Deep Archive) |
| Guilherme Augusto Veiga Pires | Temperatura das câmaras frias | "Esta câmara está fora da faixa agora?" (alerta) | 300 câmaras × 1 leitura/min ≈ 13 M eventos/mês (~2,6 GB) | Sim (minutos), mas o alerta não pode falhar | App de monitoramento, pela role | ≈ 9,35 (13 M escritas × US$ 0,625/M + 10 M leituras eventuais × US$ 0,125/M) | Planilha e banco local → **DynamoDB on-demand com TTL de 7 dias**; histórico em S3/Parquet + Athena |
| Somario Canuto da Silva | Cadastro de motoristas e rotas | "Qual motorista está na rota X hoje?" (joins entre motorista, veículo e rota) | ~500 motoristas, 50 GB, crescimento lento | Não (escala de entrega, dinheiro de frete) | Logística e RH, por roles distintas | ≈ 135,69 (`db.m5.large` Single-AZ US$ 129,94 + 50 GB × US$ 0,115) | Access/planilha → **RDS PostgreSQL**: esquema fixo, joins e integridade |
