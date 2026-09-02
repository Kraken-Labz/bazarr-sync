"""Constants for the Bazarr Sync integration."""

from __future__ import annotations

DOMAIN = "bazarr_sync"

# API endpoints
API_BADGES = "/api/badges"
API_SYSTEM_HEALTH = "/api/system/health"
API_SYSTEM_STATUS = "/api/system/status"
API_MOVIES = "/api/movies"
API_EPISODES = "/api/episodes"
API_SERIES = "/api/series"
API_PROVIDERS_MOVIES = "/api/providers/movies"
API_PROVIDERS_EPISODES = "/api/providers/episodes"
API_SUBTITLES = "/api/subtitles"

# API endpoints
API_TASKS = "/api/tasks"
API_SYSTEM_TASKS = "/api/system/tasks"

# WebSocket commands
WS_TYPE_GET_MEDIA = "bazarr_sync/get_media"
WS_TYPE_GET_SUBTITLES = "bazarr_sync/get_subtitles"
WS_TYPE_SEARCH_SUBTITLES = "bazarr_sync/search_subtitles"
WS_TYPE_DOWNLOAD_SUBTITLE = "bazarr_sync/download_subtitle"
WS_TYPE_GET_SYNC_REFERENCES = "bazarr_sync/get_sync_references"
WS_TYPE_SYNC_SUBTITLE = "bazarr_sync/sync_subtitle"

# Action names
ACTION_SEARCH_SUBTITLES = "search_subtitles"
ACTION_DOWNLOAD_SUBTITLE = "download_subtitle"
ACTION_SYNC_SUBTITLE = "sync_subtitle"

# Human-friendly action names
ACTION_FIND_SUBTITLES = "find_subtitles"
ACTION_DOWNLOAD_BEST_SUBTITLE = "download_best_subtitle"
ACTION_SYNC_SUBTITLE_AUTO = "sync_subtitle_auto"

# Library-wide bulk actions
ACTION_SEARCH_ALL_MISSING = "search_all_missing_subtitles"
ACTION_SYNC_ALL_SUBTITLES = "sync_all_subtitles"
ACTION_GET_BULK_SYNC_STATUS = "get_bulk_sync_status"

# Native Bazarr task IDs (audited against Bazarr 2025.x UI/System Tasks)
TASK_WANTED_MOVIES = "wanted_search_missing_subtitles_movies"
TASK_WANTED_SERIES = "wanted_search_missing_subtitles_series"
