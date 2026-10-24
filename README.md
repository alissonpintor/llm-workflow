# llm-workflow

CLI para instalar e manter um workflow reutilizável de desenvolvimento assistido por LLMs:

```text
descoberta → PRD → review de produto → Tech Spec → review técnico
→ tasks → gate READY → implementação/review por task → aceite final
```

O projeto é **agnóstico de linguagem, framework e harness**. A stack é adicionada por perfis depois que você a decide. O núcleo é Markdown portátil; integrações específicas de ferramentas são opcionais.

> Status: **alpha**. Versão publicada: `v0.1.0`. A integração OpenRouter faz parte da **0.2.0 em desenvolvimento**, ainda não publicada. Os exemplos com `@v0.1.0` usam a versão anterior, sem geração via API.

**Importante:** a CLI instala o workflow documental, não o código da sua aplicação. Ela não cria um projeto FastAPI/Django/Android nem instala banco de dados. No modo opcional `configure --ai`, chama o OpenRouter somente com autorização de envio/custo e salva uma proposta para revisão. Os commands Markdown orientam o agente que você já utiliza. A CLI não executa quality gates nem comandos sugeridos pela LLM.

## O que ele resolve

Ao começar um projeto novo, é comum copiar prompts, rules e templates de outro repositório. Isso traz dois problemas:

1. referências à tecnologia e ao domínio do projeto antigo;
2. cópias que deixam de receber melhorias futuras.

O `llm-workflow` mantém um núcleo versionado e permite combinar:

- módulos da aplicação;
- perfis de linguagem/framework;
- serviços de infraestrutura;
- plugins opcionais de qualidade;
- adaptadores para diferentes ferramentas de agentes.

## Requisitos

