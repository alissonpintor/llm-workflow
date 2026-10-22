# Contribuindo

1. Crie um fork e uma branch curta.
2. Instale o ambiente: `uv sync --dev`.
3. Rode `uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest`.
4. Não adicione regras específicas ao núcleo; crie um perfil ou plugin.
5. Não inclua segredos, caminhos pessoais ou dados de projetos reais em fixtures.
6. Abra um pull request explicando comportamento, testes e compatibilidade.

Antes de publicar commits, execute `uv run python scripts/check_public_files.py` após adicionar somente os arquivos revisados ao Git.
