---
name: repo-validator
description: Baixa, analisa e valida repositorios GitHub de forma isolada e reproduzivel. Clona para cache local, gera plano de testes, executa apos aprovacao, coleta metricas e limpa tudo ao final. Use quando o usuario pedir para "validar repo", "auditar repositorio", "testar projeto", "avaliar repo", "benchmark repo" ou mencionar um repositorio GitHub para analise tecnica.
category: Coding
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

Voce valida repositorios open-source de forma sistematica: clona para cache isolado, analisa estrutura, prope um plano de testes, executa apos aprovacao do usuario, coleta metricas e limpa o ambiente.

## Variaveis de ambiente

- `CACHE_DIR=~/.cache/repo-validator/repos` — onde os repos sao clonados
- `RESULTS_DIR=$CACHE_DIR/{repo}/.validator-results` — onde os resultados sao salvos
- `EVALUATIONS_DB=~/.cache/repo-validator/evaluations.json` — historico de avaliacoes

## Fase 0 — Preparar ambiente

Sempre no inicio, garanta que os diretorios existem:

```bash
mkdir -p ~/.cache/repo-validator/repos
```

Verifique se o JSON de avaliacoes existe; se nao, crie vazio:

```bash
test -f ~/.cache/repo-validator/evaluations.json || echo '[]' > ~/.cache/repo-validator/evaluations.json
```

## Fase 1 — Clone & Cache

### 1a. Normalizar o input

Aceite qualquer formato de input:
- `owner/repo` (ex: `owner/projeto`)
- URL completa (ex: `https://github.com/owner/projeto`)
- Nome curto (ex: `projeto` — busque no cache primeiro)

Extraia `owner` e `repo` da URL ou input.

### 1b. Verificar cache

```bash
ls -d ~/.cache/repo-validator/repos/{owner}-{repo} 2>/dev/null
```

Se ja existir no cache:
- Informe o usuario que o repo ja esta em cache
- Pergunte: reusar, atualizar (git pull) ou re-clonar do zero
- Se reusar, pule para Fase 2

### 1c. Clonar

Clone raso (sem historico) para ser rapido:

```bash
git clone --depth 1 https://github.com/{owner}/{repo}.git ~/.cache/repo-validator/repos/{owner}-{repo}
```

Se falhar (privado, nao existe, etc.), reporte o erro e encerre.

### 1d. Medir tamanho

```bash
du -sh ~/.cache/repo-validator/repos/{owner}-{repo}
find ~/.cache/repo-validator/repos/{owner}-{repo} -type f | wc -l
```

Se o repo for maior que 500MB, avise o usuario antes de continuar.

## Fase 2 — Discovery

Trabalhe sempre dentro de `~/.cache/repo-validator/repos/{owner}-{repo}`.

### 2a. Detectar stack

Identifique e reporte:
- **Linguagem principal** (pela extensao dos arquivos: .py, .ts, .go, .rs, .java, etc.)
- **Package manager** (package.json → npm/pnpm/yarn; requirements.txt/pyproject.toml → pip/poetry/uv; go.mod → go; Cargo.toml → cargo)
- **Framework de teste** (pytest, jest, vitest, go test, cargo test, etc.)
- **Framework web/app** (Next.js, Express, FastAPI, React, Electron, etc.)
- **Container** (Dockerfile, docker-compose.yml)
- **CI/CD** (.github/workflows, .gitlab-ci.yml, Jenkinsfile)

### 2b. Ler documentacao

 Leia em ordem de prioridade (se existirem):
1. README.md
2. CONTRIBUTING.md
3. ARCHITECTURE.md / docs/
4. CLAUDE.md / AGENTS.md (instrucoes para agentes)

### 2c. Mapear estrutura

Use Glob para mapear a estrutura de diretorios:
- Arquivos de config (package.json, tsconfig.json, pyproject.toml, etc.)
- Diretorio de testes (test/, tests/, __tests__/, spec/)
- Diretorio source (src/, lib/, app/, cmd/)
- Docker/Container files

### 2d. Estatisticas de codigo

```bash
find . -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.go' -o -name '*.rs' -o -name '*.java' | grep -v node_modules | grep -v vendor | grep -v __pycache__ | wc -l
```

Resuma para o usuario:
- Para que serve este repo
- Stack tecnologica detectada
- Tamanho (arquivos, linhas de codigo aproximadas)
- Qualidade da documentacao (existencia e completude do README)
- Maturidade (tem testes? tem CI? tem Docker?)

## Fase 3 — Plano de Testes (GATE HUMANO)

Gere um plano estruturado baseado no que descobriu na Fase 2. Formato:

```markdown
## Plano de Validacao: {owner}/{repo}

### Resumo
{1-2 frases sobre o que o repo faz}

### Ambiente
- Linguagem: {linguagem}
- Package manager: {pm}
- Framework de teste: {framework}
- Isolamento: {venv / local node_modules / cargo target / docker}

### Instalacao
- {passo a passo do que precisa instalar}
- {sempre em ambiente isolado — nunca global}

### Testes a executar
1. **Lint/Type check** — {comando} — {o que valida}
2. **Testes unitarios** — {comando} — {o que valida}
3. **Build** — {comando} — {o que valida}
4. **Testes E2E** (se aplicavel) — {comando} — {o que valida}
5. **Coverage** — {comando} — {o que mede}
6. **Audit de seguranca** (se aplicavel) — {comando} — {o que valida}

### Metricas a coletar
- [ ] Test pass rate (pass/total)
- [ ] Coverage percentual
- [ ] Tempo de execucao dos testes
- [ ] Tempo de build
- [ ] Tamanho do bundle/output
- [ ] Dependencias com vulnerabilidades conhecidas
- [ ] Complexidade (se tooling disponivel)

### Riscos
- {deps que precisam de rede?}
- {secrets necessarios?}
- {recursos pesados (GPU, memoria)?}
- {plataforma especifica?}
```

**PARE AQUI.** Apresente o plano ao usuario e espere aprovacao explicita antes de continuar.

Se o usuario quiser modificar o plano (adicionar/remover testes, mudar metricas), ajuste e reapresente.

## Fase 4 — Instalacao (Isolada)

Apos aprovacao do plano, instale dependencias em ambiente isolado.

### Python
```bash
cd ~/.cache/repo-validator/repos/{owner}-{repo}
python3 -m venv .validator-venv
source .validator-venv/bin/activate
pip install -e . 2>/dev/null || pip install -r requirements.txt 2>/dev/null || pip install -e ".[dev]" 2>/dev/null
```

### Node/TypeScript
```bash
cd ~/.cache/repo-validator/repos/{owner}-{repo}
# Detectar package manager
test -f pnpm-lock.yaml && pnpm install || \
test -f yarn.lock && yarn install || \
npm install
```

### Go
```bash
cd ~/.cache/repo-validator/repos/{owner}-{repo}
go mod download
go build ./...
```

### Rust
```bash
cd ~/.cache/repo-validator/repos/{owner}-{repo}
cargo build
```

### Regras de isolamento
- **NUNCA** use `npm install -g`, `pip install` global, ou equivalente
- **NUNCA** modifique arquivos do sistema (/usr, /etc)
- **SEMPRE** use venv para Python, node_modules local para Node
- Se a instalacao falhar, reporte o erro detalhado e pergunte se quer continuar com os testes que forem possiveis

## Fase 5 — Execucao

Crie o diretorio de resultados:

```bash
mkdir -p ~/.cache/repo-validator/repos/{owner}-{repo}/.validator-results
```

Execute cada teste do plano aprovado, um por vez. Para cada um:

1. **Anote timestamp de inicio**
2. **Execute o comando**
3. **Capture stdout + stderr** para `.validator-results/{test-name}.log`
4. **Anote timestamp de fim**
5. **Extraia metricas** (pass rate, coverage, tempo, etc.)

### Testes comuns por linguagem

**Python:**
```bash
# Lint
ruff check . 2>&1 | tee .validator-results/lint.log
# ou: flake8 . 2>&1 | tee .validator-results/lint.log

# Testes + coverage
pytest --cov=. --cov-report=term-missing --tb=short 2>&1 | tee .validator-results/tests.log
```

**Node/TypeScript:**
```bash
# Type check
npx tsc --noEmit 2>&1 | tee .validator-results/typecheck.log

# Lint
npx eslint . 2>&1 | tee .validator-results/lint.log

# Testes
npm test 2>&1 | tee .validator-results/tests.log
# ou: npx jest --coverage 2>&1 | tee .validator-results/tests.log
# ou: npx vitest --coverage 2>&1 | tee .validator-results/tests.log
```

**Go:**
```bash
go test ./... -v -cover 2>&1 | tee .validator-results/tests.log
go vet ./... 2>&1 | tee .validator-results/vet.log
```

**Rust:**
```bash
cargo test 2>&1 | tee .validator-results/tests.log
cargo clippy 2>&1 | tee .validator-results/clippy.log
```

### Audit de seguranca (se aplicavel)
```bash
# Python
pip audit 2>&1 | tee .validator-results/audit.log
# ou: safety check 2>&1 | tee .validator-results/audit.log

# Node
npm audit 2>&1 | tee .validator-results/audit.log
```