- Git;
- [uv](https://docs.astral.sh/uv/) instalado;
- Python 3.11 ou superior (o `uv` pode instalar automaticamente);
- uma ferramenta de agentes capaz de ler Markdown.

No Windows, instale o `uv` com o comando oficial:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Confirme:

```powershell
uv --version
```

## Início rápido

Os comandos desta seção usam a tag anterior `v0.1.0`. Para OpenRouter, avaliação de DDD e modo portátil por padrão, use o checkout da `0.2.0` conforme as seções abaixo; não existe ainda uma tag `v0.2.0` publicada.

### 1. Crie o projeto

```powershell
mkdir meu-projeto
cd meu-projeto
git init
```

### 2. Instale o núcleo diretamente do GitHub

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.1.0" `
  llm-workflow init .
```

O `uvx` baixa o pacote em um ambiente isolado, executa a CLI e mantém um cache local. Ele não adiciona dependências Python à sua aplicação.

### 3. Veja os perfis disponíveis

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.1.0" `
  llm-workflow profiles
```

### 4. Configure a stack

Exemplo: API Python/FastAPI com PostgreSQL e Redis:

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.1.0" `
  llm-workflow configure . `
  --module api:backend=python+fastapi `
  --service database=postgres `
  --service cache=redis `
  --uses api=database,cache `
  --set "api.test_command=uv run pytest" `
  --non-interactive
```

### 5. Verifique a instalação

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.1.0" `
  llm-workflow doctor .
```

### 6. Use os commands com sua LLM

```text
@commands/planejar-prd.md
@commands/executar-prd.md
```

Se ainda não decidiu a tecnologia, use primeiro `@commands/definir-stack.md`. O PRD pode ser discutido sem stack; a Tech Spec precisa da decisão tecnológica aprovada. A grafia `@arquivo` depende da ferramenta de agentes: você também pode pedir explicitamente que ela leia `commands/planejar-prd.md`.

Para usar comandos `llm-workflow` sem repetir `uvx --from ...`, faça a instalação permanente descrita abaixo. O primeiro `uvx` não instala o executável globalmente.

## Instalar a versão em desenvolvimento (0.2.0)

Para experimentar antes da publicação, instale a partir deste checkout:

```powershell
# Execute na pasta do repositório llm-workflow:
uv tool install --force .
# Depois, entre na pasta do seu projeto.
```

## Workflow independente de harness

Na `0.2.0`, `llm-workflow init .` gera por padrão somente o núcleo portátil, `AGENTS.md` e cópias de conveniência em `commands/` e `templates/`. Não cria `.grok/`, `.zcode/`, `.agents/` ou `.opencode/` sem seleção explícita.

```powershell
llm-workflow init .
# Na ferramenta agêntica, peça:
# Leia .workflow/START.md e siga a etapa de planejamento da funcionalidade.
```

`AGENTS.md` aponta para `.workflow/START.md`, com índice de etapas, contexto inicial, capacidades alternativas e checkpoint de retomada. Todas as etapas incluem entrada, saída e critério de conclusão. O núcleo usa Markdown sem frontmatter de harness, sem exigir slash commands, sintaxe `@arquivo` ou ferramentas com nomes proprietários.

Se a ferramenta não carregar `AGENTS.md`, peça explicitamente que leia o START. Sem acesso a arquivos, anexe os documentos necessários. Sem escrita/execução, o agente entrega propostas e comandos para aplicação/verificação humana, mantendo gates pendentes. Sem delegação, as etapas podem ser sequenciais; reviews exigem outra sessão ou reviewer humano. **Autorrevisão não conta como revisão independente.**

Portabilidade de conteúdo não garante descoberta automática nem execução idêntica em todos os produtos. Os testes verificam o núcleo e os adaptadores gerados; não equivalem a uma homologação ponta a ponta de todos os harnesses.

### Adaptadores opcionais e migração

```powershell
# Projeto novo com atalhos específicos:
llm-workflow init . --agents grok zcode
# Projeto existente: selecionar os adaptadores desejados:
llm-workflow configure . --agents agents opencode --non-interactive
# Projeto existente: voltar ao núcleo portátil:
llm-workflow configure . --portable --non-interactive
```

`init --portable` também explicita o padrão. `--agents` e `--portable` são mutuamente exclusivos. Configurações antigas mantêm seus adaptadores em `sync`/`upgrade`; a migração é voluntária. A remoção afeta somente arquivos gerenciados inalterados. Arquivos próprios são preservados; um arquivo gerenciado modificado bloqueia o plano inteiro antes de qualquer escrita. Pastas vazias podem permanecer.

Os adaptadores adicionam metadados de descoberta ao mesmo corpo canônico, sem mudar regras/etapas. O adaptador OpenCode usa `description` nos commands conforme a [documentação V2](https://opencode.ai/v2/docs/commands); os demais mantêm seus formatos existentes como compatibilidade opcional. Não há instalação de plugins nem alteração de permissões do harness.

## Gerar regras com OpenRouter

O fluxo separa **escolha do modelo → proposta → revisão → aplicação offline**:

```powershell
llm-workflow init . # apenas se ainda não inicializou
llm-workflow llm models --filter anthropic
llm-workflow llm setup . --model fornecedor/modelo --max-tokens 8000
```

Substitua `fornecedor/modelo` por um ID real retornado pelo catálogo. A lista é pública e filtra modelos que anunciam `structured_outputs`; isso não garante acesso, saldo ou compatibilidade de todos os endpoints na sua conta. `setup` só salva provedor, modelo e limite de saída, sem chamada de geração.

Defina `OPENROUTER_API_KEY` **no ambiente da sessão**, preferencialmente por um gerenciador de segredos. Em terminal interativo, se a variável estiver ausente, a CLI também pode pedir a chave com entrada oculta, sem gravá-la. Não passe a chave como argumento, nem a coloque em YAML, `.env` do projeto ou no brief.

```powershell
llm-workflow configure . --ai `
  --brief "Sistema de pedidos: API Python/FastAPI e frontend SvelteKit. Monólito modular por feature, PostgreSQL, autorização por proprietário e testes negativos." `
  --module api:backend=fastapi `
  --module web:frontend=sveltekit
```

A CLI pede consentimento para enviar o contexto e autorizar possível cobrança. Para automação, use `--allow-paid --non-interactive`. `--model fornecedor/modelo` pode substituir o modelo salvo naquela geração. Cada execução faz **no máximo uma chamada de geração**, sem retry ou fallback automático; não há chamadas pagas durante os testes do pacote.

A proposta inclui regras concretas com instrução, justificativa, exemplo, exceções e verificação, além de pastas e gates por módulo. Há regras de design, segurança e testes obrigatórias no schema. A base curada de engenharia (SOLID/Clean Code/DDD contextual) e segurança permanece presente mesmo sem IA. Uma saída válida no schema **não comprova qualidade técnica ou segurança**.

```powershell
llm-workflow llm preview .
# Revise configuração, regras, perfis locais, arquivos afetados e comandos propostos.
llm-workflow llm apply . --approve
llm-workflow doctor .
```

Gerar salva apenas `.workflow/ai/proposal.json`; não altera o workflow ativo. `preview` e `apply` não acessam a API. A aplicação exige `--approve`, rejeita perguntas pendentes e propostas cuja configuração/perfis tenham mudado, e preserva o mecanismo de detecção de conflitos locais. Pastas da aplicação são apenas recomendações documentadas, não são criadas.

Os gates aprovados ficam em `modules.<nome>.proposed_gates` no `workflow.yaml` e substituem os defaults dos perfis nesse módulo. Para ajustá-los depois da aprovação, edite essa lista e execute `sync`; `--set api.test_command=...` altera apenas o default, não os gates explícitos da proposta.

Se houver perguntas bloqueantes, responda **todas** as perguntas pendentes e gere novamente (uma nova chamada potencialmente cobrada):

```powershell
llm-workflow configure . --ai `
  --answer "Q-01=Somente o proprietário e administradores autorizados acessam o pedido."
```

O brief, as solicitações e as perguntas/respostas anteriores são preservados na retomada. Para começar outra proposta, forneça um novo `--brief` sem `--answer`; uma proposta válida anterior será substituída. Se `proposal.json` for inválido/desconhecido, preserve-o em outro local antes de tentar novamente.

### Como a LLM avalia DDD

A proposta exige `domain_assessments` por módulo e permite escopos distintos dentro dele. O contexto precisa descrever o negócio, não só a stack: processos, regras que impedem operações, estados/transições, consistência e diferenças de vocabulário entre áreas.

Cada avaliação contém:

- `simple_design`, `strategic_ddd`, `selective_ddd` ou `insufficient_context`;
- citações literais de fontes identificadas (`BRIEF`, `REQUEST-XX`, respostas `Q-XX`), separadas da interpretação proposta;
- problema concreto, justificativa, evidências e custos de cada padrão recomendado;
- uma alternativa mais simples e seus trade-offs;
- perguntas bloqueantes quando não houver informação suficiente.

A CLI rejeita fontes/citações inexistentes, padrões sem referência a evidências, avaliações sem cobertura dos módulos e decisões incompatíveis com seu nível (por exemplo, agregados sob `strategic_ddd`). Contexto insuficiente precisa apontar para perguntas reais da proposta e impede aplicação. A retomada envia as respostas como novas fontes. Não há pontuação automática baseada em tamanho, tabelas ou framework. DDD não implica microserviços, CQRS ou event sourcing.

`llm preview` mostra a avaliação ainda como PROPOSTA. Após `llm apply --approve`, ela fica no `workflow.yaml` e em `.workflow/generated/rules/domain-assessment.md`, como decisão aprovada pelo usuário. As regras devem respeitar os escopos escolhidos. **A validação comprova estrutura e rastreabilidade, não a verdade da interpretação nem a coerência semântica de todas as regras:** revisão humana continua obrigatória.

O fluxo documental também funciona sem API: a etapa `avaliar-dominio.md` e o template `domain-assessment-template.md` orientam a conversa com qualquer agente. Cada funcionalidade registra `domain-assessment.md`; pode reutilizar a decisão de projeto, mas precisa confirmar sua adequação e aprovação. `validate` exige esse documento aprovado, recomendação definida e zero perguntas bloqueantes antes de liberar o planejamento. Planos antigos precisam incorporar essa avaliação antes de validar na `0.2.0`.

### Dados enviados e cobrança

- Enviados: brief, respostas, solicitações explícitas (`--module`, `--service`, `--uses`, `--set`), perguntas anteriores, as mesmas entradas com IDs para citação e metadados permitidos (arquitetura, nomes/tipos/caminhos/perfis/relações de módulos/serviços e catálogo resumido), além da base de engenharia do pacote.
- Não enviados automaticamente: código-fonte, regras locais completas, configurações `settings` existentes, `.env`, documentos privados ou caminhos absolutos da máquina. Não há varredura do projeto.
- A chave vai somente no header de autenticação para o endpoint fixo do OpenRouter. O contexto que contiver a própria chave é recusado; a resposta que a repetir é descartada. Isso não detecta todos os outros segredos que você possa incluir manualmente.
- O transporte não segue redirects, não aceita endpoint customizado e solicita `require_parameters: true`, `allow_fallbacks: false` e `data_collection: deny`. Essa política de roteamento **não é garantia de retenção zero**: confira os termos do OpenRouter e do provedor escolhido.
- `--max-tokens` limita a saída, não define um teto monetário. Preço, tokens de entrada/raciocínio, disponibilidade e cobrança dependem do serviço. Timeout, recusa ou resposta inválida podem ocorrer depois de cobrança; não há retry automático.
- O arquivo de proposta guarda brief, solicitações, perguntas/respostas e regras. Revise antes de versionar; exclua `.workflow/ai/` pelo `.gitignore` do seu projeto se esse contexto for privado. Contadores de uso/custo retornados pelo serviço são informativos, não uma auditoria de faturamento.
- Citações da avaliação aprovada também são persistidas em `workflow.yaml` e nas regras geradas. Revise esses trechos antes de aprovar/versionar; não forneça segredos ou dados pessoais como evidência.

### Tecnologias fora do catálogo

A LLM pode propor novos perfis em `.workflow/profiles/<id>/profile.yaml`, aprovados junto com o restante da proposta. Eles não substituem perfis internos ou locais existentes. `sync` usa esses manifests como fontes locais editáveis e não os apaga quando deixam de ser selecionados.

Também é possível criar um perfil manual, sem API:

```yaml
# .workflow/profiles/minha-stack/profile.yaml
id: minha-stack
name: Minha Stack
category: framework
requires: [python]
kinds: [backend, worker]
rule: |
  Isole integrações externas atrás de contratos pequenos e teste falhas de I/O.
edge_cases:
  - Timeout antes de concluir uma escrita externa.
```

```powershell
llm-workflow profiles .
llm-workflow configure . --module api:backend=minha-stack --non-interactive
```

Revise regras e comandos antes de permitir que um agente os utilize. A geração não pesquisa documentação oficial nem executa review independente.

## Configuração declarativa (sem API)

A configuração usa três conceitos.

### Módulo

Parte executável ou publicável do sistema:

```text
--module nome:tipo=perfil+perfil
```

Exemplos:

```text
--module api:backend=python+fastapi
--module admin:backend=python+django
--module gateway:backend=go+chi
--module worker:worker=node+typescript
--module mobile:mobile=kotlin+android+compose
```

Tipos comuns:

- `backend`
- `frontend`
- `worker`
- `mobile`
- `library`
- `cli`

### Serviço

Infraestrutura compartilhada por um ou mais módulos:

```text
--service nome=perfil
```

Exemplos:

```text
--service database=postgres
--service cache=redis
```

### Uso de serviço

Relaciona um módulo aos serviços que ele consome:

```text
--uses modulo=servico,servico
```

Exemplo:

```text
--uses api=database,cache
```

## Exemplos de stacks

### Django + PostgreSQL

```powershell
llm-workflow configure . `
  --module web:backend=python+django `
  --service database=postgres `
  --uses web=database `
  --non-interactive
```

### Go com `net/http`

```powershell
llm-workflow configure . `
  --module api:backend=go+net-http `
  --service database=postgres `
  --uses api=database `
  --non-interactive
```

### Node + TypeScript + Fastify

```powershell
llm-workflow configure . `
  --module api:backend=node+typescript+fastify `
  --set api.package_manager=pnpm `
  --set "api.lint_command=pnpm lint" `
  --set "api.typecheck_command=pnpm typecheck" `
  --set "api.test_command=pnpm test" `
  --non-interactive
```

### Android com Kotlin e Compose

```powershell
llm-workflow configure . `
  --module mobile:mobile=kotlin+android+compose `
  --set "mobile.test_command=gradlew.bat test" `
  --non-interactive
```

### Projeto poliglota

```powershell
llm-workflow configure . `
  --module api:backend=fastapi `
  --module admin:backend=django `
  --module gateway:backend=go+chi `
  --module worker:worker=node+typescript `
  --module mobile:mobile=compose `
  --service database=postgres `
  --service cache=redis `
  --uses api=database,cache `
  --uses admin=database,cache `
  --uses gateway=cache `
  --uses worker=database,cache `
  --non-interactive
```

Dependências de perfil são resolvidas automaticamente:

- `fastapi` adiciona `python`;
- `django` adiciona `python`;
- `compose` adiciona `android` e `kotlin`;
- `nestjs` adiciona `typescript` e `node`.

Combinações incompatíveis no mesmo módulo são rejeitadas. Por exemplo, FastAPI e Django devem ficar em módulos separados.

## Configuração interativa

Execute sem argumentos tecnológicos:

```powershell
llm-workflow configure .
```

A CLI pergunta os módulos, perfis, serviços e relações. Antes de usar esse modo em automação, prefira os argumentos declarativos com `--non-interactive`.

O modo interativo pede confirmação antes de gravar. Argumentos declarativos já representam sua autorização de aplicar a configuração.

## Personalizando comandos de qualidade

Cada módulo pode sobrescrever os defaults dos perfis:

```powershell
llm-workflow configure . `
  --set "api.test_command=uv run pytest" `
  --set "api.lint_command=uv run ruff check ." `
  --set "api.typecheck_command=uv run pyright" `
  --non-interactive
```

A fonte de verdade fica em:

```text
.workflow/workflow.yaml
```

O contexto resolvido fica em:

```text
.workflow/generated/profile-context.md
```

As LLMs consultam esse arquivo em vez de adivinhar comandos.

Os gates iniciais são **defaults propostos**, não uma descoberta de ferramentas que já existem na sua máquina. Revise-os conforme seus arquivos reais, instale as dependências no projeto e sobrescreva os comandos necessários. Por exemplo, escolher Python não instala Ruff ou mypy no seu backend. Nunca informe senha/token em `--set`: a configuração é feita para ser versionada.

Para mudar a pasta de um módulo:

```powershell
llm-workflow configure . --set api.path=backend --non-interactive
```

Para aplicar um arquivo declarativo completo:

```powershell
llm-workflow configure . --config projeto-workflow.yaml --non-interactive
```

Formato de exemplo:

```yaml
schema_version: 1
workflow_version: 0.2.0
project:
  name: meu-projeto
  status: configured
  architecture: modular-monorepo
agents:
  targets: [agents, grok, zcode]
modules:
  api:
    kind: backend
    path: backend
    requested_profiles: [fastapi]
    settings:
      test_command: uv run pytest
      lint_command: uv run ruff check .
      typecheck_command: uv run pyright
    uses: [database]
services:
  database:
    requested_profiles: [postgres]
    settings: {}
plugins: []
```

`resolved_profiles` é calculado automaticamente; não precisa ser escrito manualmente. Para trocar/remover módulos, serviços ou plugins, edite `workflow.yaml` e rode `sync`. As flags de `configure` adicionam ou atualizam os itens nomeados, não apagam outros módulos.

## Plugin de campos fantasma Kotlin/SQL

Ative somente em projetos Kotlin que leem resultados SQL por mapas/rows:

```powershell
llm-workflow configure . `
  --module backend:backend=kotlin `
  --plugin kotlin-sql-ghost-fields `
  --non-interactive
```

Isso instala:

```text
scripts/find_ghost_fields.py
```

O plugin é executado de forma condicional no review da task e no aceite final. Ele produz candidatos heurísticos: somente campo confirmado ou não rastreado bloqueia; falsos positivos precisam de evidência.

## Arquivos gerados

```text
.workflow/
├── workflow.yaml
├── workflow.lock
├── START.md                  # entrada portátil, índice e alternativas de capacidade
├── ai/proposal.json          # opcional: contexto e proposta não aplicada
├── profiles/<id>/profile.yaml # opcional: fontes locais editáveis
└── generated/
    ├── commands/
    ├── rules/
    ├── templates/
    └── profile-context.md

commands/
templates/
docs/
MEMORY.md
AGENTS.md
```

Adaptadores opcionais na `0.2.0` (a tag `v0.1.0` ainda os criava por padrão):

```text
.agents/rules/commands/
.agents/rules/
.grok/rules/commands/
.grok/rules/
.zcode/commands/
.zcode/rules/
```

Os arquivos gerados possuem o marcador:

```html
<!-- llm-workflow:managed -->
```

Não edite esses arquivos diretamente. Altere `.workflow/workflow.yaml` e execute `sync`.

Caso tenha editado um arquivo gerado, a CLI verifica seu hash e **interrompe antes de escrever**. Salve sua customização em um arquivo próprio, restaure a versão gerenciada e só então execute `sync`/`upgrade`. Regras adicionais da equipe podem ficar fora do bloco gerenciado de `AGENTS.md` ou em documentos próprios. Um marcador sozinho não autoriza sobrescrever arquivo desconhecido.

Desativar um perfil/plugin remove apenas os arquivos gerenciados por ele e inalterados desde a geração. Um arquivo local modificado nunca é apagado silenciosamente. Caminhos absolutos, `..` e escapes por symlink/junction são recusados.

Arquivos de documentação como `docs/decisions.md` são criados apenas quando ausentes e não são sobrescritos durante upgrades.

## Commands do workflow

| Command | Finalidade |
|---|---|
| `definir-stack.md` | Decidir a stack e registrar o ADR inicial |
| `avaliar-dominio.md` | Avaliar design simples/DDD com evidências e aprovação humana |
| `criar-prd.md` | Descoberta e PRD |
| `revisar-prd.md` | Review independente de produto |
| `criar-techspec.md` | Design técnico baseado no código e perfis |
| `revisar-techspec.md` | Review técnico independente |
| `criar-uiux.md` | Spec de interface quando aplicável |
| `criar-tasks.md` | Decomposição em entregáveis |
| `validar-planejamento.md` | Gate documental até `READY` |
| `planejar-prd.md` | Orquestra todo o planejamento |
| `executar-task.md` | Implementa uma task sem commit |
| `executar-review.md` | Revisa pelo `TASK_BASE_SHA` |
| `validar-entrega-prd.md` | Aceite integrado |
| `executar-prd.md` | Orquestra implementação e release |
| `executar-bugfix.md` | Diagnóstico, teste de regressão e correção |
| `executar-qa.md` | Verificação de jornadas e critérios de aceite |
| `analisar-seguranca.md` | Auditoria de segurança somente-leitura |
| `codigo-morto.md` | Auditoria contextual de código sem uso |

## Comandos da CLI

### `init`

```powershell
llm-workflow init .
```

Opções:

```text
--agents agents grok zcode opencode
--portable
--force
```

### `configure`

```powershell
llm-workflow configure . [opções]
```

Opções repetíveis:

```text
--module nome:tipo=perfil+perfil
--service nome=perfil
--uses modulo=servico,servico
--set escopo.chave=valor
--plugin plugin-id
--config arquivo.yaml
--non-interactive
--ai --model fornecedor/modelo --brief "descrição"
--answer Q-01=texto
--allow-paid
--max-tokens 8000
--agents agents grok zcode opencode
--portable
```

### `profiles`

```powershell
llm-workflow profiles [caminho]
```

### `sync`

```powershell
llm-workflow sync .
```

Regenera commands, templates, rules e adaptadores.

### `llm`

```powershell
llm-workflow llm models --filter texto
llm-workflow llm setup . --model fornecedor/modelo
llm-workflow llm preview .
llm-workflow llm apply . --approve
```

A geração é iniciada por `configure --ai`; os demais comandos estão descritos na seção OpenRouter.

### `doctor`

```powershell
llm-workflow doctor .
```

Verifica configuração, arquivos gerados e ferramentas básicas.

### `validate`

```powershell
llm-workflow validate . tasks/prd-minha-feature
```

Verifica documentos, reviews, IDs, cobertura e arquivos de task.

Na `0.2.0`, exige também avaliação de domínio aprovada em `domain-assessment.md`. O lint verifica declarações e estrutura, não autentica por si só quem aprovou nem substitui a revisão semântica das evidências.

Também verifica ciclos de dependência, referência a decisões/testes, RF sem aceite, perguntas bloqueantes e UI/UX obrigatória. O lint não prova que as regras de negócio estão corretas: o review semântico independente continua obrigatório.

### `diff`

```powershell
llm-workflow diff .
```

Lista os arquivos novos ou divergentes em relação à versão da CLI em uso, sem modificar o projeto. Use antes de um upgrade.

### `upgrade`

Execute a versão nova da própria CLI. **O exemplo abaixo só funciona quando `v0.2.0` estiver publicada**; substitua pela tag desejada que realmente existe:

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.2.0" `
  llm-workflow upgrade .
```

O comando lê a configuração existente, regenera arquivos gerenciados e preserva documentação do projeto.

## `uvx` versus instalação permanente

### Uso isolado e reproduzível

```powershell
uvx --from "git+https://github.com/alissonpintor/llm-workflow@v0.1.0" `
  llm-workflow doctor .
```

### Instalação permanente

```powershell
uv tool install "git+https://github.com/alissonpintor/llm-workflow@v0.1.0"
```

Depois:

```powershell
llm-workflow init .
llm-workflow configure .
```

Para atualizar a ferramenta instalada:

```powershell
uv tool install --force "git+https://github.com/alissonpintor/llm-workflow@v0.2.0"
```

## Desenvolvimento local

```powershell
git clone https://github.com/alissonpintor/llm-workflow.git
cd llm-workflow
uv sync --dev
uv run ruff check .
uv run pytest
uv build
```

Teste em outro projeto sem publicar:

```powershell
uvx --from "..\llm-workflow" llm-workflow init .
```

## Segurança e privacidade

- Sem `configure --ai`, a CLI não envia contexto do projeto; `llm models` consulta somente o catálogo público. A geração opcional usa o OpenRouter com consentimento explícito.
- Não lê nem copia `.env`, chaves ou credenciais.
- Templates públicos não devem conter dados de projetos reais.
- Arquivos existentes sem marcador gerenciado não são sobrescritos silenciosamente.
- Uma URL `git+https` executa código do repositório informado: use repositório confiável e fixe tag ou commit.
- Nunca coloque token GitHub em comandos, URLs ou arquivos versionados. Use Git Credential Manager ou SSH.

Veja [SECURITY.md](SECURITY.md).

## Limitações atuais

- O projeto está em alpha.
- O modo interativo é propositalmente simples.
- `doctor` valida estrutura e ferramentas básicas; não executa todos os gates da aplicação.
- Perfis locais permitem novas tecnologias sem modificar o pacote. A geração assistida pode propô-los, mas exige revisão humana.
- Há perfis para Kotlin/Ktor, SvelteKit, React e Android Views além dos exemplos acima.
- Mudanças incompatíveis de schema entre versões ainda exigem uma migração explícita; schema desconhecido é recusado.
- A CLI não fornece um executor autônomo de agentes, nem garante que todo cliente tenha a mesma sintaxe de comandos. `AGENTS.md` aponta os arquivos canônicos e os espelhos podem ser lidos explicitamente.
- Perfis são uma base inicial e devem ser revisados conforme os padrões da equipe.

## Licença

[MIT](LICENSE).

---

**English summary:** `llm-workflow` is a stack-agnostic CLI that installs a versioned, profile-driven workflow for discovery, PRDs, technical specifications, implementation tasks, independent reviews, and final acceptance. This README is currently maintained in Portuguese.
