---
name: skill-ab-benchmark
description: Roda um benchmark A/B automatico de uma skill/ruleset de coding agent. Dado um ruleset (ex: ponytail) e um conjunto de tarefas, dispara dois bracos (COM o ruleset injetado no system prompt vs SEM) usando subagentes Sonnet, extrai o codigo gerado, mede LOC/arquivos/deps e gera um comparativo com checklist de seguranca. Use quando o usuario pedir para "testar uma skill", "benchmark A/B", "comparar com e sem a skill", "medir o efeito de um ruleset" ou avaliar o impacto pratico de um prompt/skill em geracao de codigo.
category: Coding
allowed-tools: [Agent, Bash, Read, Write, Glob, Grep]
---

Voce executa um benchmark A/B controlado para medir o efeito REAL de uma skill/ruleset de coding agent na geracao de codigo. Diferente de auditar a saude de um repo, aqui voce mede o output: roda a MESMA tarefa com e sem o ruleset e compara.

## Fluxo de uso (conversacional — leia ANTES de tudo)

Esta skill e conduzida por conversa, nao por formulario. Nunca dispare runs sem um plano de tarefas APROVADO pelo usuario. O usuario chega de UM destes tres jeitos — detecte qual e e siga:

1. **Usuario ja traz o ruleset + as tarefas** ("roda a skill X com essas 3 tarefas: ..."). Voce confirma o entendimento (lista as tarefas que entendeu, aponta se alguma e fraca como trap), pede o "ok" e roda.
2. **Usuario pede sugestoes** ("que tarefas voce sugere pra testar a skill X?"). Voce LE o ruleset (SKILL.md/AGENTS.md/README do repo) pra entender o que ele promete, e ENTAO propoe um plano sob medida pra aquela promessa.
3. **Usuario so joga o repo/ruleset** ("testa essa skill aqui: <repo>"). Voce assume a iniciativa: le o ruleset, deduz o tipo (corta codigo vs comprime prosa), e PROPOE o plano de tarefas + armadilhas pra aprovacao.

**O plano que voce apresenta pra aprovacao SEMPRE contem (formato curto, em bullets):**
- **Tipo do ruleset** (corta codigo -> metrica LOC/arquivos/deps · comprime prosa -> metrica palavras/tokens) e a metrica escolhida.
- **As 3+ tarefas** (ver gate abaixo), cada uma com: spec de 1 linha + a **armadilha** que ela arma (o que o ruleset PODE cortar errado). Misture: pelo menos uma trap forte de over-build, pelo menos uma honesta/minima.
- **Setup**: modelo (Sonnet — default fixo, nunca Haiku), n (1=POC, 4=robusto), nº total de runs = tarefas × bracos × n, e bracos (baseline / +controle terse se for prosa / treatment).
- **Custo estimado** (Sonnet por token; avise o usuario do custo total estimado).

So depois do "ok" explicito do usuario voce vai pra Fase 1. Se ele pedir ajuste no plano, ajuste e re-apresente. Trate o "armadilha" como o coracao do valor: e onde a skill revela se cortou gordura ou cortou musculo.

## GATE DE PUBLICACAO (regra dura)

Um benchmark so pode ser PUBLICADO (relatorio final, video, redes, comparativo entre skills) com **no minimo 3 tarefas distintas** rodadas COM e SEM o ruleset. Uma tarefa unica nunca e conclusiva — o resultado muda muito de uma tarefa pra outra (vide o caso do xadrez vs date-picker). Regra:
- **< 3 tarefas** = apenas PILOTO/POC. O relatorio TEM que estampar "piloto, nao publicavel" e voce avisa o usuario antes de qualquer publicacao.
- **>= 3 tarefas** = publicavel. Use tarefas variadas (pelo menos uma com over-build trap forte, pelo menos uma "honesta"/minima) pra o numero medio nao ser viesado.
- Se o usuario der so 1 tarefa, EXECUTE como piloto mas PROPONHA mais 2 antes de fechar como benchmark da skill.

## Conceito

Um ruleset de coding (ex: ponytail, caveman, um system prompt custom) e basicamente texto injetado no system prompt do agente. O benchmark:
1. Pega N tarefas de coding (idealmente com "over-build trap" — onde o ruleset deve fazer diferenca).
2. Para cada tarefa roda 2 bracos: `treatment` (ruleset injetado) e `baseline` (sem).
3. Mede o codigo produzido: LOC, nº de arquivos, deps novas.
4. Checa se o treatment manteve seguranca (validacao, error handling, a11y, teste).
5. Repete `n` vezes por braco para robustez.
6. Gera relatorio comparativo.

## Variaveis de ambiente

- `ROOT=~/.cache/skill-ab/{run-name}` — workspace isolado do run
- Estrutura: `{ROOT}/{task}/{arm}/run{k}/` recebe os arquivos extraidos

## Fase 0 — Plano aprovado (consolide o que saiu da conversa)

