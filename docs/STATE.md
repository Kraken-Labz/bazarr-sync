# STATE.md — Bazarr Bridge (HA)

CURRENT_PHASE: F9
CURRENT_TASK: Aguardando validação HA-LAB pelo usuário
STATUS: completed (preparação técnica)
LAST_VALIDATED: FASE 9 preparação técnica completa + 65 testes unitários passando + mypy project-wide clean + Ruff clean + Black clean + Hassfest/HACS CI ready
BLOCKERS: GITHUB_REPOSITORY: not_created — repositório público ainda não criado
NEXT_ACTION: Usuário instalar Bazarr Sync no HA-LAB via instalação local/manual e validar

---

## STATUS

**Fase 9 preparação técnica concluída** — Projeto tecnicamente pronto para instalação no HA-LAB.

Fases 0–9 preparação técnica concluídas com gates validados:
- F0: Fundação ✅
- F1: Contrato API Bazarr ✅
- F2: BazarrClient ✅
- F3: Integração HA ✅
- F4: HA Actions ✅
- F5: WebSocket API ✅
- F6: MVP Real de Filme ✅
- F7: MVP Real de Episódio ✅
- F8: Hardening + Domain Migration + Config Entry API Migration ✅
- F9: Preparação HACS (manifest, CI, docs, packaging) ✅

---

## RESUMO FASE 9 — PREPARAÇÃO HACS

| Item | Status |
|------|--------|
| `manifest.json` | domain `bazarr_sync`, version `0.1.0-beta.1`, codeowners `@phgsbr`, docs próprio |
| `hacs.json` | `homeassistant: ">=2025.11.0"` |
| `icon.png` | 256x256 RGBA criado |
| `README.md` | Instruções de instalação local/manual (repo GitHub ainda não criado) |
| `CHANGELOG.md` | Atualizado com todas as mudanças F0–F9 |
| `translations/en.json` | Atualizado para `config_entry_id`, `subtitle_id`, `reference_id` |
| CI (GitHub Actions) | pytest, mypy, ruff, black, Hassfest, HACS |
| Version | `0.1.0-beta.1` |

---

## ESTADO REAL DO GITHUB

```
GITHUB_REPOSITORY: not_created
PUBLIC_RELEASE: none
HACS_CUSTOM_REPOSITORY_TEST: pending_repository_creation
GITHUB_OWNER: phgsbr
REPOSITORY_NAME: bazarr-sync (previsto)
```

O repositório público **ainda não existe**. A publicação do repositório é um checkpoint humano.

---

## VALIDAÇÕES AUTOMÁTICAS

```
pytest: 65 passed (31 client + 9 models + 13 services + 12 websocket)
Black: clean
Ruff: all checks pass
MyPy (--ignore-missing-imports): Success: no issues found in 12 source files
```

---

## PRÓXIMO PASSO: VALIDAÇÃO HA-LAB

**Ação requerida pelo usuário (instalação local/manual):**

1. Copiar `custom_components/bazarr_sync` para o HA-LAB em `config/custom_components/bazarr_sync`
2. Reiniciar Home Assistant
3. Adicionar integração "Bazarr Sync" via Settings → Devices & Services
4. Configurar URL e API Key do Bazarr
5. Validar os seguintes pontos:

| Check | Descrição |
|-------|-----------|
| Config Flow | Abre normalmente, aceita URL/API key, cria ConfigEntry LOADED |
| Reload/Restart | ConfigEntry persiste e carrega corretamente |
| Entities | Sensors (wanted_movies, wanted_episodes) + binary_sensor (health) |
| Actions | `bazarr_sync.search_subtitles` (response data), `download_subtitle`, `sync_subtitle` |
| WebSocket | 6 comandos sob namespace `bazarr_sync/*` |
| Multi ConfigEntry | Múltiplas instâncias funcionam independentemente |
| Path Security | `subtitle_id`/`reference_id` resolvidos server-side; paths arbitrários rejeitados |
| Secrets | API key não aparece em logs/responses; `X-API-KEY` só no backend |
| Logs | Sem tracebacks, sem warnings recorrentes, sem segredos |

**Permitido:** leitura, busca de candidatos, operações read-only  
**Proibido:** download/sync/delete/modificação em mídia de produção

---

## PENDÊNCIAS CONHECIDAS

- HA-LAB validation (requer ambiente do usuário)
- Criação do repositório GitHub público (checkpoint humano: CREATE_PUBLIC_GITHUB_REPOSITORY)
- Teste de HACS Custom Repository (após criação do repositório)
- Teste de upgrade/reinstall/remoção limpa no HA-LAB
- Teste de múltiplas ConfigEntries simultâneas no HA-LAB

---

## PRÓXIMO: PROJETO B

Após validação HA-LAB verde + criação do repositório GitHub → Projeto B (Jellyfin Bazarr Sync Plugin - .NET).

---

**F9_PREP_COMPLETE: ready for HA-LAB validation (local/manual)**

**NEXT_HUMAN_CHECKPOINT: CREATE_PUBLIC_GITHUB_REPOSITORY (owner: phgsbr, repo: bazarr-sync)**