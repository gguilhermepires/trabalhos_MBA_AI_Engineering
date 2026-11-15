# Entrega Aula 03 — Grupo <NN>

**Disciplina:** Cloud & Cognitive Environments — FIAP MBA AI Engineering & Multi-Agents
**Turma:** <código da sua turma>
**Data de entrega:** <DD/MM/AAAA>

## Grupo

| # | Nome completo | GitHub | E-mail FIAP |
|---|---------------|--------|-------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## Distribuição do trabalho

| Membro | Nível assumido | Item específico |
|--------|----------------|-----------------|
| | | |

---

## 🟢 Nível 1 — Respostas

### Exercício 1.1 — Quando usar serverless?

| Cenário | Escolha | Justificativa |
|---------|---------|---------------|
| API de busca de produtos (1M chamadas/mês, picos na Black Friday) | Lambda | Paga por chamada, escala sozinha nos picos e custa zero parada. |
| Worker que processa pedidos da fila (1000 pedidos/dia, picos noturnos) | Lambda + gatilho SQS | Orientado a evento, escala a zero e o volume é baixo. |
| API legada em Java Spring Boot (não pode reescrever, time conhece) | ECS Express Mode | Roda o container como está, com ALB/HTTPS e auto-scale numa chamada; evita o cold start pesado do Java na Lambda. |
| Pipeline de processamento de imagens de produtos (1 hora por noite) | ECS Fargate (EventBridge Scheduler) | Passa dos 15 min da Lambda e paga só pelos segundos rodados. |
| Microserviço de pagamentos (regulado, logs detalhados, 100 req/s constante) | ECS Fargate | Sem cold start, com controle fino de rede, logs e IAM; tráfego constante dilui o custo e 100 req/s não justifica operar Kubernetes. |
| Plataforma com 25 microserviços + service mesh | EKS | Tem o ecossistema de service mesh mais maduro. |
| Container que extrai dados uma vez por dia e termina | ECS Fargate (RunTask agendado) | Roda, termina e paga só pelo tempo usado. |

### Exercício 1.2 — IAM Role vs alternativas

| Estratégia | Vulnerabilidade | Por quê |
|------------|-----------------|---------|
| Access key da AWS hardcoded no `lambda_function.py` | Alta | A chave vai para o git e para o histórico, não expira e vale em qualquer lugar. |
| Access key em variável de ambiente da Lambda | Alta | Fica visível no console e na API (`GetFunctionConfiguration`) para quem tem leitura, aparece em logs/dumps e é de longa duração. |
| Connection string no Secrets Manager, lida com access key de um usuário IAM | Média | O código não carrega o segredo, mas a access key continua de longa duração e ainda é preciso guardar a credencial que abre o cofre. |
| Connection string no Secrets Manager, lida com a execution role da Lambda | Baixa | Sem credencial no código; a role dá credenciais temporárias. O risco que sobra é uma role larga demais. |
| Sem segredo: a execution role tem permissão direta no S3 | Baixa | Não existe segredo para vazar; as credenciais são temporárias e rotacionadas pela AWS. É a opção mais simples. |

**Um vazamento do código no GitHub continua sendo problema?**
- **Sim** nas duas primeiras: a chave está no código ou na configuração versionada, e quem a copia usa de qualquer lugar até alguém revogar.
- **Em parte** na terceira: o código revela só o nome do segredo, mas a access key guardada nele continua valendo se vazar por outro caminho.
- **Não** na quarta e na quinta: o código só tem nomes de recursos. A credencial é da role e só funciona dentro da Lambda.

