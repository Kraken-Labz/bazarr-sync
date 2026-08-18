# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- BazarrClient: classe separada para toda comunicação HTTP com Bazarr
- Models: `MediaReference`, `SubtitleCandidate`, `InstalledSubtitle`, `SyncReference`
- HA Actions: `bazarr.search_subtitles`, `bazarr.download_subtitle`, `bazarr.sync_subtitle`
- WebSocket API: comandos seguros para frontends (sem expor API key)
- Entity base: DRY do `device_info` entre plataformas
- Testes unitários com mock de rede
- **FASE 8 - Hardening**:
  - Concurrency control: semaphore no BazarrClient (padrão 5 requests simultâneos)
  - Retry com backoff exponencial para operações idempotentes (GET/HEAD/OPTIONS)
  - Logging estruturado com correlation IDs para rastreamento de requisições
  - Cobertura de testes expandida: retry 5xx, timeout, network error, max retries
  - Type hints estritos (mypy --strict)
  - Ruff configurado (lint + formatação)
- **Domain Migration**: `bazarr` → `bazarr_sync`
  - Novo domínio: `bazarr_sync`
  - Actions: `bazarr_sync.*`
  - WebSocket: `bazarr_sync/*`
  - ConfigEntry type: `BazarrSyncConfigEntry`
- **Config Entry API Migration**: `config_entry` → `config_entry_id`
  - Services: `config_entry_id` obrigatório em todos os schemas
  - WebSocket: `config_entry_id` obrigatório em todos os comandos
  - `services.yaml`: `config_entry_id` em todos os campos
- **Path Security Overhaul**:
  - Frontend não envia mais filesystem paths
  - `subtitle_id` (installed subtitle path) → resolvido server-side
  - `reference_id` (stream identifier) → validado contra sync references
  - Novos métodos: `async_get_installed_subtitle_path()`, `async_get_sync_reference_identifier()`
  - Testes negativos: path arbitrário, forged IDs, cross-media IDs rejeitados
- **Action Response**: `search_subtitles` usa `SupportsResponse.ONLY`

### Fixed
- `config_flow.py`: corrigido bug `isinstance` que impedia detectar 401 corretamente
- `coordinator.py`: removida dependência `httpcore.TimeoutException` (não padrão do HA)
- `coordinator.py`: 401 durante polling agora levanta `ConfigEntryAuthFailed`
- `coordinator.py`: `/api/system/status` não é mais chamado 2x desnecessariamente
- `services.py`: import `DOMAIN` adicionado, variáveis não utilizadas removidas
- `websocket.py`: imports não utilizados removidos, variáveis não utilizadas removidas
- `client.py`: type hints corrigidos para params dict
- `translations/en.json`: atualizado para `config_entry_id`, `subtitle_id`, `reference_id`

### Based on
- Upstream: owenvoke/hass-bazarr @ 65c27a3 (v1.2.3, MIT License)