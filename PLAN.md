# working-bee — plano do projeto

> **working bee** (inglês da Austrália e do Reino Unido) é um mutirão: gente que se junta para fazer, de graça, um
> trabalho que ninguém faria sozinho. Aqui, os vizinhos são agentes, e o celeiro é o seu projeto.

Documento vivo. Status em 2026-11-24: **Fases 0 e 1 entregues localmente** (aguardando validação do autor e push).

## 1. Objetivos

1. **Aprender e dominar o Claude Code** fazendo: skills, hooks, subagentes, plugins, marketplace, orquestração,
   equipes de agentes e evals. Cada conceito entra porque resolve uma necessidade real, não por demonstração.
2. **Parar de reconfigurar cada projeto.** Um repo novo ou sem guardrails fica pronto com poucas linhas de
   `.claude/settings.json`, que só dizem quais plugins ligar e com quais opções.
3. **Ser compartilhável de graça.** Plugins genéricos, configuráveis, documentados em inglês, com licença MIT.
4. **Demonstrar AI fluency** com evidência: testes, evals com baseline (com e sem o plugin), custo em tokens e
   decisões registradas (ADRs).

## 2. Princípios (não negociáveis)

- **Inspiração, nunca cópia.** O marketplace da empresa é PROPRIETARY. Dele vêm só ideias e padrões, que já são
  públicos na documentação da Anthropic. Nada de código, texto, nomes internos, processos, URLs ou nomes de
  colegas. As skills escritas lá são reescritas do zero, genéricas.
- **Local primeiro.** Commit local; push e PR só depois de validar rodando.
- **Defender linha por linha.** Nada entra sem que o autor saiba explicar.
- **Privacidade por padrão.** Uma trava de privacidade vale desde o primeiro commit. Segredos, tokens e dados
  pessoais nunca entram no repo. O `env` do `~/.claude/settings.json` (que tem um token) nunca vira template.
- **Hooks em Python, só stdlib.** Em erro inesperado, liberam a chamada (fail-open), exceto as travas de
  segurança explícitas. Cada hook tem teste rodando como subprocesso real.
- **Skills enxutas.** O SKILL.md é curto, os detalhes ficam em `references/` e são lidos sob demanda. Contexto
  custa caro.
- **Documentação em inglês**, com um `README.pt-BR.md`. (Este plano fica em português enquanto o repo for
  privado; antes de abrir, traduzir ou mover para `docs/`.)

## 3. Onde cada coisa mora (níveis de configuração)

| Nível | Onde | Vale para | O que vai aí |
|---|---|---|---|
| Gerenciado | política do sistema | todos, sem sobrescrever | (uso de empresa, não se aplica) |
| Usuário | `~/.claude/` | todos os projetos do usuário | gosto pessoal: modelo, idioma, status line, voz. Fica no repo `claude-config` |
| Projeto | `.claude/settings.json`, `AGENTS.md`, `.claude/skills/`, `.mcp.json` (no git) | quem abrir o repo | fatos e regras **daquele** repo, e quais plugins ligar |
| Local | `.claude/settings.local.json`, `CLAUDE.local.md` (fora do git) | só você, só ali | ajustes pessoais e segredos |
| **Plugin** | instalado de um marketplace | onde for habilitado (usuário ou projeto) | comportamento reutilizável: hooks, skills, agentes, MCPs, com opções configuráveis |

Plugin é um **pacote**, não um nível: ele entra no nível em que é habilitado. Marketplace é o catálogo git de
plugins. Regra de bolso:
- copiaria para o próximo projeto → plugin;
- só serve para aquele repo → projeto;
- é gosto pessoal → usuário.

**"Times" para quem trabalha sozinho:** no marketplace da empresa, cada time tem um plugin. Aqui, cada **chapéu**
(stack ou papel) tem um. O projeto liga os chapéus de que precisa. O `core` é dependência de todos e vem junto
automaticamente.

