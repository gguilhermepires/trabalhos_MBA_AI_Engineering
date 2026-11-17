# Canvas de compute — Quantum Commerce

**Grupo:** 01 · **Entrega 03 · N2**

Uma linha por carga de trabalho. As colunas são as perguntas que decidem onde ela roda; a última é a decisão.

| Coluna | A pergunta por trás |
|--------|---------------------|
| Como é chamada | Por HTTP (o agente, o site), por evento (fila, arquivo novo) ou por agenda? |
| Quanto tempo roda | Milissegundos, minutos ou horas? (a Lambda para em 15 minutos) |
| Tráfego | Em picos, constante ou parado boa parte do dia? |
| Espera 1 s? | O usuário aguenta esperar a primeira chamada (cold start)? |
| Identidade | Com que role ela roda, e o que essa role pode ler? Só o necessário? |
| Custo/mês | Estimativa na [calculadora AWS](https://calculator.aws), região `us-east-1`, na casa escolhida e na outra |
| Onde roda e por quê | Lambda, Fargate ou outro + uma frase de justificativa (e o que vocês **não** usariam) |

## As 5 cargas da QC

A primeira linha é o exemplo feito em sala.

| Carga | Como é chamada | Quanto tempo roda | Tráfego | Espera 1 s? | Identidade | Custo/mês | Onde roda e por quê |
|-------|----------------|-------------------|---------|-------------|------------|-----------|---------------------|
| Busca no catálogo (`buscar_produtos`) | O agente, por HTTP | < 1 s (~3 ms medidos) | Picos; parada de madrugada | Sim | Só `s3:GetObject` no `catalogo/*` | **Lambda US$ 0,21** (1M req, 3 ms, 256 MB) · Fargate 0,25 vCPU/0,5 GB 24/7 US$ 9,01 | Lambda: paga por chamada e parada custa zero. Não usaria Fargate 24/7, que cobra parado. |
| Cálculo de frete | O agente, por HTTP | ~3 ms | 50 mil/mês, estável | Sim | Nenhuma permissão além dos logs (não lê S3 nem banco) | **Lambda US$ 0,01** (50 mil req) · Fargate 0,25 vCPU 24/7 US$ 9,01 | Lambda, na mesma função do catálogo: determinística e sem estado. Não usaria container dedicado. |
| Notas fiscais (geração noturna) | Por agenda (EventBridge Scheduler) | ~1 h | 1 vez por noite | Sim (ninguém espera) | Ler pedidos do dia e escrever as notas no bucket/banco fiscal | **Fargate US$ 1,48** (1 vCPU/2 GB, 30 h/mês) · Lambda inviável (limite de 15 min) | Fargate com RunTask agendado: passa dos 15 min e paga só pelo tempo rodado. Não usaria Lambda nem serviço 24/7. |
| Recomendação de produtos | O agente, por HTTP | 1–5 s (modelo) | Picos de uso | Não | Ler catálogo e histórico; invocar o modelo | **Fargate US$ 36,04** (1 vCPU/2 GB 24/7) · Lambda US$ 20,04 (hipótese: 200 mil req, 3 s, 2 GB, sem concorrência provisionada) | Fargate: o modelo fica carregado na memória e não há cold start de vários segundos. A Lambda é mais barata no papel, mas a primeira chamada fria quebra a UX. Não usaria Lambda sem concorrência provisionada. |
| Checkout | O site, por HTTP | 100–500 ms | Constante e crítico | Não | Escrever pedido e pagamento; segredo no Secrets Manager | **Fargate US$ 36,04** (2 tarefas de 0,5 vCPU/1 GB, 24/7) · Lambda US$ 5,40 (hipótese: 2M req, 300 ms, 512 MB, sem concorrência provisionada) | Fargate com 2 tarefas em AZs diferentes: sem cold start, controle fino e tráfego constante dilui o custo. A Lambda custa menos, mas o cold start no pagamento não é aceitável. Não usaria EKS: 100 req/s não justifica operar Kubernetes. |

> **Como os custos foram obtidos:** a calculadora AWS (us-east-1, sem free tier, Linux x86) confirmou a Lambda de busca (US$ 0,21) e o Fargate de 1 vCPU/2 GB 24/7 (US$ 36,04), com as taxas de US$ 0,04048 por vCPU-hora e US$ 0,004445 por GB-hora. As outras linhas usam essas mesmas taxas (`evidencias/2.1-calculadora/calculos-derivados.txt`). Os volumes de recomendação e checkout são hipóteses nossas. Prints em `evidencias/2.1-calculadora/`.

## Uma linha do trabalho de vocês

Cada membro do grupo, uma linha com uma carga real do próprio trabalho. Anonimizem nomes, sistemas, números e clientes.

| Membro | Carga | Como é chamada | Quanto tempo roda | Tráfego | Espera 1 s? | Identidade | Custo/mês | Onde roda hoje — e onde deveria rodar |
|--------|-------|----------------|-------------------|---------|-------------|------------|-----------|---------------------------------------|
| Guilherme Augusto Veiga Pires | API de cadastro e mensalidades de uma associação (NestJS + banco relacional gerenciado) | O site (front estático), por HTTP | 50–500 ms por chamada; envio de e-mail de alguns segundos | Baixo e em picos (horário comercial); parada à noite | Hoje não: o primeiro acesso depois de ociosa leva 30–60 s (hibernação do plano gratuito). Aceitável só para uso interno | String de conexão do banco e credencial do e-mail em variáveis de ambiente do host; sem role de nuvem | **Hoje US$ 0** (plano gratuito) · Lambda ~US$ 0,20 por 1M req (estimativa nossa) · Fargate 0,25 vCPU/0,5 GB 24/7 US$ 9,01 | Hoje num container em PaaS gratuito. Deveria ir para Lambda (tráfego baixo e em picos, custo parado zero), com as credenciais no Secrets Manager lidas pela execution role; o cold start do ORM (centenas de ms) é aceitável, e o do plano atual (30–60 s) não é. Não usaria Fargate 24/7 para esse volume. |
| Somario Canuto da Silva | Fechamento noturno de relatórios gerenciais de uma área de negócio | Por agenda (1 vez por noite) | ~40 min | Uma execução por noite; parada o resto do dia | Sim (ninguém espera) | Ler as tabelas do dia e gravar os relatórios em um bucket; credencial do banco no Secrets Manager | **Fargate US$ 1,48** (1 vCPU/2 GB, 30 h/mês, mesmas taxas do canvas) · Lambda inviável (passa dos 15 min) | Hoje num servidor sempre ligado, com cron. Deveria ir para Fargate com RunTask agendado (EventBridge Scheduler): paga só os ~40 min e libera o servidor. Não usaria Lambda (limite de 15 min) nem serviço 24/7. |
| Cinara Nubia Silva | Processamento de documentos enviados por clientes (extrair dados de PDFs) | Por evento (arquivo novo no bucket) | ~2 s por arquivo | Em rajadas, ~20 mil arquivos por mês, quase nenhum à noite | Sim (processamento em segundo plano) | Ler o arquivo do prefixo de entrada e gravar o resultado no de saída; nada além disso | **Lambda US$ 0,67** (20 mil req, 2 s, 1 GB) · Fargate worker 0,5 vCPU/1 GB 24/7 US$ 18,02 | Hoje num worker sempre ligado que consulta a pasta. Deveria ir para Lambda com gatilho S3 (ou S3 → SQS → Lambda): escala por arquivo e custa zero parada. Não usaria um serviço 24/7 para um volume tão baixo. |