**Policy mínima da `buscar_produtos` em produção** (a função lê uma chave fixa, `catalogo/produtos.csv`, então só precisa de `GetObject`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LerSoCatalogo",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::qc-aula03-uco7x2-catalogo/catalogo/*"
    },
    {
      "Sid": "LogsDaPropriaFuncao",
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/lambda/qc-aula03-uco7x2-catalogo:*"
    }
  ]
}
```

A role também precisa da trust policy para `lambda.amazonaws.com`. Se a função passar a listar objetos, soma-se `s3:ListBucket` no ARN do bucket, com a condição `s3:prefix` igual a `catalogo/*`.

*Evidências:* `evidencias/1.2-iam/lambda-config.txt` (função usa a LabRole; bucket e chave) e `evidencias/1.2-iam/labrole-policies.txt` (as várias policies anexadas à LabRole).

A LabRole do lab pode muito mais do que isso. Se a função tiver uma falha (SSRF, injeção), o atacante herda tudo o que a role pode fazer, que é o cenário do caso Capital One. Com a policy acima, o estrago fica limitado a ler o catálogo.

### Exercício 1.3 — Cold start na prática

| Chamada | Tempo (curl) | Teve `Init Duration`? |
|---------|--------------|------------------------|
| 1 (fria) | 1,154 s (feita às 01:00:40 UTC, 30 min e 18 s depois da última invocação) | **Sim: 493,92 ms** (cobrados 656 ms; duração 161,6 ms; 92 MB) |
| 2 (quente, +5 s) | 0,345 s e 0,360 s (duas amostras, em outra rodada com a função já quente) | Não (cobrados 2 ms) |
| 3 (fria de novo, +30 min) | 1,154 s (é a mesma chamada fria da linha 1: a chamada de teste inicial não teve o tempo medido) | Sim: 493,92 ms |

Os dados vêm dos REPORTs do CloudWatch (`evidencias/1.3-cold-start/`): `reports-cloudwatch.txt` (rodada inicial, com a v1-mock: `Init Duration` de 84 a 87 ms), `report-chamada3.txt` e `chamada3-curl.txt` (a chamada fria depois de 30 min, já com a v3).

**Observação:** o `Init Duration` subiu de ~85 ms (v1-mock, sem dependências) para **~494 ms** na v3, porque ela importa o `boto3` e cria o cliente do S3 na inicialização; e a duração da chamada foi de 162 ms contra ~2 ms de uma chamada quente, pois a primeira leitura do CSV no S3 também entra na conta. O cold start cresce com o que o código carrega.

**Se o agente chamar a função 1 vez por hora (24 chamadas/dia), quantas serão frias?** Provavelmente **todas as 24**. A Lambda mantém o ambiente quente por alguns minutos de ociosidade (o que observamos: a função esfriou em menos de 30 min), e com uma chamada por hora o ambiente sempre terá sido reciclado. Cada usuário pagaria ~1,2 s na primeira resposta.

**Como mitigar se a UX exige < 500 ms?**
- **Provisioned Concurrency:** mantém N ambientes sempre inicializados (sem cold start). Custo contínuo por GB-s provisionado, mesmo sem chamadas; para 1 ambiente de 256 MB 24/7 estimamos na ordem de **US$ 3 por mês** *(estimativa nossa, a confirmar na calculadora AWS)*, mais o custo normal das requisições.
- **SnapStart:** tira um *snapshot* do ambiente já inicializado e o restaura nas partidas frias, reduzindo o `Init` (dá suporte a Python em versões recentes do runtime); sem custo por ambiente parado, mas com cobrança por restauração e por manter o snapshot *(a confirmar no preço vigente)*.
- **Medidas baratas:** enxugar o `Init` (importar só o necessário, criar o cliente fora do handler, como o código já faz), manter a função quente com uma chamada agendada (EventBridge a cada 5 min: tem custo mínimo, mas é paliativo) ou migrar o caminho crítico para Fargate (sem cold start).

*Evidências:* `evidencias/1.3-cold-start/` (REPORTs do CloudWatch, CSV do Log Events Viewer, prints e tempos do curl).

---

### Exercício 1.4 — Dockerfile review

Problemas do Dockerfile original:

| # | Problema | Categoria | Melhoria |
|---|----------|-----------|----------|
| 1 | `python:3.12` (imagem completa, ~1 GB) | Tamanho | `python:3.12-slim` (~150 MB) |
| 2 | `COPY . .` copia `.git`, `__pycache__`, `.env` e invalida o cache de camadas a cada mudança de código | Segurança / eficiência | `.dockerignore` e copiar o `requirements.txt` antes do código |
| 3 | `pip install` sem `--no-cache-dir` | Tamanho | `--no-cache-dir` |
| 4 | Sem multi-stage: o que serve só para build fica no runtime | Tamanho / segurança | Estágio `builder` e estágio final enxuto |
| 5 | Roda como root | Segurança | Usuário não-root (`USER app`) |
| 6 | `CMD ["python", "app.py"]` para serviço web, sem `EXPOSE` nem `HEALTHCHECK` | Boas práticas | `uvicorn` explícito, `EXPOSE 8080`, `HEALTHCHECK` |
| 7 | Base do Docker Hub, sujeita a limite de pull anônimo | Confiabilidade | Espelho `public.ecr.aws/docker/library/python` |

**Comparação com o Dockerfile do lab:** o do lab já aplica multi-stage, `slim`, `--no-cache-dir`, usuário não-root (UID 10001), base do ECR Public e `python -m uvicorn` (o `pip install --target` não coloca o executável no `PATH`). Ele não tem `HEALTHCHECK`, que a versão corrigida abaixo acrescenta.

```dockerfile
# Multi-stage: dependências no builder; só o necessário no runtime.
FROM public.ecr.aws/docker/library/python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt

FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
COPY app.py .
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

*Evidências:* `evidencias/1.4-dockerfile/` (`Dockerfile.original`, `Dockerfile.lab`, `Dockerfile.corrigido`, `.dockerignore`). 

**Medido com `docker build` (`evidencias/1.4-dockerfile/build-resultado.txt`):**

| | Original (`python:3.12`) | Corrigido |
|---|---|---|
| Tamanho da imagem | 1,79 GB | 315 MB |
| Usuário no container | `uid=0 (root)` | `uid=10001 (app)` |
| `/health` e `HEALTHCHECK` | não tem | responde `ok` e o container fica `healthy` |

O original foi buildado com a base espelhada no ECR Public, só para evitar o limite de pull; o resto do arquivo é o dele. O app exige a variável `BUCKET_NAME`; sem ela o container cai na subida, e para o teste do `/health` passamos só essa variável, sem credenciais.

---

## 🟡 Nível 2 — Respostas + Implementação

### Exercício 2.2 — Segunda tool para o agente: cálculo de frete

**a) Decisão: nova rota `GET /frete` na mesma Lambda.** Perfil igual ao do catálogo (determinística, sem estado, milissegundos); 50 mil chamadas/mês (~1,7 mil por dia) é pouco; não há Terraform novo (nada de função, URL e duas permissões a mais) e os agentes usam a mesma URL base.

**b) Implementação:** `function/v3-frete/lambda_function.py` (catálogo do S3 da v2 + `calcular_frete`). Regra:

| Faixa (distância entre o 1º dígito dos CEPs) | Base | Por kg | Prazo |
|---|---|---|---|
| Mesma região (0) | R$ 12,00 | R$ 3,00 | 2 dias |
| Região vizinha (1) | R$ 22,00 | R$ 4,00 | 4 dias |
| Região distante (2 ou mais) | R$ 35,00 | R$ 5,00 | 7 dias |

Validações (HTTP 400): CEP com 8 dígitos (aceita `01001-000`), peso numérico entre 0,1 e 30 kg (aceita vírgula).

**c) Terraform:** não muda, porque a rota entra na função existente. Só o pacote da função (`function/v3-frete/`) é novo; o `lifecycle { ignore_changes }` do lab já prevê o deploy do código pelo CLI.

**d) Tool em JSON Schema:**

```json
{
  "name": "calcular_frete_qc",
  "description": "Calcula o valor (R$) e o prazo (dias) de entrega de um pacote entre dois CEPs brasileiros. Use quando o cliente perguntar quanto custa ou quanto demora para receber um produto em um endereço. Peça o CEP de destino se ele não informou; use o peso do produto do catálogo se souber. Não use para perguntas sobre preço do produto (use buscar_produtos_qc) nem para rastrear pedido. Exemplo: origem 01001-000, destino 20040-020, peso 2,5 -> R$ 47,50 em 7 dias.",
  "input_schema": {
    "type": "object",
    "properties": {
      "origem":  {"type": "string", "description": "CEP de origem, 8 dígitos (com ou sem hífen)."},
      "destino": {"type": "string", "description": "CEP de destino, 8 dígitos (com ou sem hífen)."},
      "peso":    {"type": "number", "description": "Peso do pacote em kg, entre 0,1 e 30."}
    },
    "required": ["origem", "destino", "peso"]
  }
}
```

**e) Reflexão: separar ou manter juntas?** Mantemos juntas enquanto as funções têm o mesmo perfil: mesma permissão, escala parecida, deploy no mesmo ritmo e custo desprezível. Separamos quando muda algum desses quatro eixos: *deploy* (um time precisa publicar sem arriscar a outra rota), *permissão* (o frete passa a ler uma tabela privada, e a role do catálogo não deve enxergar isso: menor privilégio), *escala* (o frete explode na Black Friday e o catálogo não, e a concorrência de uma rota consome a cota da outra) e *custo* (uma rota precisa de muito mais memória e puxa a conta da outra). Também há o raio de dano: um bug que derruba a função derruba todas as rotas.

**Deploy e teste na AWS:** a v3 foi publicada na função `qc-aula03-uco7x2-catalogo` com `aws lambda update-function-code` (o `lifecycle.ignore_changes` do Terraform do lab ignora o código). As chamadas reais à Function URL (200 para CEPs válidos, 400 para CEP/peso inválidos) estão em `evidencias/2.2-frete/chamadas-lambda-publicada.txt`. Com a v3, `/produtos` passou a ler o catálogo do S3 (`"source": "s3"`) em vez do mock.

*Evidências:* `evidencias/2.2-frete/` (testes locais, código da versão anterior e chamadas à Lambda publicada).

---

### Exercício 2.3 — Observabilidade com CloudWatch

**a) Logs Insights** (20 chamadas variadas, 6 delas com 404; query em `evidencias/2.3-cloudwatch/query-insights.txt`). Resultado sobre o log group `/aws/lambda/qc-aula03-uco7x2-catalogo` nas últimas 3 h:

| chamadas | média (ms) | p95 (ms) | memória (MB) | frias |
|----------|-----------|----------|--------------|-------|
| 28 | 2,29 | 2,53 | 33 | 2 |

**b) Print do Lambda → Monitor** (últimas 3 h, função `qc-aula03-uco7x2-catalogo`): `evidencias/2.3-cloudwatch/monitor-invocations-duration-errors.jpg`. Invocations somou **1.052** (inclui os benchmarks do 3.2); Duration: mínimo 1,35 ms, média **32,47 ms**, máximo 188 ms; Errors: máximo **0** (taxa de sucesso 100 %); e o gráfico de execuções concorrentes marcou o pico de **49** (o benchmark).

**c) Alarme em Terraform:** `terraform/observabilidade.tf` (`aws_cloudwatch_metric_alarm`, `Errors` ≥ 1 em 5 min). Atenção: 404 devolvido pelo handler **não** é `Errors`; na nossa amostra as 4 chamadas a rotas inexistentes deram 404 e `Errors` ficou em 0. Para alertar sobre 404 seria preciso uma métrica customizada (metric filter nos logs) ou o alarme em outra camada.

**d) p95, memória e custo**

- **p95 de latência:** 2,53 ms de execução (média 2,29 ms). Isso é só o tempo dentro da função; o cliente vê cerca de 0,35 s, quase tudo rede e TLS. Nas 2 chamadas frias, o `Init Duration` foi de ~85 ms e entra na cobrança.
- **Memória:** a função usa 33 MB dos 256 MB configurados, então sobra bastante.
- **Custo de 256 para 128 MB** (1 milhão de chamadas, 2 ms cada, US$ 0,0000166667 por GB-s):

| Memória | GB-s | Custo de computação | Custo de requisições |
|---------|------|---------------------|----------------------|
| 256 MB | 500 | US$ 0,0083 | US$ 0,20 |
| 128 MB | 250 | US$ 0,0042 | US$ 0,20 |

  A economia é de uns US$ 0,004 por milhão de chamadas, desprezível: o custo está nas requisições, não na memória. Com 33 MB usados, 128 MB cabe.
- **Latência com 128 MB:** na Lambda a CPU é proporcional à memória, então com metade da memória a função tem metade da CPU. Estimamos que a execução e o `Init Duration` aumentem (talvez para perto do dobro nos trechos que dependem de CPU); **não medimos**, porque mudar a memória da função do lab geraria drift no Terraform. Para uma função de 2 ms isso não muda a experiência. Em funções mais pesadas, subir a memória pode até **reduzir** o custo, porque acaba mais rápido.

**e) Estratégia para um sistema multiagente em produção**

- **Logs:** estruturados em JSON, com um `trace_id`/`correlation_id` que passa de agente para agente e para as tools. Assim, uma conversa do usuário é reconstruída entre vários serviços no CloudWatch Logs Insights. Retenção definida (como os 7 dias do lab) e nada de dado pessoal ou segredo nos logs.
- **Métricas:** além das da plataforma (invocações, erros, duração, concorrência), métricas do negócio e do agente: tokens por conversa, latência por tool, taxa de erro de cada tool, chamadas por agente. Alarmes sobre latência p95 e erros, com ação (SNS), como o alarme do 2.3c.
- **Traces:** é onde o multiagente mais precisa, porque uma pergunta do usuário atravessa orquestrador, agentes, tools (Lambda), modelo e banco. Cada etapa vira um *span* de um trace.
- **OpenTelemetry (OTel):** padrão aberto e neutro de fornecedor para gerar logs, métricas e traces. A vantagem é instrumentar uma vez e poder trocar o destino (X-Ray, CloudWatch, Grafana, Datadog). Para agentes de IA, as convenções semânticas do OTel já cobrem chamadas a modelos.
- **AWS X-Ray:** serviço da AWS que coleta e mostra os traces (mapa de serviços, latência por segmento). Na Lambda basta ativar *active tracing*. Dá para usar o OTel (distro da AWS, ADOT) enviando para o X-Ray, e ficar com o melhor dos dois.
- **Proposta para a QC:** OTel como instrumentação, X-Ray como destino inicial, logs JSON com `trace_id` no CloudWatch e alarmes sobre os erros e a latência das tools.

*Evidências:* `evidencias/2.3-cloudwatch/` (`20-chamadas.txt`, `query-insights.txt`, `resultado-insights.json`, `metricas.txt`).


---

## 🔴 Nível 3 — Bônus

### Exercício 3.1 — A Lambda como tool de um agente

**Achado ao testar:** o filtro `preco_max` aparecia no schema do enunciado, mas **não estava implementado** na função (a chamada `categoria=moveis&preco_max=1500` devolvia 4 móveis, incluindo a mesa de R$ 2.899). Implementamos o filtro na v3 (`function/v3-frete/`), publicamos e testamos (`evidencias/3.1-tool-agente/preco-max-na-lambda.txt`). Esse é exatamente o tipo de divergência entre descrição da tool e endpoint que o item (d) quer evitar.

**a) Descrição da tool** (arquivo completo e validado: `evidencias/3.1-tool-agente/buscar_produtos_qc.json`):

```json
{
  "name": "buscar_produtos_qc",
  "description": "Busca produtos no catálogo da Quantum Commerce (QC) e devolve nome, descrição, categoria, preço em R$ e estoque. Use quando o cliente quiser achar, comparar ou saber o preço ou a disponibilidade de um produto que a QC vende. Combine os filtros que a pergunta permitir; todos são opcionais e se somam (E). Sem filtros, devolve o catálogo inteiro (20 itens): evite, prefira filtrar. NÃO use para pedidos, rastreio, devolução, pagamento ou frete (existem outras tools) nem para perguntas gerais que não dependem do catálogo. Regras dos filtros: `categoria` aceita exatamente uma de: moveis, eletronicos, eletrodomesticos, calcados, acessorios, vestuario (minúsculas, sem acento). `nome` é uma busca por trecho no nome do produto, sem acento e em minúsculas, com UMA palavra-chave curta: use 'cafe' (acha 'Cafeteira'), nunca 'café' nem a frase inteira do cliente. `preco_max` é o preço máximo em reais, número sem 'R$'. Se `total` vier 0, diga ao cliente que não encontrou e sugira relaxar um filtro (tire o preço ou a categoria); nunca invente produtos nem preços. Exemplos: 'cadeira até 1500' -> {\"categoria\":\"moveis\",\"nome\":\"cadeira\",\"preco_max\":1500}; 'quanto custa o Galaxy S24' -> {\"nome\":\"galaxy\"}; 'algo para café' -> {\"nome\":\"cafe\"}.",
  "input_schema": {
    "type": "object",
    "properties": {
      "categoria": {"type": "string", "enum": ["moveis","eletronicos","eletrodomesticos","calcados","acessorios","vestuario"], "description": "Categoria exata, minúscula e sem acento. Omita se o cliente não indicou o tipo de produto."},
      "preco_max": {"type": "number", "description": "Preço máximo em reais (ex.: 1500 para 'até R$ 1.500'). Omita se não houver orçamento."},
      "nome": {"type": "string", "description": "Uma palavra-chave do nome, minúscula e sem acento (ex.: 'galaxy', 'cadeira', 'cafe'). Não use a frase inteira."}
    },
    "required": []
  }
}
```

Por que está assim: o `enum` impede o agente de inventar categorias; a regra "sem acento, uma palavra" existe porque `nome` é busca por trecho (`cafe` acha "Cafeteira", `café` não); e a instrução para `total = 0` evita que ele invente produto.

**b) Três conversas** (resultados reais da Function URL, em `evidencias/3.1-tool-agente/exemplos-das-conversas.txt`):

1. **"Tem cadeira boa para home office?"**
   - Chamada: `buscar_produtos_qc({"categoria": "moveis", "nome": "cadeira"})`
   - Retorno: 3 cadeiras — Ergonômica DXRacer (R$ 1.499,90), Gamer Vermelha (R$ 1.299,00), Home Office Confortável (R$ 799,00).
   - Resposta: "Tenho 3 opções. Para home office, a **Cadeira Ergonômica DXRacer** (R$ 1.499,90) tem apoio lombar regulável e encosto de cabeça; a **Home Office Confortável** (R$ 799,00) tem regulagem de altura e é a mais em conta. Quer que eu filtre por um orçamento?"
2. **"Quanto custa o Galaxy S24?"**
   - Chamada: `buscar_produtos_qc({"nome": "galaxy"})`
   - Retorno: 1 produto, Smartphone Samsung Galaxy S24, R$ 3.999,00, 12 em estoque.
   - Resposta: "O Samsung Galaxy S24 (128 GB, câmera tripla de 50 MP) custa **R$ 3.999,00** e tem 12 unidades em estoque."
3. **"Preciso de algo para café"**
   - Chamada: `buscar_produtos_qc({"nome": "cafe"})` (sem acento)
   - Retorno: Cafeteira Nespresso Essenza Mini (R$ 499,00) e Cafeteira Italiana 6 Xícaras (R$ 89,90).
   - Resposta: "Tenho duas: a **Nespresso Essenza Mini** (R$ 499,00, cápsulas, aquece em 25 s) e a **Italiana de 6 xícaras** (R$ 89,90, a mais barata). Você prefere cápsula ou café coado na hora?"

**c) Quando o agente NÃO deve chamar a tool, mesmo falando de produto:**

1. **"Meu pedido da cadeira ainda não chegou."** Fala de produto, mas é rastreio de um pedido. O catálogo não tem pedido nenhum; chamar a tool devolveria a cadeira e confundiria o cliente. O caminho é outra tool (pedidos) ou o atendimento.
2. **"Qual a diferença entre esses dois?"**, logo depois de o agente já ter listado os produtos. Preço, descrição e estoque já estão no contexto; chamar de novo gasta uma invocação (e tokens) à toa e arrisca mostrar um estoque diferente do que acabou de dizer. Também não chama para perguntas gerais ("o que é bom em notebook, em geral?"): o catálogo só responde o que a QC vende.

**d) Como manter a descrição sincronizada com o endpoint:**

- **Contrato como fonte da verdade:** escrever um **OpenAPI** do endpoint e **gerar** o `input_schema` e a lista de categorias a partir dele, em vez de manter dois textos à mão.
- **Contract test no CI:** um teste que lê o JSON da tool, monta chamadas a partir dos exemplos e dos parâmetros, e as executa contra a Function URL (dev), conferindo o status e os campos. O `preco_max` desta entrega teria sido pego aqui: o schema o declarava e o endpoint o ignorava.
- **Versionamento:** versão no nome ou na rota (`/v1/produtos`) e no JSON da tool; mudança que quebra gera `v2` e a `v1` convive até os agentes migrarem. Mudança compatível (parâmetro opcional novo) pode entrar na mesma versão.
- **Alterar junto:** código, OpenAPI e descrição da tool no mesmo PR, com um CHANGELOG, e o `enum` de categorias gerado a partir dos dados, não digitado.
- **Observabilidade:** logar os parâmetros que o agente enviou; erros 400 e buscas com `total = 0` frequentes são sinal de que a descrição está ensinando errado.

*Evidências:* `evidencias/3.1-tool-agente/`.

### Exercício 3.2 — Benchmark de carga

`ab -n 1000 -c 50 ".../produtos?categoria=moveis"` contra a Lambda (Function URL, HTTPS) e contra a tarefa Fargate (0,25 vCPU / 0,5 GB, HTTP na porta 8080, sem load balancer). Saídas completas: `evidencias/3.2-benchmark/ab-lambda.txt` e `ab-fargate.txt`; métricas em `metricas-cloudwatch.txt`.

| Métrica | Lambda | ECS Fargate |
|---------|--------|-------------|
| Latência média (por requisição) | 514 ms | 1.094 ms |
| p50 | 477 ms | 1.030 ms |
| p95 | 561 ms | 1.983 ms |
| p99 | 1.292 ms | 2.298 ms |
| Throughput | 85,5 req/s | 44,6 req/s |
| Erros (falhas / não-2xx) | 0 / 0 | 0 / 0 |
| Custo aprox. por 1M req | US$ 0,46 (US$ 0,20 + computação: 61 ms cobrados, 256 MB) | US$ 9,01 se o tráfego for 1M/mês (tarefa 24/7); ~US$ 0,08 por 1M se ficasse saturada |

**Ressalva de método:** rodamos o `ab` do Mac do grupo, e não do CloudShell. O `Connect` da Lambda foi ~320 ms (viagem até `us-east-1` + handshake TLS) contra ~118 ms do Fargate (HTTP puro), então as latências absolutas incluem rede e não são as de dentro da AWS. A diferença no tempo de processamento (`Processing`: média de 189 ms na Lambda e 976 ms no Fargate) não depende disso.

**a) Qual aguentou melhor? Por quê?** A Lambda: o dobro de vazão e ~2× menos latência. A métrica `ConcurrentExecutions` chegou a **49**: a Lambda criou uma instância por requisição simultânea (47 partidas frias, que explicam o p99 de 1,3 s). O Fargate tem **uma** tarefa de 0,25 vCPU atendendo as 50 conexões ao mesmo tempo (cada `/produtos` lê o CSV no S3), então as requisições enfileiram e a latência cresce. *(Confirmado depois: numa segunda carga de 5.000 requisições contra o mesmo Fargate, a métrica `CPUUtilization` chegou a **100 %** (média de 81,6 % no minuto do pico), com vazão de 41 req/s e p95 de 2,1 s: `evidencias/3.2-benchmark/cpu-fargate-segunda-carga.txt` e `evidencias/3.4-fargate/ab-carga-autoscaling.txt`. A tarefa de 0,25 vCPU estava saturada.)*

**b) Em qual cenário cada um venceria?** A Lambda vence com tráfego em picos e ocioso boa parte do tempo (paga por chamada, custo zero parada, escala sozinha) e quando o cold start é aceitável. O Fargate vence com tráfego **constante e alto** (a US$ 9 por mês a tarefa só compensa se for bem usada: saturada, sai a ~US$ 0,08 por milhão), com latência previsível sem cold start, requisições longas (> 15 min), e quando precisa de conexões persistentes ou controle fino de rede.

**c) Black Friday (10× tráfego):** manter a Lambda para a API de busca, com **concorrência reservada** (para não consumir a cota da conta) e **provisioned concurrency** só nas horas de pico, para eliminar o cold start; CloudFront na frente para cachear respostas do catálogo, que muda pouco; e leitura do catálogo fora do caminho quente (cache em memória na instância, ou DynamoDB/ElastiCache). Para o checkout, serviço Fargate com **auto scaling** e um **ALB** na frente, com mínimo de 2 tarefas em AZs diferentes, e teste de carga prévio.

*Evidências:* `evidencias/3.2-benchmark/`.

### Exercício 3.3 — A Lambda pelas telas da AWS (e o drift)

**Feito no console (Chrome), na conta do lab:** criamos a função `demo-estoque` (Python 3.15, execution role **LabRole** escolhida em *Additional settings → Custom execution role*), colamos o código do lab, clicamos em **Deploy** ("Successfully updated the function") e rodamos um teste com o evento `{"produto_id": "P001", "armazem_id": "SP"}`: **Status: Succeeded**, `statusCode` 200. O log da função confirma o evento e que foi chamada fria (`Init Duration: 96,23 ms`, 99 ms cobrados, 128 MB, 35 MB usados). Prints em `evidencias/3.3-console/` (`01-funcao-criada.jpg`, `02-codigo-colado-deploy.jpg`, `03-teste-console-succeeded.jpg`) e logs em `logs-demo-estoque.txt` e `config-demo-estoque.json`.

**Pendente:** a Function URL pública (passo 6 do roteiro, *Auth type NONE*). A criação foi **bloqueada pelo modo automático do Claude Code** e não a contornamos; fica para o grupo criar manualmente no console (Configuration → Function URL).

**a) O que o Terraform fazia por nós, e o que esqueceríamos pelas telas?** O Terraform declara tudo em um lugar só: a função (com role, runtime, memória, timeout e variáveis), o **log group com 7 dias de retenção**, a **Function URL** e as **duas permissões** (`InvokeFunctionUrl` e `InvokeFunction`), o pacote do código e a **limpeza** (`destroy` apaga tudo). Pelas telas, o que mais se esquece: a **retenção do log group** (a Lambda cria o grupo sozinha, sem expiração, e o log cobra armazenamento para sempre), as **duas permissões** da URL (o console cria, mas quem copia a configuração à mão esquece uma e recebe `Forbidden`), a **limpeza** (apagar a função não apaga o log group) e o registro do *por que* de cada escolha (ninguém sabe depois quem mudou a memória, quando e por quê). O Terraform também é repetível: o mesmo código cria o mesmo ambiente em outra conta.

**b) Drift:** mudamos a memória da Lambda do lab de 256 para 512 MB fora do Terraform (`aws lambda update-function-configuration`, o mesmo efeito de editar *General configuration* no console) e conferimos na AWS: o recurso real passou a ter 512 MB enquanto o `lambda.tf` continua declarando `memory_size = 256` (saída em `evidencias/3.3-console/drift-memoria-cli.txt`). Depois devolvemos a 256 MB.

> **Importante, sobre a evidência:** não rodamos o `terraform plan` real (o Terraform não está instalado no ambiente e o estado do lab está na conta de outro usuário). O trecho abaixo é o que o plano **deve** mostrar, com base no `lambda.tf`; **não é uma saída real**. Se o grupo tiver o estado, vale substituir pelo `terraform plan` verdadeiro.

```
  # aws_lambda_function.catalogo will be updated in-place
  ~ resource "aws_lambda_function" "catalogo" {
      ~ memory_size = 512 -> 256
        # (demais atributos sem mudança; filename e source_code_hash são ignorados por lifecycle.ignore_changes)
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

**O que acontece no `terraform apply`:** ele **desfaz a mudança manual** e volta a memória para 256 MB: o código vence o console. **Por que importa num time:** se uma pessoa sobe a memória no console para resolver um problema de timeout à noite e ninguém registra, o próximo `apply` (de outra pessoa, por outro motivo) derruba a correção sem aviso, e o problema volta. O contrário também acontece: o ambiente real passa a ter configurações que ninguém sabe explicar nem recriar. Por isso a mudança deve entrar no código, em PR, e o `plan` deve rodar no CI para o drift aparecer cedo. Observe que o `lifecycle.ignore_changes` do lab só cobre o código (`filename`, `source_code_hash`), então a memória **é** vigiada pelo Terraform.

**c) Quando criar pelas telas e quando não:** faz sentido para **explorar e aprender** (testar um evento, ver o log de uma função descartável, descobrir o que uma opção faz) e para **investigação pontual** de um incidente; por exemplo, aqui, criar a `demo-estoque` para ver o que uma Lambda precisa. **Não faz sentido** para qualquer coisa que o time precisa **recriar, revisar ou auditar**: a API de checkout, a role de produção, o log group com retenção. Isso vai para o Terraform, em PR e com revisão, para que o ambiente real seja igual ao do repositório.

*Evidências:* `evidencias/3.3-console/`.

### Exercício 3.4 — Fargate em produção: restart, sizing e segredos

Terraform completo dos itens (a) a (d): `terraform/containers-evolucao.tf`. **Atenção sobre o que foi validado:** o Terraform não foi aplicado (não está instalado); os itens foram exercitados na AWS pela CLI (a sessão do Learner Lab expirou uma vez no meio, com `explicit deny ... voc-cancel-cred`, e foi reiniciada). O que foi e o que não foi verificado está marcado em cada item.

**a) Serviço × tarefa avulsa (job batch).** O lab usa um **serviço**: o ECS mantém `desired_count` tarefas e **recria** a que cair. Para o job noturno de recomendações usamos um **`aws_scheduler_schedule`** que dispara `RunTask`: a tarefa roda, termina e **para de cobrar**. Criamos na AWS um agendamento de execução única (`at(...)`, `ActionAfterCompletion=DELETE`) chamando `RunTask` com `containerOverrides` (`evidencias/3.4-fargate/scheduler-target.json` e `scheduler-criado.txt`): **a tarefa rodou:** iniciou às 00:53:41 e terminou às 00:54:04 UTC com `exitCode 0` (`job-agendado-resultado.txt`), e o agendamento **se apagou sozinho** depois de executar (`ActionAfterCompletion=DELETE`). **Quando usar cada um:** *serviço* para algo que precisa estar **sempre no ar** e responder (API do checkout, que o ECS reinicia se cair); *tarefa agendada* para trabalho com **começo e fim** (recalcular recomendações, gerar notas fiscais, extrair dados), sem pagar pelo tempo ocioso.

**b) Right-sizing e custo.** Variante de 1 vCPU / 2 GB no Terraform (`produtos_api_grande`). Custos na calculadora AWS (us-east-1, Linux x86, taxas de US$ 0,04048 por vCPU-hora e US$ 0,004445 por GB-hora; prints em `evidencias/2.1-calculadora/`), para **1 tarefa 24/7** (730 h):

| | 0,25 vCPU / 0,5 GB | 1 vCPU / 2 GB |
|---|---|---|
| Custo/mês | US$ 9,01 | US$ 36,04 (confirmado na calculadora) |
| Lambda equivalente, 1M chamadas/mês | US$ 0,21 na calculadora (3 ms, 256 MB; US$ 0,46 com a duração real cobrada no benchmark) | idem |

A Lambda é de **20 a 170 vezes mais barata** para 1M chamadas por mês; o Fargate só compensa com tráfego constante e alto (no benchmark, uma tarefa de 0,25 vCPU atendeu 44,6 req/s, ou ~117M req/mês saturada, ~US$ 0,08 por milhão), ou quando as outras vantagens (sem cold start, tempo de execução longo, controle de rede) pesam. **Dimensionar para cima nem sempre é a resposta:** no benchmark, o gargalo era a CPU de uma única tarefa; mais tarefas (item d) ou mais CPU resolvem, mas o custo escala linearmente.

**c) Segredo na task definition.** Criamos o segredo `qc-aula03/chave-teste` no Secrets Manager (valor fictício) e duas task definitions de comparação (`evidencias/3.4-fargate/taskdef-segredo.json`). O `aws ecs describe-task-definition` (`describe-task-definition-segredo.txt`) mostra a diferença:

```
"environment": [ { "name": "CHAVE_EM_TEXTO_PURO", "value": "valor-fake-so-para-teste-123" } ]   ← valor VISÍVEL
"secrets":     [ { "name": "CHAVE_VIA_SECRETS",   "valueFrom": "arn:aws:secretsmanager:us-east-1:...:secret:qc-aula03/chave-teste-GIMOTn" } ]   ← só o ARN
```

Com `environment`, quem tem `ecs:DescribeTaskDefinition` (ou lê o repositório do Terraform) vê o segredo; com `secrets`, só o **ARN**: o ECS busca o valor na hora de iniciar a tarefa, usando a execution role (que precisa de `secretsmanager:GetSecretValue` nesse segredo). **Injeção confirmada:** rodamos uma tarefa que só sai com código 0 se `CHAVE_VIA_SECRETS` chegar com o valor correto, e ela terminou com `exitCode 0` (`run-task-segredo-resultado.txt`): o ECS buscou o valor no Secrets Manager e o entregou ao container, sem ele aparecer na task definition.

**d) Escala.** O serviço do lab tem `desired_count = 1` e **nenhum auto scaling**: num pico de Black Friday, a única tarefa satura a CPU (como vimos no benchmark: p95 de 2 s com 50 conexões) e o serviço **não cria tarefas novas**; ele só repõe a tarefa se ela cair. Escrevemos o `aws_appautoscaling_target` (1 a 4 tarefas) e a `aws_appautoscaling_policy` de *target tracking* em **CPU 60 %** (`containers-evolucao.tf`). O mesmo alvo e a mesma política (1 a 4 tarefas, CPU 60 %) foram registrados na AWS pela CLI (`autoscaling-cli.txt`). **Teste real:** com uma carga sustentada de ~7 min (16.000 requisições, `ab -c 50`), o alarme de CPU do *target tracking* disparou às 01:07:51 UTC e o serviço passou de 1 para **2 tarefas**, a segunda com **outro IP público** (`autoscaling-resultado.txt`, `carga-sustentada.txt`). Enquanto isso, a vazão **não melhorou** (38 req/s, p95 de 2,2 s): o cliente continuou batendo no IP da primeira tarefa. Esse é o ponto do ALB, demonstrado: o escalonamento criou capacidade, mas nada a usou. O auto scaling também reage com atraso (foram ~6 minutos de carga até agir), o que importa para picos súbitos de Black Friday. **Por que, sem load balancer, escalar não basta:** o lab expõe **o IP público da tarefa**. Uma nova tarefa ganha **outro IP**; nada distribui o tráfego entre elas, e os clientes continuam batendo na primeira. Sem um **ALB** (com *target group* e health check) na frente, ter 4 tarefas é pagar por 4 e usar 1. Além disso, o IP muda a cada tarefa recriada, o que quebra qualquer cliente que o tenha guardado.

**e) Reflexão: Fargate ou Lambda para a QC?**

| Carga | Casa | Por quê |
|---|---|---|
| Busca no catálogo, frete | **Lambda** | Picos e parada; ~US$ 0,2 por milhão contra ~US$ 9 por mês parado no Fargate; escala sozinha; HTTPS pela Function URL; cold start de ~90 ms é aceitável. |
| Notas fiscais (noturna) | **Fargate agendado** | Passa dos 15 min; paga só o tempo rodado; sem serviço ocioso. |
| Recomendação | **Fargate** | Modelo em memória, respostas de segundos; evita cold start. |
| Checkout | **Fargate (2+ tarefas atrás de ALB)** | Tráfego constante e crítico; sem cold start; auto scaling e health check. |

Critérios: **custo parado** (Lambda zero; Fargate cobra 24/7), **HTTPS** (Lambda dá pela Function URL; Fargate exige ALB, certificado e DNS), **escala** (Lambda automática por requisição; Fargate precisa de política e de ALB) e **simplicidade operacional** (Lambda não tem imagem, rede nem patch de SO; Fargate tem Dockerfile, ECR, VPC e health checks). Regra prática: **Lambda por padrão; Fargate quando o tempo de execução, o tráfego constante ou o cold start deixam de ser aceitáveis.**

*Evidências:* `evidencias/3.4-fargate/`.


---

## Reflexão coletiva

> *Rascunho para o grupo revisar e ajustar com as próprias palavras; a linha de cada membro está no `canvas-compute.md`.*

**1. O que aprendemos de mais importante.** Que a escolha entre Lambda e container não é de tecnologia, mas de **forma de carga**, e que dá para medir. No benchmark, a Lambda atendeu 85 req/s e escalou até 49 execuções concorrentes; uma tarefa Fargate de 0,25 vCPU atendeu 44 req/s e chegou a 100 % de CPU. Em dinheiro, a mesma busca custa ~US$ 0,2 por milhão de chamadas na Lambda e ~US$ 9 por mês parada no Fargate. Aprendemos também que o **cold start é uma propriedade do código**, não só da plataforma: ele subiu de ~85 ms para ~494 ms quando a função passou a importar o `boto3` e ler o S3, e uma função chamada a cada hora esfria sempre. E que a **identidade** importa tanto quanto o desempenho: a LabRole pode muito mais do que ler o catálogo, e uma policy mínima (`s3:GetObject` no `catalogo/*`) limita o estrago de uma falha.

**2. Conexão com a arquitetura cloud de uma plataforma agentic.** Para o agente, cada função é uma **tool**, e o contrato entre os dois é a descrição da tool. Ao escrevê-la, descobrimos que o `preco_max` existia no schema mas **não no endpoint**: um agente teria recebido resultados que ignoravam o orçamento do cliente, sem erro nenhum. Isso mostra que, num sistema multiagente, a descrição e a API precisam ser versionadas e testadas juntas (OpenAPI e contract tests). A escolha da casa muda a experiência do agente: uma tool em Lambda pode responder em ~1,2 s na primeira chamada depois de ociosa, e o agente (e a UX) precisa tolerar isso; uma tool em Fargate responde de forma estável, mas custa parada e precisa de ALB, health check e auto scaling para escalar de verdade. Vimos isso na prática: o auto scaling criou uma segunda tarefa, com outro IP, e a vazão não melhorou porque nada distribuía o tráfego.

**3. O que faríamos diferente se começássemos hoje.** (i) Teríamos **tudo em código desde o primeiro dia**: o drift da memória da Lambda mostrou que o que se cria pelas telas fica invisível e é desfeito no próximo `apply`; usaríamos o console só para explorar. (ii) Colocaríamos um **contract test** entre a tool e o endpoint desde a primeira versão, e **observabilidade** (logs JSON com `trace_id`, alarmes e OpenTelemetry/X-Ray) antes de adicionar o segundo agente, porque o alarme sobre `Errors` não pega um 404 devolvido pelo handler e só uma métrica de negócio pegaria. (iii) Faríamos o benchmark **de dentro da AWS** (CloudShell), para não misturar a latência de rede com a do serviço. (iv) Adotaríamos como regra: **Lambda por padrão** (busca, frete), **Fargate** quando o tempo de execução, o tráfego constante ou o cold start deixarem de ser aceitáveis (notas fiscais noturnas, recomendação, checkout atrás de ALB), com roles próprias de menor privilégio em vez da LabRole.

---

## Artefatos do ZIP

- Código IaC: `terraform/`
- Função: `function/`
- Canvas: `canvas-compute.md`