## 4. Arquitetura

```
working-bee/
├── .claude-plugin/marketplace.json      # catálogo (name: "working-bee")
├── plugins/
│   ├── core/            # guardrails + sessão; dependência de todos
│   ├── memory/          # learn-from-mistakes, gotchas, agents-md
│   ├── bootstrap/       # /bootstrap: prepara um repo novo
│   ├── dev-workflow/    # subagentes + /plan /slice /review /deliver
│   ├── python-backend/  # chapéu Python (ruff, pytest, Django/FastAPI)
│   ├── privacy/         # dados pessoais fora de commits e do contexto
│   ├── scraping/        # (Fase 7) coleta ética
│   ├── infra-gcp/       # (Fase 7) Terraform/gcloud com freio
│   └── voice/           # (a decidir) a skill talk, só Windows
├── evals/               # suites do `claude plugin eval`, por plugin
├── tests/               # testes dos hooks (subprocesso) e dos manifestos
├── docs/
│   ├── gotchas.md       # surpresas que custaram caro (com data de verificação)
│   ├── decisions/       # ADRs: uma decisão por arquivo
│   └── concepts.md      # mapa do Claude Code: o que é, quando usar, onde mora
├── AGENTS.md            # regras do próprio repo (Always / Ask First / Never)
├── CLAUDE.md            # contém só "@AGENTS.md"
├── .github/workflows/   # claude plugin validate + pytest
├── LICENSE              # MIT
└── README.md / README.pt-BR.md
```

**Dogfooding:** o próprio repo usa os seus plugins desde a Fase 1.

### Catálogo de plugins

| Plugin | Componentes | Opções (userConfig) | Inspiração / origem |
|---|---|---|---|
| **core** | Hooks: comandos perigosos (`rm -rf`, force push, push/commit na branch protegida, `reset --hard`, `--no-verify`); leitura/escrita de `.env` e chaves; proteção das próprias configs (`.claude/settings*`, hooks); "ask" para caminhos sensíveis; auditoria (PostToolUse); brief no SessionStart; contexto do git no PreCompact. Skill `/audit-settings` | branches protegidas, caminhos protegidos extras, comandos permitidos | `guard_git.py`, `guard_files.py`, `session_brief.py` (Garimpei); padrões vistos no trabalho |
| **memory** | Skills: `/learn` (erro → regra de uma linha no AGENTS.md), `/gotcha` (entrada em `docs/gotchas.md`), `/agents-md init\|audit\|update`. Talvez um hook Stop que só *sugere* `/learn` após uma correção | arquivo-alvo (AGENTS.md ou CLAUDE.md) | ideia do learn-from-mistakes; memória de feedback |
| **bootstrap** | Skill `/bootstrap`: pergunta stack e chapéus, gera AGENTS.md, CLAUDE.md, `.claude/settings.json` (marketplace + plugins + permissões base), `docs/gotchas.md`, template de PR, pre-commit | chapéus padrão | ideia do create-claude-md (reescrita) |
| **dev-workflow** | Agentes: `planner` (só lê), `implementer`, `qa`, `architecture-reviewer` (lê as regras em `docs/` do projeto), `adversarial-reviewer`, painel de analistas (prático, cético, simples, segurança). Skills: `/plan` (plano → GitHub Issues → branches), `/slice` (fatia tests-first → PR), `/review` (revisores em paralelo + passada adversarial), `/deliver` (um worker por issue em worktree, PRs para uma branch de integração), `/dependabot-triage`, `/quiz` (perguntas sobre o código para quem precisa defendê-lo) | modelo por papel, cobertura mínima | `refactor-slice-pr`, `dependabot-triage`, agente do Garimpei; padrões de orquestração vistos |
| **python-backend** | Hook pós-edição: `ruff check --fix` + `ruff format`. Skill de testes (detecta poetry/uv/pytest) | ferramenta de execução (poetry, uv, pip) | `ruff_on_edit.py` (Garimpei) |
| **privacy** | Hook que barra dados pessoais (listas fora do repo) em escrita, commit e push; skill que instala o pre-commit equivalente | caminho das listas de palavras permitidas e proibidas | privacy guard do InstaBot / whatsapp-mcp |
| **scraping** (F7) | Guardrails e skill de coleta ética: robots.txt, ritmo humano, limite diário, dados pessoais | limites | experiência InstaBot / Garimpei |
| **infra-gcp** (F7) | Hook: `terraform apply/destroy`, `gcloud ... create/delete` pedem confirmação; skill de revisão de plano do Terraform | projetos permitidos | padrão visto no trabalho (reescrito) |
| **voice** (?) | Skill `talk` (ditado + fala pt/en, Windows) | voz, velocidade | `claude-config/skills/talk` |

