# STATE.md — Bazarr Sync (HA)

CURRENT_PHASE: F9
CURRENT_TASK: Aguardando validação HA-LAB pelo usuário (service handlers corrigidos)
STATUS: HA-LAB installation success; services.yaml fixed; service handlers fixed
LAST_VALIDATED: HA-LAB install OK + entities + actions + Bazarr connection; services.yaml single-doc + service handlers bind + 81 testes unitários passando + mypy project-wide clean + Ruff clean + Black clean
BLOCKERS: none
NEXT_ACTION: Usuário atualizar Bazarr Sync no HA-LAB via HACS e reiniciar/recarregar

---

## STATUS

**Fase 9 preparação técnica concluída** — Projeto tecnicamente pronto para instalação no HA-LAB. Repositório GitHub público criado, auto-release removido.

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
- F9: Preparação HACS (manifest, CI, docs, packaging, GitHub repo, auto-release removido) ✅

---

## RESUMO FASE 9 — PREPARAÇÃO HACS

| Item | Status |
|------|--------|
| `manifest.json` | domain `bazarr_sync`, version `0.1.0-beta.1`, codeowners `@phgsbr`, docs próprio |
| `hacs.json` | `homeassistant: "2025.11.0"` |
| `icon.png` | 256x256 RGBA criado |
| `README.md` | Instruções de instalação via HACS Custom Repository (repo real) |
| `CHANGELOG.md` | Atualizado com todas as mudanças F0–F9 |
| `translations/en.json` | Atualizado para `config_entry_id`, `subtitle_id`, `reference_id` |
| CI (GitHub Actions) | pytest, mypy, ruff, black, Hassfest, HACS (auto-release removido) |
| Version | `0.1.0-beta.1` |

---

## ESTADO REAL DO GITHUB

```
GITHUB_REPOSITORY: created (https://github.com/Kraken-Labz/bazarr-sync)
PUBLIC_RELEASE: none
HACS_CUSTOM_REPOSITORY_TEST: ready (repo real disponível)
GITHUB_OWNER: Kraken-Labz
REPOSITORY_NAME: bazarr-sync
GITHUB_URL: https://github.com/Kraken-Labz/bazarr-sync
UPSTREAM: https://github.com/owenvoke/hass-bazarr
ORIGIN: https://github.com/Kraken-Labz/bazarr-sync
```

O repositório público **foi criado** em https://github.com/Kraken-Labz/bazarr-sync

---

## VALIDAÇÕES AUTOMÁTICAS

```
pytest: 81 passed (78 + 3 registration contract)
Black: clean
Ruff: all checks pass
MyPy (--ignore-missing-imports): Success: no issues found in 13 source files
```

## BUG EXTERNAL REFERENCE CORRIGIDO (pré-HA-LAB)

- `util.py`: única implementação canônica de `generate_external_reference_id` (client.py e models.py importam dela)
- `async_get_sync_reference_identifier()` agora retorna o valor REAL enviado ao Bazarr: audio `a:0` -> `a:0`, embedded `s:0` -> `s:0`, external opaque hash -> path real (server-side only)
- WebSocket e Actions usam `resolved_reference` (retorno do resolver) na chamada `async_sync_subtitle(reference=...)`
- Testes: roundtrip external (`/internal/example.en.srt` -> hash -> path real), passthrough audio/embedded, forged ID rejeitado, path nunca exposto publicamente

---

## HA-LAB HACS INSTALL ATTEMPT 1

**result:** failed  
**cause:** invalid `homeassistant` version expression in `hacs.json` (`">=2025.11.0"` not accepted by HACS AwesomeVersion parser)  
**fix:** `homeassistant: ">=2025.11.0"` -> `"2025.11.0"` (commit 5e0eac1)  
**next:** usuário repetir download via HACS no HA-LAB

---

## HA-LAB INSTALLATION ATTEMPT 2

**result:** success  
**config entry:** loaded  
**entities:** created (wanted_movies=17, wanted_episodes=297, health=OK)  
**bazarr connection:** v1.6.0 detected  
**actions registered:** 3 (search_subtitles, download_subtitle, sync_subtitle)  
**services.yaml:** failed on first parse  

**cause:** multi-document YAML with `---` separators  
**fix:** single-document mapping keyed by action names (commit af42d62)  
**tests added:** 5 tests for services.yaml structure (single doc, actions, no separators, fields, opaque ID desc)  
**next:** usuário atualizar via HACS no HA-LAB e reiniciar/recarregar

---

## HA-LAB SEARCH ACTION ATTEMPT 1

**result:** failed  
**cause:** service handlers registered with incompatible `(hass, call)` signature  
**impact:** all three Actions affected (search_subtitles, download_subtitle, sync_subtitle)  
**fix:** bind `hass` using `functools.partial` before `async_register` (commit 66f54ec)  
**tests added:** 3 registration contract tests (call handler with just `call`)  
**type ignores removed:** 3 from async_register calls  
**next:** usuário atualizar via HACS no HA-LAB, reiniciar/recarregar, testar SOMENTE search_subtitles

---

## PRÓXIMO PASSO: VALIDAÇÃO HA-LAB

**Ação requerida pelo usuário (agora via HACS Custom Repository real):**

1. Adicionar este repositório como Custom Repository no HACS (category: Integration)
   - URL: `https://github.com/Kraken-Labz/bazarr-sync`
2. Instalar "Bazarr Sync" via HACS
3. Reiniciar Home Assistant
4. Adicionar integração "Bazarr Sync" via Settings → Devices & Services
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
- Teste de HACS Custom Repository (repositório real disponível)
- Teste de upgrade/reinstall/remoção limpa no HA-LAB
- Teste de múltiplas ConfigEntries simultâneas no HA-LAB

---

## PRÓXIMO: PROJETO B

Após validação HA-LAB verde → Projeto B (Jellyfin Bazarr Sync Plugin - .NET).

---

**F9_PREP_COMPLETE: ready for HA-LAB validation (HACS Custom Repository real)**

**NEXT_HUMAN_CHECKPOINT: HA_LAB_VALIDATION_COMPLETE**