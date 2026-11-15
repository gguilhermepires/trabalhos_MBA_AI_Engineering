variable "region" {
  description = "Região da AWS (o Learner Lab libera us-east-1 e us-west-2)"
  type        = string
  default     = "us-east-1"
}

variable "stack_name" {
  description = "Valor da tag 'stack', usada pelo Resource Group para achar os recursos"
  type        = string
  default     = "iac-aula01"
}

variable "vm_name" {
  description = "Nome da instância EC2 (tag Name)"
  type        = string
  default     = "vm-lab-aula01"
}

variable "instance_type" {
  description = "Tipo da instância (o Learner Lab aceita de nano a large)"
  type        = string
  default     = "t3.micro"
}

variable "meu_ip" {
  description = "Seu IP público (sem /32). No CloudShell: curl -s https://checkip.amazonaws.com. Sem default de propósito: o SSH nunca fica aberto por esquecimento."
  type        = string

  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", var.meu_ip))
    error_message = "meu_ip deve ser um IPv4 simples, ex.: 203.0.113.10 (sem /32)."
  }
}

variable "app_port" {
  description = "Porta da futura camada de aplicação, aceita só vinda do security group da VM"
  type        = number
  default     = 8080
}

variable "ssh_public_key_path" {
  description = "Chave pública SSH usada no key pair (no CloudShell: ~/.ssh/id_rsa.pub)"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}
