# PROJECT.md — Bazarr Sync (HA)

## 1. Visão Geral

Integração Home Assistant para Bazarr que expõe capacidade de busca, download e sincronização de legendas via Actions e WebSocket API.

## 2. Upstream

| Item | Valor |
|------|-------|
| Repositório | https://github.com/owenvoke/hass-bazarr |
| Commit base | `65c27a3` (main, 2025-12-01) |
| Licença | MIT |
| **Domain** | **`bazarr_sync`** |
| HA mínimo | 2025.11.0 |

## 3. Arquitetura Existente (preservada)

```
Config Flow (URL + API key)
    ↓
BazarrDataUpdateCoordinator (5 min polling)
    ↓ GET /api/badges, /api/system/health, /api/system/status
Sensores: wanted_movies, wanted_episodes, health_issues
```

- 3 entidades (2 sensors + 1 binary sensor)
- Config flow com reauth
- runtime_data pattern
- HACS compatível

## 4. O que foi acrescentado

### BazarrClient (`client.py`)
Classe separada para toda comunicação HTTP com Bazarr.

Métodos:
- `async_get_status()` — /api/system/status
- `async_get_badges()` — /api/badges
- `async_get_health()` — /api/system/health
- `async_get_movies(start, length)` — /api/movies
- `async_get_episodes(series_id, episode_id)` — /api/episodes
- `async_get_series(start, length)` — /api/series
- `async_search_movie_subtitles(radarr_id)` — GET /api/providers/movies
- `async_search_episode_subtitles(episode_id)` — GET /api/providers/episodes
- `async_download_movie_subtitle(...)` — POST /api/providers/movies (form-encoded)
- `async_download_episode_subtitle(...)` — POST /api/providers/episodes (form-encoded)
- `async_get_sync_references(subtitles_path, ...)` — GET /api/subtitles (camelCase params)
- `async_sync_subtitle(...)` — PATCH /api/subtitles (form-encoded)
- **`async_get_installed_subtitle_path(media_type, media_id, subtitle_id, series_id?)`** — resolve path server-side
- **`async_get_sync_reference_identifier(media_type, media_id, reference_id, series_id?)`** — valida reference_id

Tratamento de erros: 401 → BazarrAuthError, 404 → BazarrNotFoundError, timeout → BazarrTimeoutError, outros → BazarrError.

### Models (`models.py`)
Dataclasses: `MediaReference`, `SubtitleCandidate`, `InstalledSubtitle`, `SyncReference`.

### HA Actions (`services.py` + `services.yaml`)
- `bazarr_sync.search_subtitles` — busca candidatos (com response data, `SupportsResponse.ONLY`)
- `bazarr_sync.download_subtitle` — baixa legenda específica
- `bazarr_sync.sync_subtitle` — sincroniza legenda (usa `subtitle_id` + `reference_id`)

### WebSocket API (`websocket.py`)
Comandos para frontends (namespace `bazarr_sync/`):
- `bazarr_sync/get_media` — listar filmes/episódios
- `bazarr_sync/get_subtitles` — legendas instaladas
- `bazarr_sync/search_subtitles` — buscar candidatos
- `bazarr_sync/download_subtitle` — baixar candidato
- `bazarr_sync/get_sync_references` — referências de sync (usa `subtitle_id`)
- `bazarr_sync/sync_subtitle` — executar sync (usa `subtitle_id` + `reference_id`)

### Entity base (`entity.py`)
DRY do `device_info` entre sensor.py e binary_sensor.py.

## 5. Bugs do upstream corrigidos

1. `config_flow.py`: `isinstance(err, aiohttp.ClientResponseError and err.status == 401)` → corrigido para verificar status separadamente
2. `coordinator.py`: removida dependência `httpcore.TimeoutException` (não é padrão do HA)
3. `coordinator.py`: 401 durante polling agora levanta `ConfigEntryAuthFailed`
4. `/api/system/status` não é mais chamado 2x desnecessariamente

## 6. Endpoints Bazarr confirmados

### Autenticação
Header: `X-API-KEY: <key>`

### Listagem de mídia
| Endpoint | Método | Params chave |
|----------|--------|-------------|
| `/api/movies` | GET | `start`, `length`, `radarrid[]` |
| `/api/episodes` | GET | `seriesid[]` ou `episodeid[]` (obrigatório) |
| `/api/series` | GET | `start`, `length`, `seriesid[]` |

### Busca e download
| Endpoint | Método | Params (form-encoded) |
|----------|--------|----------------------|
| `/api/providers/movies` | GET | `radarrid` |
| `/api/providers/movies` | POST | `radarrid`, `provider`, `subtitle`, `hi`, `forced`, `original_format` |
| `/api/providers/episodes` | GET | `episodeid` |
| `/api/providers/episodes` | POST | `seriesid`, `episodeid`, `provider`, `subtitle`, `hi`, `forced`, `original_format` |

### Sync
| Endpoint | Método | Params |
|----------|--------|--------|
| `/api/subtitles` | GET | `subtitlesPath`, `sonarrEpisodeId` ou `radarrMovieId` (camelCase) |
| `/api/subtitles` | PATCH | `action=sync`, `language`, `path`, `type`, `id`, `forced`, `hi`, `original_format`, `reference`, `max_offset_seconds`, `no_fix_framerate`, `gss` |

### Convenções importantes
- POST/PATCH são **form-encoded** (não JSON)
- Booleanos são strings `"True"` / `"False"` (capital T)
- `/api/subtitles` GET usa **camelCase**: `subtitlesPath`, `sonarrEpisodeId`, `radarrMovieId`
- Demais endpoints usam **lowercase sem underscore**: `radarrid`, `episodeid`, `seriesid`
- `PATCH /api/subtitles`: `type`+`id` discriminam movie (`type=movie`, `id=radarrId`) vs episode (`type=episode`, `id=sonarrEpisodeId`)
- Download é assíncrono (204 imediato, job em background)

## 7. Estrutura de arquivos

```
custom_components/bazarr_sync/
├── __init__.py          # setup entry, registra actions + WS
├── manifest.json
├── const.py             # DOMAIN = "bazarr_sync" + constantes
├── config_flow.py       # URL + API key (fix bugs)
├── coordinator.py       # polling (delegado ao client)
├── sensor.py            # sensores existentes
├── binary_sensor.py     # binary sensor existente
├── entity.py            # base entity (DRY)
├── client.py            # BazarrClient (toda HTTP)
├── models.py            # dataclasses de domínio
├── services.py          # HA actions
├── services.yaml        # schemas das actions
├── websocket.py         # WS API para frontends
├── types.py             # BazarrSyncConfigEntry
└── translations/en.json
tests/
├── conftest.py
├── test_client.py
├── test_models.py
├── test_services.py
└── test_websocket.py
```

## 8. Projeto B — Jellyfin Bazarr Sync (planejado)

Repo separado, criado após aprovação do Projeto A.

Arquitetura:
```
Jellyfin Web → botão "Sincronizar legenda" → Jellyfin Bazarr Sync Plugin → Bazarr API
```

V1:
- Botão na página de detalhes de Movie/Episode (antes do playback)
- Apenas SYNC de legenda existente (não busca/download)
- JS Injector para inserir botão na UI web
- Backend .NET baseado no template oficial Jellyfin
- Solicitar refresh do item Jellyfin após sync
- Não mexer no OSD
- Não alterar Kraken/produção sem autorização

Depois da V1 pode acrescentar "Procurar outra legenda no Bazarr".
