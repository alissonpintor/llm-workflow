# Segurança

Não publique tokens, credenciais, chaves, arquivos `.env` ou dados de clientes em issues.

Para relatar uma vulnerabilidade, use **Security → Report a vulnerability** no GitHub do projeto. Inclua apenas os passos mínimos para reproduzir e remova qualquer segredo dos logs.

O `llm-workflow` escreve arquivos no diretório informado. Antes de usar uma versão vinda de Git, confira o repositório e fixe uma tag ou commit confiável.

A CLI não executa os comandos dos quality gates automaticamente. Configurações, documentos e perfis são entradas que precisam de revisão humana antes que um agente execute comandos. Não grave credenciais em `workflow.yaml`; esse arquivo é pensado para ser público/versionado.

Antes de publicar, rode `python scripts/check_public_files.py`. Ele verifica arquivos rastreados sem imprimir os valores suspeitos. É uma proteção focal, não substitui ferramentas especializadas nem garante ausência de todo tipo de dado sensível.