**O que não entra:**
- a status line, a skill `sl` e as settings pessoais (ficam no `claude-config`);
- `e2e-local` e as regras de arquitetura do Garimpei (ficam no Garimpei);
- o `caveman` (plugin de terceiros).

## 5. Fases

Cada fase termina com:
- funcionamento validado localmente pelo autor;
- entrada em `docs/gotchas.md` e ADR das decisões;
- atualização de `docs/concepts.md`;
- só então o push.

| Fase | Entrega | Conceitos aprendidos | Critério de pronto (teste real) |
|---|---|---|---|
| **0. Fundação** | estrutura, `marketplace.json`, `plugins/core` vazio, LICENSE, AGENTS.md, CI com `claude plugin validate` + pytest, `docs/concepts.md` inicial | marketplace, `plugin.json`, níveis de config, `/plugin marketplace add` local | `claude plugin validate .` passa; `/plugin install core@working-bee` funciona a partir do caminho local |
| **1. core** | hooks de guardrail + brief + PreCompact + testes + userConfig + `/audit-settings` | hooks (JSON no stdin, exit 2, `permissionDecision: ask`), matchers, userConfig, `claude plugin configure`, testes de hook | Garimpei remove `guard_git.py`, `guard_files.py` e `session_brief.py` e liga `core@working-bee`, sem perder proteção; um teste mostra cada bloqueio acontecendo |
| **2. memory** | `/learn`, `/gotcha`, `/agents-md` | skills: frontmatter, `description` que dispara certo, `argument-hint`, `allowed-tools`, `references/`; CLAUDE.md em camadas e `@import` | insulin-log ganha AGENTS.md; um erro real vira regra com `/learn`. **Fim da fase: auditoria de histórico e repo vira público** |
| **3. bootstrap + chapéus** | `/bootstrap`, `python-backend`, `privacy` | dependências entre plugins, `enabledPlugins` e `extraKnownMarketplaces` no projeto, opções por projeto | um repo novo do zero fica configurado em 5 minutos; o InstaBot e o whatsapp-mcp usam `privacy` |
| **4. dev-workflow** | agentes + `/plan`, `/slice`, `/review`, `/quiz`, `/dependabot-triage` | subagentes (frontmatter, `tools`, `model`, `permissionMode`), isolamento de contexto, modelo por papel, revisão adversarial, conteúdo não confiável (prompt injection) | uma feature do Garimpei vai de issue a PR pelo fluxo; `/review` acha algo que uma passada só não acharia |
| **5. Orquestração** | `/deliver` (worktrees em paralelo), agentes em segundo plano, experimento com equipe de agentes | dividir e juntar trabalho, worktrees, `--bg` e `claude agents`, equipes de agentes (experimental), workflows em script (se disponível) | scrapers OLX e Mercado Livre do Garimpei construídos em paralelo, cada um no seu PR |
| **6. Qualidade e lançamento** | evals por plugin com baseline, custo em tokens no README, versões com tag, README com GIF, `README.pt-BR.md`, CONTRIBUTING, post de lançamento | `claude plugin eval` (ablation com/sem plugin), `claude plugin details`, `claude plugin tag`, releases | README mostra "melhora X em Y pontos a Z tokens"; um estranho instala com 2 comandos |
| **7. Opcionais** | `scraping`, `infra-gcp`, MCP autoral dentro de um plugin, `voice` | MCP em plugin, opções secretas | conforme a necessidade |

