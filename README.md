
# OD-11 loudspeaker component for Home Assistant

A custom component for local control of the OD-11 and OB-4
[wireless speakers from Teenage Engineering][te]
via its WebSocket interface.

[te]: https://teenage.engineering/products/wireless-speakers

## How it works

The OD-11 exposes a WebSocket server on port 8081. This integration
maintains a persistent connection to the speaker, sends commands, and
listens for state updates pushed by the speaker in real time.

On connection, the integration performs the Orthoplay handshake
(`global_join`/`group_join`) to receive the current speaker state,
including volume, input source, and playback status.

The speaker can be discovered automatically on the local network
via mDNS/Zeroconf (`_http._tcp` / `_airplay._tcp`), or
added manually by IP address.

### Features

- Source selection: AirPlay, Spotify Connect, Bluetooth, optical, line-in
- The entity icon changes dynamically to reflect the active input source.
- Playback controls are hidden for optical and line-in sources.
- The seek position updates in real time from the speaker.
- Reconnects automatically when speaker wakes from standby.

### Limitations

- **Turn on** is not supported because the OD-11 can only be woken
  by pressing the function button. The integration reconnects
  automatically once the speaker is reachable.
- **Pause** is equivalent to **stop**
  because there is no separate pause command on the OD-11.
- **Album art** is not provided by the OD-11.
- The **play media** action rely on the `playlist_add_url` command
  which may be deprecated (OD-11 used to support Soundcloud).
  **Queue insertion** (`enqueue: next`) is not supported, and
  the action will return an error.
- Not tested with the **OB-4 speaker**, but expected to work with
  minor alterations of the sources (line-in, bluetooth, radio, disk).

### Media player actions supported

| HA action              |   | OD-11 WebSocket command                            |
|------------------------|---|----------------------------------------------------|
| `turn_on`              |   | Not supported, but will auto-reconnect             |
| `turn_off`             | ✓ | `group_enter_standby`                              |
| `select_source`        | ✓ | `group_set_input_source`                           |
| `volume_up`            | ✓ | `group_change_volume amount:1`                     |
| `volume_down`          | ✓ | `group_change_volume amount:-1`                    |
| `volume_set`           | ✓ | `group_set_volume`                                 |
| `volume_mute`          |   | Considering `group_set_volume vol:0`               |
| `select_sound_mode`    |   | Considering `group_set_eq_{bass,mid,treble}_boost` |
| `media_play`           | ✓ | `playback_start`                                   |
| `media_pause`          | ✓ | `playback_stop` (no separate pause on OD-11)       |
| `media_stop`           | ✓ | `playback_stop`                                    |
| `media_next_track`     | ✓ | `track_skip_to_next`                               |
| `media_previous_track` | ✓ | `track_skip_to_prev`                               |
| `play_media`           | ✓ | `playlist_add_url`                                 |
| `clear_playlist`       | ✓ | `playlist_clear`                                   |
| `shuffle_set`          |   | Not supported                                      |
| `repeat_set`           |   | Not supported                                      |

## Installation and setup

There are 2 different methods of installing the custom component.

### HACS installation

1. Open HACS → Integrations → ⋮ → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **OD-11 wireless loudspeaker**
4. Restart Home Assistant

### Git installation

SSH into your HA instance and clone the repository directly into your
config directory:

```bash
cd /config
git clone https://github.com/vibrog/ha-orthoplay
./ha-orthoplay/scripts/link.sh
ha core restart
```

Or clone the repository on your local machine and use the deploy script
to copy files to your HA instance.

### Setup

Go to **Settings → Devices & Services**. If the speaker is on your
network, it may be discovered automatically and prompt you to
confirm. Otherwise, manually **Add Integration** and search for
**Orthoplay** to enter the IP address of your speaker manually.

Note: `od-11.local` may not resolve on all networks depending on mDNS
support and router configuration. Use Orthoplay or your routers DHCP
list to find the speaker's IP address if needed.

## Disclaimer

This integration was developed by reverse engineering the
[Orthoplay](https://www.orthoplay.com/) web application for the OD-11,
with the assistance of [Claude AI](https://claude.ai/). The WebSocket
interfaces were derived from the Orthoplay JavaScript source, and
implemented on the Home Assistant integration structure, over a few
iterations.
