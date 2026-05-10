"""Constants for the Orthoplay integration."""

DOMAIN = "orthoplay"

DEFAULT_HOST = "od-11.local"
DEFAULT_PORT = 8081
DEFAULT_NAME = "OD-11"

# OD-11 input sources (confirmed from JS app source)
SOURCES = {
    0: "AirPlay",
    1: "Cloud / Spotify",
    5: "Bluetooth",
    4: "Optical",
    3: "Line In",
}
SOURCE_ICONS = {
    0: "mdi:cast-audio-variant",
    1: "mdi:spotify",
    5: "mdi:bluetooth",
    4: "mdi:toslink",
    3: "mdi:audio-input-stereo-minijack",
}
SOURCE_NAME_TO_ID = {name: src_id for src_id, name in SOURCES.items()}

# Volume range on the OD-11
VOLUME_MIN = 0
VOLUME_MAX = 100

# Zeroconf service type the OD-11 advertises
ZEROCONF_TYPE = "_airplay._tcp.local."
