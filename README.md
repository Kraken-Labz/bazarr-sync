# Bazarr Sync — Home Assistant Integration

Custom Home Assistant integration for [Bazarr](https://www.bazarr.media/) that provides secure subtitle search, download, and synchronization via HA Actions and WebSocket API.

## Features

- **Sensors**: Wanted movies, wanted episodes, health issues (from upstream)
- **Actions**: Search subtitles, download a specific subtitle, sync subtitles
- **WebSocket API**: Secure interface for custom frontend cards (e.g. Octopus Media Card)
- **Security**: API key never exposed to frontend; filesystem paths resolved server-side

## Installation (HACS)

### As Custom Repository (Pre-Release)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** (three dots) → **Custom repositories**
3. Add repository URL: `https://github.com/Kraken-Labz/bazarr-sync`
4. Category: **Integration**
5. Click **Add**
6. Search for **Bazarr Sync** in HACS and install
7. Restart Home Assistant
7. Add the integration via **Settings → Devices & Services → Add Integration → Bazarr Sync**
8. Provide your Bazarr URL and API key

### Manual Installation

1. Copy `custom_components/bazarr_sync` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → Add Integration → Bazarr Sync**

## Configuration

| Field | Description |
|-------|-------------|
| URL   | Base URL of your Bazarr instance (e.g. `http://localhost:6767`) |
| API Key | Found in Bazarr → Settings → General → Authentication |

The integration creates a **Config Entry** that is used to identify which Bazarr instance to use when multiple are configured.

## Actions

All actions require `config_entry_id` to identify the target Bazarr instance.

### `bazarr_sync.search_subtitles`

Search for available subtitles for a movie or episode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config_entry_id` | string | Yes | Config Entry ID of the Bazarr Sync instance |
| `media_type` | `movie` \| `episode` | Yes | Media type |
| `media_id` | integer | Yes | `radarrId` for movies, `sonarrEpisodeId` for episodes |
| `series_id` | integer | No | `sonarrSeriesId` (required for episodes) |

**Response**: `{"candidates": [...]}` — list of subtitle candidates with provider, subtitle_id, language, score, matches, etc.

### `bazarr_sync.download_subtitle`

Download a specific subtitle found in a previous search.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config_entry_id` | string | Yes | Config Entry ID of the Bazarr Sync instance |
| `media_type` | `movie` \| `episode` | Yes | Media type |
| `media_id` | integer | Yes | `radarrId` or `sonarrEpisodeId` |
| `series_id` | integer | No | `sonarrSeriesId` (required for episodes) |
| `provider` | string | Yes | Provider name from search result |
| `subtitle` | string | Yes | Subtitle ID from search result |
| `language` | string | Yes | Language code2 (e.g. `en`, `pt`) |
| `hearing_impaired` | boolean | No | Default: false |
| `forced` | boolean | No | Default: false |
| `original_format` | boolean | No | Default: false |

### `bazarr_sync.sync_subtitle`

Synchronize an existing installed subtitle against a reference track.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config_entry_id` | string | Yes | Config Entry ID of the Bazarr Sync instance |
| `media_type` | `movie` \| `episode` | Yes | Media type |
| `media_id` | integer | Yes | `radarrId` or `sonarrEpisodeId` |
| `subtitle_id` | string | Yes | Opaque subtitle identifier (from `get_subtitles` WebSocket) |
| `reference_id` | string | No | Sync reference stream identifier (e.g. `a:0`, `s:0`) from `get_sync_references` |
| `hearing_impaired` | boolean | No | Default: false |
| `forced` | boolean | No | Default: false |
| `original_format` | boolean | No | Default: false |
| `max_offset_seconds` | integer | No | Maximum offset allowed |
| `no_fix_framerate` | boolean | No | Default: false |
| `gss` | boolean | No | Default: false |
| `series_id` | integer | No | `sonarrSeriesId` (required for episodes) |

**Important**: The frontend does not provide filesystem paths. The backend resolves opaque `subtitle_id` and validates opaque `reference_id` against installed subtitles and sync references.

## WebSocket API

All commands use the `bazarr_sync/` namespace and require `config_entry_id`.

### `bazarr_sync/get_media`

Get list of movies, episodes, or series.

```json
{
  "type": "bazarr_sync/get_media",
  "config_entry_id": "<entry_id>",
  "media_type": "movies|episodes|series",
  "series_id": 123
}
```

### `bazarr_sync/get_subtitles`

Get installed subtitles for a media item.

```json
{
  "type": "bazarr_sync/get_subtitles",
  "config_entry_id": "<entry_id>",
  "media_type": "movie|episode",
  "media_id": 123,
  "series_id": 456
}
```

### `bazarr_sync/search_subtitles`

Search for subtitle candidates.

```json
{
  "type": "bazarr_sync/search_subtitles",
  "config_entry_id": "<entry_id>",
  "media_type": "movie|episode",
  "media_id": 123,
  "series_id": 456
}
```

### `bazarr_sync/download_subtitle`

Download a specific subtitle.

```json
{
  "type": "bazarr_sync/download_subtitle",
  "config_entry_id": "<entry_id>",
  "media_type": "movie|episode",
  "media_id": 123,
  "series_id": 456,
  "provider": "opensubtitlescom",
  "subtitle": "subtitle-id-from-search",
  "language": "en",
  "hearing_impaired": false,
  "forced": false,
  "original_format": false
}
```

### `bazarr_sync/get_sync_references`

Get sync references (audio tracks, embedded subtitles) for an installed subtitle.

```json
{
  "type": "bazarr_sync/get_sync_references",
  "config_entry_id": "<entry_id>",
  "media_type": "movie|episode",
  "media_id": 123,
  "subtitle_id": "abc123def4567890",
  "series_id": 456
}
```

### `bazarr_sync/sync_subtitle`

Synchronize a subtitle against a reference track.

```json
{
  "type": "bazarr_sync/sync_subtitle",
  "config_entry_id": "<entry_id>",
  "media_type": "movie|episode",
  "media_id": 123,
  "subtitle_id": "abc123def4567890",
  "reference_id": "a:0",
  "hearing_impaired": false,
  "forced": false,
  "original_format": false,
  "max_offset_seconds": 30,
  "no_fix_framerate": false,
  "gss": false,
  "series_id": 456
}
```

## Security

- **API Key**: Never exposed to frontend; only used server-side
- **Filesystem Paths**: Never accepted from frontend; resolved server-side via `subtitle_id` and validated `reference_id`
- **Config Entry Isolation**: Each action/WS command targets a specific Config Entry via `config_entry_id`

## Development

### Requirements

- Python 3.12+
- Home Assistant 2025.11+

### Running Tests

```bash
# Install dependencies
pip install -r requirements-test.txt

# Run tests
pytest tests/ -v

# Linting
ruff check custom_components/bazarr_sync/
mypy custom_components/bazarr_sync/ --ignore-missing-imports
black --check .
```

## License

MIT License — see [LICENSE](LICENSE)

## Origins & Credits

This project was originally based on [owenvoke/hass-bazarr](https://github.com/owenvoke/hass-bazarr) (commit 65c27a3, MIT License) by Owen Voke.

**Bazarr Sync** is now maintained independently and is not affiliated with or endorsed by the original author or the Bazarr project.

**Development Transparency**: Bazarr Sync is a personal project developed with extensive assistance from AI coding tools (AI-assisted software development). The source code, tests, and development documentation are available for inspection.

## Disclaimer

This project is provided as-is, without commercial support or guarantees. Use at your own risk.