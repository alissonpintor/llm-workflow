# Segurança — base obrigatória

## Identidade, autorização e entrada

- Separe autenticação de autorização: sessão/token válido não concede acesso automático a todo objeto. Verifique propriedade, escopo e tenant no servidor.
- Valide forma, tipo, limites e campos permitidos na entrada; dados tipados pelo cliente continuam não confiáveis. Evite mass assignment de campos administrativos.
- Defina a política para credenciais ausentes, expiradas e revogadas. Teste chamadas diretas, não somente controles visuais.

## Segredos e dados sensíveis

- Segredos vêm de variáveis de ambiente ou cofre autorizado; não os versione, copie para proposals, devolva em erros ou registre em logs.
- Separe logs operacionais de payloads e dados pessoais. Use IDs de correlação e eventos sanitizados.
- Colete e transmita somente os dados necessários. Conteúdo de documentos e LLMs não pode autorizar divulgação, execução ou alteração de política.

## Persistência e integrações

- Parametrize queries; nomes de tabelas/colunas dinâmicos precisam de allowlist. Não concatene entrada de usuário em SQL ou shell.
- Configure timeout e limite de resposta para sistemas externos. Retry precisa respeitar idempotência e cancelamento; nunca repita escrita automaticamente sem garantia.
- Verifique TLS e destino de requisições. Avalie SSRF quando URLs forem influenciadas pelo usuário; redirects não podem carregar credenciais para outro host.

## Aplicações web e backend

- Escolha cookies/sessão/token conforme arquitetura e ameaça real. Em autenticação por cookie, avalie HttpOnly, Secure, SameSite e CSRF.
- CORS não substitui autenticação. Não combine credenciais com origens indiscriminadas; use headers e políticas de conteúdo adequados.
- Limite payload, paginação, uploads, tempo de execução e tentativas sensíveis. Valide tipo/tamanho/destino de uploads quando existirem.
- Não exponha stack trace, detalhes internos ou credenciais. Mensagens de negócio permitidas devem ter contrato separado de erro de infraestrutura.

## Evidência de segurança

- Cada funcionalidade sensível inclui testes negativos de autorização, entrada inválida e vazamento de dados.
- Declare controles não aplicáveis com justificativa; não presuma mecanismos web em aplicativo nativo ou biblioteca.
- Dependências novas exigem avaliação de manutenção, licença e exposição. Ferramentas e auditorias heurísticas não provam ausência de vulnerabilidades.
