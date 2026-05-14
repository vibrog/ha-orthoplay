"""Constants for the Orthoplay integration."""

DOMAIN = "orthoplay"

DEFAULT_HOST = "od-11.local"
DEFAULT_PORT = 8081
DEFAULT_NAME = "OD-11"

SOURCE_ICONS: dict[str | None, str] = {
    "Spotify":   "mdi:spotify",
    "Playlist":  "mdi:playlist-music",
    "AirPlay":   "mdi:cast-audio-variant",
    "Bluetooth": "mdi:bluetooth",
    "Optical":   "mdi:toslink",
    "Line in":   "mdi:audio-input-stereo-minijack",
    "Radio":     "mdi:radio",
    "Disk":      "mdi:waveform",
    None:        "mdi:speaker",
}