Voce so chega aqui DEPOIS do "ok" do usuario no plano (ver "Fluxo de uso" no topo). Consolide:
- **Ruleset / skill alvo**: o texto do system prompt a injetar no braco treatment. Se for uma skill instalada, leia o SKILL.md/AGENTS.md e use o corpo como ruleset.
- **Tarefas (com armadilha)**: MINIMO 3 para benchmark publicavel (ver GATE DE PUBLICACAO no topo). 1 tarefa = so piloto. Cada tarefa = 1 paragrafo de spec + "Make it production-quality", e voce sabe qual armadilha ela arma. Misture: pelo menos uma com over-build trap forte (date picker, debounce, validacao de email, color picker, cache simples, formatador de data, jogo simples) e pelo menos uma honesta/minima.
- **n** (runs por braco): 1 para POC rapido, 4 para numero robusto (default 1, sugira 4).
- **Modelo**: Sonnet sempre (default fixo, NUNCA Haiku). Os dois bracos usam o mesmo modelo pra ser justo.

## Fase 1 — Disparar os bracos (CRITICO: output inline)

**LICAO APRENDIDA: subagentes rodam com Write/Bash BLOQUEADOS.** Eles NAO conseguem gravar arquivos. Por isso os agentes devem RETORNAR o codigo inline no texto da resposta, e o orquestrador (voce) grava depois.

Lance os subagentes via `Agent` tool (`subagent_type: general-purpose`, `model: sonnet`, `run_in_background: true`), em paralelo. Numero de agentes = tarefas × 2 bracos × n.

### Prompt do braco BASELINE
```
You are a senior {role} developer. Do NOT use any tools. Produce your answer entirely as text.

TASK: {spec da tarefa}. Make it production-quality.

OUTPUT FORMAT: For each file you would create, emit a block exactly like this:
=== FILE: relative/path.ext ===
<full file contents>
=== END FILE ===
Include every file. Output only these file blocks, nothing else.
```

### Prompt do braco TREATMENT
Identico ao baseline, mas com o ruleset prefixado:
```
SYSTEM RULESET (follow strictly):
{texto completo do ruleset/skill alvo}

Act as a senior {role} developer under the ruleset above. Do NOT use any tools. Produce your answer entirely as text.

TASK: {mesma spec}. Make it production-quality.

OUTPUT FORMAT: {mesmo bloco === FILE: === do baseline}
```

Guarde o mapa agentId -> (task, arm, run). Espere TODOS terminarem (as notificacoes chegam sozinhas — nao faca polling).

## Fase 2 — Extrair os arquivos

**LICOES APRENDIDAS (parser tem que ser robusto a 3 armadilhas):**
1. O `{agentId}.output` e um TRANSCRIPT JSONL, nao texto puro. Leia linha a linha, `json.loads`, pegue so as mensagens `role == "assistant"` e concatene os blocos `content[].type == "text"`. O prompt do usuario (role user) contem o TEMPLATE de exemplo `=== FILE: ===` — se voce parsear o arquivo cru vai pegar falso positivo.
2. Saidas grandes nem sempre terminam o bloco com `=== END FILE ===` — alguns agentes usam so a cerca ```` ``` ```` de fechamento. NAO dependa do marcador END. Extraia por HEADER: ache cada `=== FILE: path ===`, o corpo vai dali ate o PROXIMO header (ou fim).
3. O braco baseline costuma embrulhar o conteudo em ```` ```lang ... ``` ```` — remova as cercas ao gravar.

Grave cada arquivo em `{ROOT}/{task}/{arm}/run{k}/{path}`. Parser de referencia (rode via Bash):

```python
import os, re, json
HEADER = re.compile(r"=== FILE: (.+?) ===")
def clean(body):
    body = re.split(r"=== END FILE ===", body)[0].strip("\n")
    m = re.match(r"^```[a-zA-Z0-9]*\n(.*)\n```\s*$", body.strip(), re.DOTALL)
    return m.group(1) if m else body
def assistant_text(path):
    out = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line: continue
        try: rec = json.loads(line)
        except Exception: continue
        msg = rec.get("message", {})
        if msg.get("role") != "assistant": continue
        for blk in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            if isinstance(blk, dict) and blk.get("type") == "text":
                out.append(blk.get("text", ""))
    return "\n".join(out)
def extract(text):
    ms = list(HEADER.finditer(text)); files = []
    for i, m in enumerate(ms):
        path = m.group(1).strip().lstrip("/")
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        files.append((path, clean(text[m.end():end])))
    return files
