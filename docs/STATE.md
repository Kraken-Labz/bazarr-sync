# STATE.md — Bazarr Sync (HA)

CURRENT_PHASE: F9
CURRENT_TASK: Aguardando validação HA-LAB pelo usuário (search action passou; normalização original_format/url)
STATUS: HA-LAB search_subtitles passed; original_format boolean + url optional normalized
LAST_VALIDATED: HA-LAB search OK (2 pt-BR candidates); original_format bool + url optional; 83 testes + mypy + ruff + black
BLOCKERS: none
NEXT_ACTION: Usuário atualizar Bazarr Sync no HA-LAB via HACS e testar download/sync

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
pytest: 83 passed (81 + 2 original_format/url normalization)
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

## HA-LAB SEARCH ACTION ATTEMPT 2

**result:** passed  
**action:** `bazarr_sync.search_subtitles`  
**params:** media_type=movie, media_id=244  
**response:** 2 candidates pt-BR (opensubtitlescom, scores 91/74)  
**validation:** Action registered, config_entry_id works, handler works, HA→Bazarr comms works, response data works

---

## NORMALIZAÇÃO original_format/url

**result:** fixed  
**issue:** Bazarr returns `original_format: "False"` (string), public API should return boolean  
**fix:** `_normalize_bool()` + `_normalize_optional_str()` in models.py  
**contract:** `original_format: bool`, `url: str | None`  
**tests:** 4 new cases (True/False/string/None normalization)  
**tests total:** 83 passed

---

## PRÓXIMO PASSO: VALIDAÇÃO HA-LAB (F9 — NON-MUTATING)

**Ação requerida (autônoma + usuário):**

1. Atualizar "Bazarr Sync" via HACS no HA-LAB → commit 23a751c
2. Reiniciar/recarregar Home Assistant (reload + restart completo)
3. Validar **apenas operações read-only**:

| Check | Descrição |
|-------|-----------|
| Config Flow | Abre normalmente, aceita URL/API key, cria ConfigEntry LOADED |
| Reload ConfigEntry | Persiste e carrega corretamente |
| Restart HA-LAB | Integração carrega sem erros |
| Entities | Sensors (wanted_movies, wanted_episodes) + binary_sensor (health) + availability |
| Action search_subtitles | Retorna `original_format: bool`, `url: string | null` |
| WebSocket read-only | 4 comandos: `get_media`, `get_subtitles`, `search_subtitles`, `get_sync_references` |
| Multi ConfigEntry | Schemas validados (testes automatizados); segunda instância se disponível |
| Path Security | Respostas públicas não expõem `path`; usam `subtitle_id`/`reference_id` opacos |
| Secrets | API key não aparece em logs/responses; `X-API-KEY` só no backend |
| Logs | Sem tracebacks, sem warnings recorrentes, sem segredos |
| Schemas mutáveis | `download_subtitle`, `sync_subtitle` validados via registro de contrato (testes) — **sem execução** |

**Permitido:** leitura, busca, reload, restart, validação de schemas read-only  
**Proibido:** download/sync/delete/modificação em mídia de produção (F6/F7 já validaram)

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