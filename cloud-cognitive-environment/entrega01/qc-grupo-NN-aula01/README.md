# Entrega 01 — Aula 01 (Fundamentos & IaC) — Grupo <NN>

Conteúdo deste ZIP:

- `entrega-grupo-aula01.md`: documento principal (N1, N2, N3 e reflexão).
- `diagramas/arquitetura-qc-aula01.png`: diagrama do Exercício 2.1 (fonte em `.svg`).
- `terraform/`: Exercício 3.1 (lab com SSH restrito ao seu IP + `sg-app`).
- `cloudformation/template.yaml`: Exercício 3.2.
- `evidencias/`: capturas de tela de cada passo do N3, executado no AWS Learner Lab (citadas no documento como E-00 a E-13).

## Como rodar o Terraform (AWS CloudShell)

```bash
export PATH="$HOME/bin:$PATH"          # Terraform instalado pelo script do lab
test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
cd terraform
terraform init
terraform plan  -var "meu_ip=$(curl -s https://checkip.amazonaws.com)"
terraform apply -var "meu_ip=$(curl -s https://checkip.amazonaws.com)"
terraform output public_ip_address
terraform destroy -var "meu_ip=$(curl -s https://checkip.amazonaws.com)"   # sempre ao final
```

Para ver o diff do exercício (SSH `0.0.0.0/0` → `/32`), aplique primeiro o `main.tf` original do lab e depois este; o `plan` deve mostrar o security group alterado in-place e a EC2 **sem** recriação.

## Como rodar o CloudFormation (AWS CloudShell)

```bash
cd cloudformation
aws cloudformation validate-template --template-body file://template.yaml
aws cloudformation deploy --stack-name aula01-grupo --template-file template.yaml \
  --parameter-overrides SshCidr="$(curl -s https://checkip.amazonaws.com)/32"
aws cloudformation describe-stacks --stack-name aula01-grupo --query "Stacks[0].Outputs"
aws cloudformation detect-stack-drift --stack-name aula01-grupo
aws cloudformation delete-stack --stack-name aula01-grupo      # sempre ao final
```

Nenhum segredo está no código. Não inclua `terraform.tfstate*`, `.terraform/`, `.env` nem `*.pem` no ZIP.
