# Segurança

Não publique tokens, credenciais, chaves, arquivos `.env` ou dados de clientes em issues.

Para relatar uma vulnerabilidade, use **Security → Report a vulnerability** no GitHub do projeto. Inclua apenas os passos mínimos para reproduzir e remova qualquer segredo dos logs.

O `llm-workflow` escreve arquivos no diretório informado. Antes de usar uma versão vinda de Git, confira o repositório e fixe uma tag ou commit confiável.

A CLI não executa os comandos dos quality gates automaticamente. Configurações, documentos e perfis são entradas que precisam de revisão humana antes que um agente execute comandos. Não grave credenciais em `workflow.yaml`; esse arquivo é pensado para ser público/versionado.

## OpenRouter (opcional)

- `configure --ai` envia somente contexto explicitamente permitido e exige consentimento interativo ou `--allow-paid`. Os comandos offline não fazem geração; `llm models` consulta o catálogo público.
- Use `OPENROUTER_API_KEY` no ambiente ou o prompt oculto interativo. A chave não é persistida, não entra no prompt e só é enviada em autenticação ao endpoint fixo `https://openrouter.ai/api/v1`.
- Não inclua outros segredos/dados pessoais em brief, respostas, metadados ou flags: eles são enviados ao serviço e persistidos na proposta. A proteção contra repetição da chave não é um detector universal de segredos.
- Código, `.env`, documentos privados e `settings` existentes não são enviados automaticamente. O transporte tem timeout/limite de resposta, não segue redirects e não faz retry/fallback automático.
- A política `data_collection: deny` filtra provedores conforme o OpenRouter, mas não garante retenção zero nem substitui a avaliação de termos, residência de dados ou conformidade. Limite de tokens não é teto de gasto; uma falha ainda pode ser cobrada.
- As saídas são dados não confiáveis, validados por schema e referências locais. Não há ferramentas disponíveis para a LLM; não execute comandos sugeridos sem revisão. Nem o schema nem as regras curadas garantem correção/segurança sem avaliação contextual.
- Revise com `llm preview` e aprove separadamente com `llm apply --approve`. Arquivos gerados entram nos agentes como recomendações aprovadas; conteúdo malicioso ainda pode induzir um agente a agir se não for revisado.
- `.workflow/ai/proposal.json` contém o brief e a conversa de configuração. Não o publique sem revisão; adicione `.workflow/ai/` ao `.gitignore` do projeto quando necessário.
- Perfis locais são fontes editáveis preservadas em `sync`. Eles também podem alterar orientações e gates usados pelos agentes: trate mudanças neles como mudanças de código que exigem review.
- Avaliações de domínio exigem citações literais do contexto, mas isso não comprova a interpretação da LLM. As citações aprovadas ficam em `workflow.yaml` e nas regras geradas; revise-as para evitar exposição de dados de negócio sensíveis.

## Portabilidade e capacidades

O núcleo não exige recursos proprietários nem altera permissões da ferramenta agêntica. `AGENTS.md`/START são pontos de entrada, não uma autorização para executar ações. Sem acesso a arquivos, comandos ou reviewer independente, declare limitações e mantenha os gates pendentes. Adaptadores são opcionais e não garantem que todos os harnesses os descubram automaticamente.

Ao migrar com `configure --portable`, apenas arquivos gerenciados inalterados dos adaptadores desativados são removidos. Um conflito local bloqueia o plano inteiro antes da escrita; documentos próprios e perfis locais permanecem preservados.

Antes de publicar, rode `python scripts/check_public_files.py`. Ele verifica arquivos rastreados sem imprimir os valores suspeitos. É uma proteção focal, não substitui ferramentas especializadas nem garante ausência de todo tipo de dado sensível.

Durante o desenvolvimento, use `python scripts/check_public_files.py --include-untracked` para incluir os novos arquivos ainda não adicionados ao Git.
