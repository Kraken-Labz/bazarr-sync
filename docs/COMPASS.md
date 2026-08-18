# COMPASS.md — Bazarr Bridge (HA) + Jellyfin Bazarr Sync

> **Plano executivo canônico do projeto.**  
> Ler este arquivo antes de iniciar qualquer trabalho.  
> Atualizar `docs/STATE.md` a cada etapa concluída.

---

## DECISÕES JÁ TOMADAS — NÃO REABRIR SEM MOTIVO TÉCNICO

| ID | Decisão |
|----|---------|
| D-01 | Projeto dividido em dois produtos: **A. Bazarr para HA** | **B. Bazarr Sync para Jellyfin** |
| D-02 | Projeto A vem primeiro; B só começa quando A estiver comprovado |
| D-03 | Projeto A parte do `owenvoke/hass-bazarr` (fork/evolução, não rewrite) |
| D-04 | Não recriar interface completa do Bazarr — expor operações úteis |
| D-05 | Bazarr baixa/sincroniza; HA e Jellyfin são interfaces/orquestradores |
| D-06 | API key do Bazarr **nunca** vai para frontend/browser |
| D-07 | Frontend **nunca** envia path arbitrário — backend resolve e valida |
| D-08 | Filmes/episódios **não** viram entidades HA — usar actions + WS |
| D-09 | Octopus Media Card **não** será alterado agora — integração preparada para ele |
| D-10 | Projeto B = repositório/produto separado |
| D-11 | Jellyfin v1: botão na página de detalhes (antes do playback), **não** no OSD |
| D-12 | Jellyfin v1: **apenas SYNC** de legenda existente; busca/download depois |
| D-13 | Projeto B backend = plugin .NET (template oficial Jellyfin) |
| D-14 | UI Jellyfin: avaliar **JavaScript Injector** primeiro |
| D-15 | Suporte inicial: Jellyfin Web + clientes que usem esse frontend |
| D-16 | **HA-PROD nunca** usado para desenvolvimento |
| D-17 | Kraken Jellyfin produção **não** alterado sem autorização explícita |

---

## FASES DO PROJETO A — BAZARR PARA HOME ASSISTANT

### FASE 0 — FUNDAÇÃO ✅
- [x] Repositório preparado
- [x] Upstream importado (`owenvoke/hass-bazarr` @ `65c27a3`)
- [x] Licença MIT confirmada
- [x] Código-base auditado (config flow, coordinator, sensores, auth, HACS)
- [x] Documentação mínima: README, AGENTS, PROJECT, STATE, CHANGELOG, COMPASS

### FASE 1 — CONTRATO REAL DA API BAZARR ✅
- [x] Endpoints confirmados via código Bazarr + instância lab
- [x] Auth: `X-API-KEY` header
- [x] Movies/Series/Episodes listing
- [x] Manual search movie/episode
- [x] Download específico movie/episode (form-encoded)
- [x] Sync references (camelCase params)
- [x] Sync action (form-encoded)

### FASE 2 — BAZARRCLIENT ✅
- [x] `client.py` isolado com toda comunicação HTTP
- [x] Exceções tipadas: `BazarrAuthError`, `BazarrNotFoundError`, `BazarrTimeoutError`, `BazarrError`
- [x] Models: `MediaReference`, `SubtitleCandidate`, `InstalledSubtitle`, `SyncReference(s)`
- [x] Testes unitários: 22 passando
- [x] Nenhum HTTP espalhado; API key nunca em logs

### FASE 3 — INTEGRAÇÃO HOME ASSISTANT ✅
- [x] Config flow preservado + bug fix `isinstance`
- [x] Coordinator delega ao `BazarrClient` + bug fix 401/timeout
- [x] Sensores preservados: wanted_movies, wanted_episodes, health_issues
- [x] Entity base para DRY device_info

### FASE 4 — ACTIONS DO HOME ASSISTANT ✅
- [x] `bazarr.search_subtitles` (com response data)
- [x] `bazarr.download_subtitle`
- [x] `bazarr.sync_subtitle`
- [x] Schemas em `services.yaml`
- [x] Validação de args, erros úteis, sem paths arbitrários

### FASE 5 — API INTERATIVA / WEBSOCKET ✅
- [x] 6 comandos WS: `get_media`, `get_subtitles`, `search_subtitles`, `download_subtitle`, `get_sync_references`, `sync_subtitle`
- [x] Auth HA obrigatória; API key Bazarr nunca retornada
- [x] Input validation + erros normalizados
- [x] Testes unitários: 10 passando