```

## Fase 3 — Medir

Para cada `{task}/{arm}/run{k}`:
- **LOC**: linhas nao-vazias dos arquivos de codigo (ignore arquivos so de config se quiser, mas registre separado). Conte com um script, NAO no olho.
- **Arquivos**: total de arquivos gerados.
- **Deps novas**: pacotes adicionados (cheque imports + package.json).

Script de medicao (Bash + python): ande por cada arm dir, conte arquivos, e para .ts/.tsx/.js/.jsx/.py/.css/.go conte linhas com `strip()` nao-vazio.

Agregue por (task, arm): media de LOC/arquivos/deps entre os n runs.

## Fase 4 — Checklist de seguranca (qualitativo)

O ponto critico de um ruleset "lazy" e: cortou codigo SEM cortar seguranca? Para cada braco treatment, leia o codigo e marque:
- [ ] Validacao de input em trust boundary mantida
- [ ] Error handling que evita perda de dado mantido
- [ ] Acessibilidade (label/aria) mantida quando aplicavel
- [ ] Deixou pelo menos UM teste/check rodavel para logica nao-trivial

Reporte qualquer caso onde o treatment cortou seguranca junto com o codigo — isso e o achado mais importante.

## Fase 5 — Relatorio (HTML e o entregavel PADRAO)

O entregavel final SEMPRE e um HTML no layout padrao da skill. Copie
`report-template.html` (nesta pasta) para `{ROOT}/report.html`, preencha os campos
`{{...}}` e os blocos marcados `<!-- FILL -->`, e abra no navegador
(`xdg-open`/`open`/`start`) quando o usuario pedir. NUNCA abra automatico.

**LINGUAGEM DO HTML (regra dura — o relatorio e PUBLICO/leigo):** NUNCA escreva os termos tecnicos `baseline`, `terse`, `treatment`, `braco`, `controle` na pagina renderizada. Traduza SEMPRE para nomes que qualquer pessoa entende:
- `baseline` -> **"Agente solto"** (sem regra nenhuma)
- `terse` (controle de prosa) -> **'Só "seja breve"'** (a instrucao gratuita)
- `treatment` -> **"Com a skill"**
- `vs controle` -> **"Ganho da skill"** · `vs baseline` -> **"vs agente solto"**
Inclua sempre um "Por que 3 colunas?" (1 frase explicando que o numero honesto e contra "só pedir pra ser breve") e um "lê assim:" abaixo da tabela narrando uma linha. Os termos tecnicos so existem internamente (prompts/JSON), nunca na UI.

**Estrutura fixa do HTML (nao reordenar):**
1. **Cenário exato do teste** — cards das colunas ("Agente solto" / 'Só "seja breve"' opcional / "Com a skill") + a lista das tarefas IDENTICAS na integra + linha de setup (modelo, n, total de runs, metrica) em linguagem simples. Esta secao e obrigatoria: e o que faz o leitor entender o "com vs sem" antes de ver numero.
2. **KPIs** — 3 numeros grandes (ex: ganho da skill vs "seja breve", vs agente solto, claim anunciada/perda de seguranca).
3. **Tabela** por tarefa (Agente solto / 'Só "seja breve"' / Com a skill / Ganho da skill / vs agente solto + linha media). `class="good"` p/ corte, `class="bad"` p/ piora.
4. **Achado central (sem hype)** no callout — numero honesto vs a claim do ruleset, com ressalvas de metodologia.
5. **Onde ganha / onde nao ganha**.
6. **Exatidao tecnica** (prosa) ou **Seguranca preservada** (codigo) — checklist; use `class="warn"` se algo foi cortado.
7. **Veredito** + proximo passo (n=4 / modo ultra / medicao exata).

Salve tambem `{ROOT}/REPORT.md` (mesmo conteudo em markdown, para grep/diff) e
apresente um resumo curto no chat. Por fim, grave uma linha no historico
`~/.cache/skill-ab/evaluations.json` (crie `[]` se nao existir):
{ ruleset, date, model, mode, n, tasks, metric, mean_delta_vs_control, mean_delta_vs_baseline, safety_notes }.

**Metrica depende do tipo de ruleset:**
- Ruleset que corta CODIGO (ex: ponytail) -> metrica = LOC / arquivos / deps. Coluna da tabela = LOC.
- Ruleset que comprime PROSA (ex: caveman, "code blocks unchanged") -> metrica = tokens/palavras da resposta. Coluna = palavras. Inclua um braco de controle `terse` ("Answer concisely.") pra nao inflar o numero (caveman vs terse = delta honesto; vs baseline = delta vs verboso). Para prosa as tarefas sao perguntas de explicacao/debug, nao geracao de codigo.

## Fase 6 — Cleanup

Pergunte: manter o workspace `{ROOT}` para reuso, ou remover (`rm -rf {ROOT}`).

## Regras criticas

1. **Justica**: mesmo modelo, mesma spec, mesmo formato de output nos dois bracos. So muda o ruleset injetado.
2. **Output inline obrigatorio**: subagentes nao escrevem arquivos — eles retornam o codigo, voce grava.
3. **Mede com script, nao no olho**: LOC contado por programa.
4. **>= 3 TAREFAS para publicar** (gate duro, ver topo). Alem disso, **n>=4 runs por braco** para qualquer numero citado publicamente (n=1 e so POC, rotule como tal). Tarefa unica = sempre piloto.
5. **Tarefas com trap revelam mais**: se as tarefas ja sao minimas, a diferenca some — isso e esperado e deve ser dito.
6. **Seguranca acima de tamanho**: um treatment que corta validacao nao e "melhor" por ter menos LOC — destaque isso.
7. **Custo**: Sonnet sempre (nunca Haiku); avise o custo total estimado. n × tarefas × 2 = total de runs.
