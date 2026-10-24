# Changelog

## 0.2.0 — em desenvolvimento

- Diagnóstico real com DeepSeek V4 Flash/V3.2 e contexto sintético: separação entre entrevista e proposta, categorias obrigatórias no contrato e citações limitadas a trechos fornecidos.
- Diagnósticos de geração distinguem truncamento, recusa, JSON inválido e violações sanitizadas do schema, sem exibir conteúdo privado ou repetir chamadas.
- Setup informa presença da chave no processo sem autenticação remota; placeholders de brief são recusados antes do envio.
- OpenRouter opcional em `configure --ai`, com escolha de modelo, JSON Schema e chave somente no ambiente/entrada oculta.
- Catálogo público, setup offline, proposta separada, preview e aplicação com `--approve`.
- Consentimento de envio/custo, contexto por allowlist, respostas limitadas e ausência de retries/fallbacks automáticos.
- Perguntas bloqueantes retomáveis e validação de configuração/perfis desatualizados.
- Regras detalhadas por módulo, pastas documentadas e gates propostos sem execução.
- Perfis locais editáveis para tecnologias fora do catálogo, sem sobrescrever perfis existentes.
- Base de engenharia contextual e segurança independente de stack.
- Testes de transporte e fluxo completo com OpenRouter simulado, sem geração paga.
- Avaliação de DDD por módulo/área com citações verificáveis, custos, alternativa simples e perguntas bloqueantes.
- Etapa/template de avaliação de domínio e gate documental de aprovação antes de READY.
- Núcleo portátil por padrão, START com índice/capacidades/retomada e etapas com contratos explícitos.
- Adaptadores opcionais: metadados separados do corpo canônico, seleção com `--agents` e migração segura com `configure --portable`.
- Mudança de comportamento: instalações novas não geram pastas de harness por padrão; configurações existentes preservam seus targets.

## 0.1.0 — 2026-10-22

- Núcleo agnóstico para descoberta, PRD, Tech Spec, tasks, reviews e execução.
- Configuração por módulos, serviços, perfis e plugins.
- Adaptadores para Agents, Grok, ZCode e OpenCode.
- Perfis iniciais para Python/FastAPI/Django, Go, Node/TypeScript, Kotlin/Android, PostgreSQL e Redis.
- Plugin opcional de campos fantasma Kotlin/SQL.
