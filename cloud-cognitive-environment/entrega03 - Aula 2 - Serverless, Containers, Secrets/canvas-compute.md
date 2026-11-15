# Canvas de compute — Quantum Commerce

**Grupo:** NN · **Entrega 03 · N2**

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
| | | | | | | | | |