### Status

| Fase | Estado |
|---|---|
| 0. Fundação | ✅ local (2026-11-24); falta push e o CI rodar no GitHub |
| 1. core | ✅ local (2026-11-24); falta o autor validar no Garimpei |
| 2. memory | ⏳ próxima |
| 3. bootstrap + chapéus | — |
| 4. dev-workflow | — |
| 5. Orquestração | — |
| 6. Qualidade e lançamento | — |
| 7. Opcionais | — |

## 6. Qualidade

- **Hooks:** um arquivo de teste por hook, rodando o script como subprocesso com o JSON real do evento. Cada
  regra tem um caso que **precisa** bloquear e um que **precisa** passar. Lição vista no trabalho: um hook que
  lê a interface errada (por exemplo, variáveis de ambiente que não existem) parece igual a um hook que funciona.
- **Manifestos e frontmatter:** `claude plugin validate` no CI, mais testes de schema próprios (nome em
  kebab-case, `description` com "Use when", nenhum nome reservado).
- **Evals (Fase 6):** suites em `evals/` para as skills avaliáveis (entrada estável, saída comparável). Para as
  outras, verificação binária manual. O critério de "vale avaliar?" fica num ADR.
- **Custo:** `claude plugin details` mede o custo em tokens de cada plugin; ele vai para o README.

## 7. Versionamento e distribuição

- **Decidido (ADR 0001):** semver desde `0.1.0`, com `claude plugin tag` nos releases. O `validate --strict` exige
  `version`, e o marketplace por caminho local ignora o pin durante o desenvolvimento.
- Uso em projeto: o `.claude/settings.json` declara `extraKnownMarketplaces.working-bee` (fonte GitHub) e
  `enabledPlugins`, de modo que quem confiar na pasta recebe o convite para instalar.

## 8. Riscos e dúvidas em aberto

- **Equipes de agentes** (verificado em 2026-11-24): existem, são experimentais e vêm desligadas; liga-se com
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Entram na Fase 5 como experimento, sem promessa.
- **Workflows em script** (verificado em 2026-11-24): plugins podem trazer `workflows/*.js` (está na referência
  oficial de plugins). Estudar a documentação na Fase 5.
- ~~Python no Windows~~ **resolvido** (ADR 0002): o `python3` era o stub da Microsoft Store, que sai com 49 e
  desliga a trava em silêncio. O lançador `run.sh` sonda e guarda o Python certo.
- **Regras por projeto:** o `userConfig` fica no nível de usuário. Resolvido com `.claude/working-bee.json`
  (ADR 0003).
- **Auditoria (PostToolUse) adiada:** um log de comandos pode guardar segredos digitados no comando. Reavaliar
  junto com o plugin `privacy` (Fase 3).
- **Nomes temáticos de abelha** para os plugins (por exemplo, `hive` para orquestração): a tendência é manter
  nomes funcionais e deixar o tema só no README e no logo.
- **`voice`:** vale publicar uma skill que só funciona no Windows? Decidir na Fase 3.
- **Contrato de trabalho:** manter tudo genérico, no tempo e no equipamento pessoal; sem nada específico da
  empresa.

## 9. Referências

- Documentação oficial: plugins, marketplaces, hooks, skills, subagentes (code.claude.com/docs).
- `claude plugin --help` (CLI 2.1.331): `validate`, `eval`, `configure`, `details`, `tag`, `init`, dependências
  com `prune`.
- Marketplaces da comunidade, para referência de estrutura: listas "awesome-claude-plugins" e
  claudemarketplaces.com.
