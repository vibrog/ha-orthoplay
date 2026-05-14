"""Constants for the Orthoplay integration."""

DOMAIN = "orthoplay"

DEFAULT_HOST = "od-11.local"
DEFAULT_PORT = 8081
DEFAULT_NAME = "OD-11"

SOURCE_ICONS: dict[str | None, str] = {
    None:        "mdi:speaker",
    "AirPlay":   "mdi:cast-audio-variant",
    "Spotify":   "mdi:spotify",
    "Playlist":  "mdi:playlist-music",
    "Line in":   "mdi:audio-input-stereo-minijack",
    "Optical":   "mdi:toslink",
    "Bluetooth": "mdi:bluetooth",
    "Radio":     "mdi:radio",
    "Disk":      "mdi:waveform",
}
