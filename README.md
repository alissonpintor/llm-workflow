# llm-workflow

CLI para instalar e manter um workflow reutilizável de desenvolvimento assistido por LLMs:

```text
descoberta → PRD → review de produto → Tech Spec → review técnico
→ tasks → gate READY → implementação/review por task → aceite final
```

O projeto é **agnóstico de linguagem e framework**. O núcleo não sabe se sua aplicação usa Python, Go, Kotlin, Node ou qualquer outra tecnologia. A stack é adicionada por perfis depois que você a decide.

> Status: **alpha (0.1.0)**. Use uma tag fixa e revise os arquivos gerados antes de adotar em produção.

**Importante:** a CLI instala o workflow documental, não o código da sua aplicação. Ela não cria um projeto FastAPI/Django/Android, não instala banco de dados e não chama uma LLM por conta própria. Os commands Markdown orientam o agente que você já utiliza. Os quality gates são instruções para o agente executar; a CLI não roda comandos arbitrários do projeto automaticamente.

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

## Como funciona a configuração

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
workflow_version: 0.1.0
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

Adaptadores padrão:

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
```

### `profiles`

```powershell
llm-workflow profiles
```

### `sync`

```powershell
llm-workflow sync .
```

Regenera commands, templates, rules e adaptadores.

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

- A CLI não envia conteúdo do projeto para serviços externos.
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
- A versão inicial aceita os perfis retornados por `profiles`; novas tecnologias exigem adicionar manifests ao pacote. O núcleo permanece agnóstico.
- Há perfis para Kotlin/Ktor, SvelteKit, React e Android Views além dos exemplos acima.
- Mudanças incompatíveis de schema entre versões ainda exigem uma migração explícita; schema desconhecido é recusado.
- A CLI não fornece um executor autônomo de agentes, nem garante que todo cliente tenha a mesma sintaxe de comandos. `AGENTS.md` aponta os arquivos canônicos e os espelhos podem ser lidos explicitamente.
- Perfis são uma base inicial e devem ser revisados conforme os padrões da equipe.

## Licença

[MIT](LICENSE).

---

**English summary:** `llm-workflow` is a stack-agnostic CLI that installs a versioned, profile-driven workflow for discovery, PRDs, technical specifications, implementation tasks, independent reviews, and final acceptance. This README is currently maintained in Portuguese.
