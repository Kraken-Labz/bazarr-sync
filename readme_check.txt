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
| API Key | Found in Bazarr → Settings → General → A