### FASE 6 — MVP REAL DE FILME ✅
- [x] Selecionar movie real no Bazarr lab
- [x] Listar legendas instaladas
- [x] Manual search → candidatos
- [x] Escolher candidato → baixar
- [x] Confirmar legenda instalada
- [x] Listar referências de sync
- [x] Escolher áudio → sync
- [x] Confirmar resultado

### FASE 7 — MVP REAL DE EPISÓDIO ✅
- [x] Mesmo ciclo para episódio (Sonarr IDs → search → download → sync)

### FASE 8 — HARDENING ✅
- [x] 401/403/404/timeout/Bazarr offline/candidato expirado/media não encontrado
- [x] Concorrência (semaphore), retry exponencial (GET/HEAD/OPTIONS), logs com correlation IDs
- [x] Type hints estritos (mypy --strict), Ruff, Black, 59 testes (→ 65)
- [x] Path security: `subtitle_id` + `reference_id` (frontend não envia paths)
- [x] Config Entry API: `config_entry` → `config_entry_id` (Services + WS)
- [x] Domain migration: `bazarr` → `bazarr_sync`

### FASE 9 — PREPARAÇÃO HACS 🔄 **CURRENT**
- [x] manifest.json, hacs.json, version `0.1.0-beta.1`, README, LICENSE
- [x] CI: GitHub Actions (pytest, mypy, ruff, black, Hassfest, HACS)
- [x] icon.png (256x256), translations/en.json atualizado
- [x] README.md com instruções de instalação e API
- [x] CHANGELOG.md atualizado
- [ ] Instalação limpa via Custom Repository no HA-LAB
- [ ] Upgrade/reinstall/remoção limpa

---

## FASES DO PROJETO B — JELLYFIN BAZARR SYNC

> Só inicia após **FASE 9** do Projeto A ou ponto equivalente registrado.

### J0 — LAB JELLYFIN ⏳
### J1 — PLUGIN BACKEND .NET ⏳
### J2 — MAPEAMENTO JELLYFIN ↔ BAZARR ⏳
### J3 — SYNC BACKEND ⏳
### J4 — BOTÃO NA PÁGINA DE DETALHES ⏳
### J5 — TESTE REAL ⏳
### J6 — HARDENING ⏳
### J7 — MVP COMPLETE ⏳

---

## STATE MACHINE — FORMATO OBRIGATÓRIO EM `docs/STATE.md`

```markdown
CURRENT_PHASE: F6
CURRENT_TASK: Validar movie end-to-end no Bazarr lab
STATUS: in_progress
LAST_VALIDATED: WebSocket search/download/sync (unit tests)
BLOCKERS: none
NEXT_ACTION: Conectar ao Bazarr lab e executar fluxo completo de filme
```

---

## REGRAS DE AUTONOMIA

**Avançar sozinho em:**
- Leitura/auditoria de código, pesquisa técnica, desenvolvimento, refactors no escopo
- Criação/ajuste de testes, ambientes lab (HA-LAB, containers, Bazarr lab)
- Documentação, correções descobertas durante testes, validações
- Commits locais (se fluxo git já configurado)

**PARE e peça decisão somente quando:**
1. Alteração destrutiva/irreversível
2. Modificar HA-PROD
3. Modificar Jellyfin Kraken produção
4. Armazenar/expor credenciais
5. Duas alternativas arquiteturais materialmente diferentes sem decisão registrada
6. Incompatibilidade que obrigue abandonar requisito aprovado
7. Publicar/release público
8. Impossibilidade técnica comprovada de seguir o plano
9. Risco de afetar outro projeto no ambiente compartilhado

---

## CRITÉRIO DE "DONE"

Uma tarefa só é **DONE** quando:
1. Implementada
2. Testada
3. Validada no ambiente adequado
4. Sem erro novo relevante
5. Documentação atualizada
6. `STATE.md` atualizado

Uma fase só é **DONE** quando **todos os seus gates passam**.

---

## REGRA CONTRA OVERENGINEERING

Sempre preferir a implementação **menor** que satisfaça:
- Requisito atual
- Segurança
- Manutenção razoável
- Testes

**Não criar:**
- Framework interno, event bus próprio, banco próprio, sistema de plugins próprio
- Abstrações para futuros requisitos não aprovados
- Infraestrutura distribuída, microserviços

> Estamos construindo **duas integrações pequenas e úteis**, não uma plataforma.