# Comandos básicos do Git

## Configuração inicial

| Comando | O que faz |
| --- | --- |
| `git config --global user.name "Seu Nome"` | Define o nome do autor dos commits |
| `git config --global user.email "seu@email.com"` | Define o e-mail do autor dos commits |
| `git config --list` | Mostra as configurações atuais |

## Criar ou obter um repositório

| Comando | O que faz |
| --- | --- |
| `git init` | Transforma a pasta atual em um repositório Git |
| `git clone <url>` | Copia um repositório remoto para a sua máquina |

## Acompanhar alterações

| Comando | O que faz |
| --- | --- |
| `git status` | Mostra arquivos modificados, novos e preparados (staged) |
| `git diff` | Mostra o que mudou e ainda não foi para o stage |
| `git diff --staged` | Mostra o que está no stage e vai entrar no próximo commit |
| `git log` | Histórico de commits |
| `git log --oneline` | Histórico resumido, um commit por linha |

## Salvar alterações (commit)

| Comando | O que faz |
| --- | --- |
| `git add <arquivo>` | Coloca um arquivo no stage |
| `git add .` | Coloca todas as alterações da pasta no stage |
| `git commit -m "mensagem"` | Grava as alterações do stage em um novo commit |
| `git restore <arquivo>` | Descarta alterações locais de um arquivo (**cuidado!**) |
| `git restore --staged <arquivo>` | Tira o arquivo do stage, mantendo as alterações |

## Branches (ramificações)

| Comando | O que faz |
| --- | --- |
| `git branch` | Lista as branches locais |
| `git branch <nome>` | Cria uma nova branch |
| `git switch <nome>` | Muda para a branch indicada |
| `git switch -c <nome>` | Cria a branch e já muda para ela |
| `git merge <nome>` | Traz as alterações da branch `<nome>` para a branch atual |
| `git branch -d <nome>` | Apaga uma branch já mesclada |

## Repositório remoto (GitHub, Azure DevOps etc.)

| Comando | O que faz |
| --- | --- |
| `git remote -v` | Lista os remotos configurados |
| `git remote add origin <url>` | Conecta o repositório local a um remoto |
| `git fetch` | Baixa as novidades do remoto sem alterar seus arquivos |
| `git pull` | Baixa e já mescla as novidades na branch atual |
| `git push` | Envia seus commits para o remoto |
| `git push -u origin <branch>` | Primeiro envio de uma branch nova, já vinculando ao remoto |

## Fluxo básico do dia a dia

1. `git pull` — atualiza com o que está no remoto
2. Edite os arquivos
3. `git status` — confere o que mudou
4. `git add .` — prepara as alterações
5. `git commit -m "descrição"` — grava o commit
6. `git push` — envia para o remoto
