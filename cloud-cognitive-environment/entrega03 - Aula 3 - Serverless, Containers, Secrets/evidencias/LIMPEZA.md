# Limpeza ao final (Learner Lab, conta 924438851703, us-east-1)

## Já existiam (criados pelo Terraform do lab) — confirmar com o usuário antes de apagar
- Lambda `qc-aula03-uco7x2-catalogo` + Function URL + permissões + log group `/aws/lambda/qc-aula03-uco7x2-catalogo`
- Bucket S3 `qc-aula03-uco7x2-catalogo`

## Criados por nós nesta entrega — apagar no final
- Código da Lambda `qc-aula03-uco7x2-catalogo` trocado para a v3-frete em 2026-11-13 00:06 UTC (versão anterior, v1-mock, em evidencias/2.2-frete/lambda-publicada-ANTES-v1-mock.py). Não é um recurso novo; ao apagar a função isto some junto.

## Local
- Arquivo de credenciais temporário no scratchpad (apagar)
- Imagem Docker `qc-corrigido`

## Navegador
- Aba da calculadora AWS foi fechada; a estimativa não foi salva nem compartilhada (só existe na sessão da aba).

## Criados por nós (2026-11-13) — APAGAR no final
- ECS service `produtos-api` no cluster `qc-aula03-uco7x2-cluster` (desired=1; depois escalar a 0 e deletar com --force)
- Task definition `qc-aula03-uco7x2-produtos-api:2` (deregister) e as revisões que o 3.4 criar
- Imagem `produtos-api:bench1` no ECR (repositório já existia, vazio; apagar a imagem)
- Lambda `demo-estoque` (3.3, criada pelo console) + Function URL + log group `/aws/lambda/demo-estoque` (NÃO fazem parte do Terraform: apagar função e log group)
- EventBridge Scheduler `qc-aula03-job-recomendacoes` (se ainda existir; one-shot com DELETE automático)
- Secrets Manager `qc-aula03/chave-teste` (apagar com --force-delete-without-recovery)
- Task definition family `qc-aula03-uco7x2-produtos-api-segredo` (deregister)

## STATUS FINAL (2026-11-13 01:10 UTC): limpeza FEITA (log em LIMPEZA-executada.txt)
Apagado: serviço ECS, auto scaling, task definitions (INACTIVE), imagens do ECR, segredo, `demo-estoque` + log group, schedule (se apagou sozinho), imagens Docker locais, credenciais temporárias.
Mantido (já existia no lab, criado pelo Terraform): Lambda `qc-aula03-uco7x2-catalogo` (agora com o código v3-frete; a v1-mock está em 2.2-frete/), bucket `qc-aula03-uco7x2-catalogo`, cluster ECS, repositório ECR (vazio), security group, log groups. Para apagar tudo: `terraform destroy` no lab, pelo grupo.
