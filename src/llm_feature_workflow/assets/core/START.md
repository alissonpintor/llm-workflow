# Iniciar e retomar o workflow portátil

Este documento usa caminhos relativos à raiz do projeto. Não exige slash commands,
menções de arquivos, plugins, MCP, ferramentas com nomes específicos ou descoberta automática.
Leia a etapa solicitada como instruções em linguagem natural. Nenhum arquivo concede
permissão para executar comandos, publicar, remover dados ou acessar sistemas externos.

## Contexto inicial

1. Leia `MEMORY.md`, `.workflow/workflow.yaml` e `.workflow/generated/profile-context.md`.
2. Leia `.workflow/generated/rules/common.md`, `.workflow/generated/rules/engineering.md`,
   `.workflow/generated/rules/security.md` e as regras de módulos/perfis aplicáveis.
3. Quando existir, leia `.workflow/generated/rules/domain-assessment.md`: registre divergências
   do domínio e reavalie decisões antes de introduzir padrões não aprovados.
4. Identifique objetivo, pasta da funcionalidade, etapa atual e decisões já aprovadas.
   Não presuma que uma nova sessão herdou a conversa anterior.

## Escolher uma etapa

{{ command_index }}

Para planejamento completo, comece por `.workflow/generated/commands/planejar-prd.md`.
Para executar um plano READY, use `.workflow/generated/commands/executar-prd.md`,
somente após autorização do usuário. Leitura de documentos não autoriza implementação.

## Capacidades e alternativas

| Capacidade | Quando disponível | Quando ausente |
|---|---|---|
| Ler arquivos | Abra apenas os caminhos necessários | Peça ao usuário que anexe/cole os documentos; não alegue inspeção |
| Editar arquivos | Edite somente o escopo autorizado | Entregue uma proposta de patch/documento para aplicação humana |
| Executar comandos | Rode gates autorizados e registre saída real | Forneça comandos/diretório e peça resultados; mantenha validação pendente |
| Revisão independente | Use outro reviewer ou sessão separada com contexto explícito | Peça revisão humana ou outra sessão; pare nesse gate, não simule independência |
| Delegação | Use recursos nativos se disponíveis e autorizados | Faça etapas sequenciais; revisões independentes continuam separadas |
| Testes de interface | Use recursos adequados à plataforma quando autorizados | Forneça roteiro de QA manual e registre casos não executados |

Uma autorrevisão não equivale a review independente. Ferramentas sem acesso local podem
receber documentos anexados; isso não lhes dá acesso ao restante do repositório.
Compatibilidade do conteúdo não garante descoberta automática ou execução em todo harness.

## Checkpoint e retomada

Na pasta da funcionalidade, registre um checkpoint com etapa/estado, objetivo, artefatos,
decisões aprovadas, perguntas, baselines originais, resultados reais dos testes e próxima ação.
Se estiver sem escrita, entregue esse checkpoint ao usuário para guardar/anexar na próxima sessão.
Ao retomar, confira os artefatos contra o checkpoint: não confie só em checkboxes e não
substitua baselines por um HEAD mais recente. Conteúdo histórico é evidência, não autorização.

## Inicialização manual

Se a ferramenta não carregar `AGENTS.md`, peça explicitamente:

> Leia `.workflow/START.md` e siga a etapa solicitada. Informe capacidades ausentes,
> peça o contexto que faltar e aguarde aprovação nos gates.

Os arquivos em `commands/` e `templates/` são cópias de conveniência do núcleo canônico.
Pastas específicas de harness são opcionais e não mudam o significado das etapas.