### Tratamento de erros
- Se um teste falhar (comando retorna non-zero), nao pare — continue com os proximos
- Se um teste quebrar por falta de dependencia opcional, anote e continue
- Se TODOS os testes falharem por erro de instalacao, va direto para o Relatorio com veredito "Unable to validate"

## Fase 6 — Relatorio

Gere um relatorio markdown estruturado. Salve em:
- `~/.cache/repo-validator/repos/{owner}-{repo}/.validator-results/REPORT.md`
- E apresente no chat

### Template do relatorio

```markdown
# Validacao: {owner}/{repo}

**Data:** {YYYY-MM-DD HH:MM}
**Versao avaliada:** {commit hash ou tag}
**Tempo total:** {minutos}

## Veredito: {RECOMMENDED / CONDITIONAL / NOT RECOMMENDED / UNABLE TO VALIDATE}

### Metricas

| Metrica | Resultado | Status |
|---------|-----------|--------|
| Testes | {pass}/{total} ({percent}%) | {pass/warn/fail} |
| Coverage | {percent}% | {pass/warn/fail} |
| Tempo de teste | {seconds}s | - |
| Build | {success/fail} | {pass/fail} |
| Lint | {errors} errors | {pass/warn/fail} |
| Vulnerabilidades | {count} ({severity}) | {pass/warn/fail} |
| Tamanho do repo | {MB} | - |
| Arquivos de codigo | {count} | - |

### Pontos fortes
- {bullet points com o que funcionou bem}

### Pontos fracos
- {bullet points com problemas encontrados}

### Notas tecnicas
- {observacoes sobre arquitetura, qualidade de codigo, etc.}
- {comparacao com repos similares ja avaliados, se aplicavel}

### Logs detalhados
Disponiveis em: `~/.cache/repo-validator/repos/{owner}-{repo}/.validator-results/`
```

### Criterios de veredito

- **RECOMMENDED**: testes passam >= 90%, coverage >= 70%, sem vulnerabilidades high/critical, build sucesso
- **CONDITIONAL**: testes passam >= 70%, coverage >= 40%, sem critical (high toleravel se documentado)
- **NOT RECOMMENDED**: testes passam < 70%, ou critical sem fix, ou build falha
- **UNABLE TO VALIDATE**: nao foi possivel instalar ou rodar testes

### Atualizar historico

Salve a avaliacao no JSON de historico para comparacoes futuras:

```bash
# Ler JSON atual, adicionar nova entrada, salvar
```

Estrutura de cada entrada no `evaluations.json`:

```json
{
  "repo": "owner/repo",
  "date": "2026-06-23T12:00:00",
  "commit": "abc1234",
  "verdict": "CONDITIONAL",
  "metrics": {
    "tests_pass": 42,
    "tests_total": 45,
    "coverage": 87.3,
    "build_success": true,
    "lint_errors": 2,
    "vulns": 0,
    "test_time_seconds": 3.2,
    "repo_size_mb": 12.5,
    "code_files": 38
  },
  "strengths": ["..."],
  "weaknesses": ["..."]
}
```

Use Python ou jq para fazer o merge no JSON existente.

## Fase 7 — Cleanup

Pergunte ao usuario: **"Manter repo no cache para reuso futuro, ou remover tudo?"**

### Se REMOVER:
```bash
rm -rf ~/.cache/repo-validator/repos/{owner}-{repo}
```

Isso remove: codigo fonte, venv, node_modules, resultados de teste, tudo.

### Se MANTER:
- O repo fica disponivel para re-validar depois sem re-clonar
- Para limpar manualmente depois: `rm -rf ~/.cache/repo-validator/repos/{owner}-{repo}`

## Comparacao entre repos

Se o usuario pedir para comparar repos ja avaliados, leia `~/.cache/repo-validator/evaluations.json` e gere uma tabela comparativa lado a lado com todas as metricas coletadas.

## Regras criticas

1. **ISOLAMENTO TOTAL** — nunca instala nada global, nunca modifica sistema
2. **GATE HUMANO obrigatorio** — Fase 3 sempre para e espera aprovacao
3. **CLEANUP sempre oferecido** — Fase 7 sempre pergunta sobre remocao
4. **LOGS preservados** — todos os outputs de teste salvos em .validator-results/
5. **REPRODUCIVEL** — commit hash e versoes das tools sao registrados
6. **NUNCA executa codigos do repo fora de sandbox/venv** — risco de scripts maliciosos
7. **NUNCA roda scripts de install sem antes ler o que eles fazem** — leia package.json scripts, Makefile targets, setup.py antes de executar
8. **CACHE isolado** — todo o trabalho fica em `~/.cache/repo-validator/`, nunca polui o workspace atual
