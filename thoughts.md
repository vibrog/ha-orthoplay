
## "the latest technology at heart."

The wireless OD-11 was released in 2014, and is a reengineered version
of the legendary ortho directional loudspeaker by Stig Carlsson from
1974.

In this text I will explore the technical specifications of the
speaker and explain why I think there is an untapped potential,
as Teenage Engineering is not actively maintaining or improving
the firmware.

Details compared against a representative modern competitor:

| OD-11 | Spec | KEF LS-50 / LSX |
|---|---|---|
| 100 W, 28–20k Hz (-3dB) | Audio specifications | 100 W, 40-28k Hz (±3dB) |
| 262,262,272 mm (hwd) | Dimensions | 305,200,311 mm |
| $1,998 (2 pcs) | Price | $2,999.99 / $1,499.99 (/set) |
| 2014 | Launch year | 2020 / 2022 |
| 802.11 a/b/g/n, IPv4 | Wireless | 802.11 a/b/g/n/ac, RJ45 ethernet, IPv4, IPv6 |
| TOSLINK, analog 3.5mm | Inputs | TOSLINK, analog 3.5mm, HDMI eARC |
| AirPlay 2, Bluetooth 4 LE | Stream inputs | AirPlay 2, Google Cast, Bluetooth 5.0, Roon, DNLA/UPnP |
| Spotify, mDNS, WebSocket API | Control layer | Spotify, Tidal, Amazon Music, Qobuz, Deezer, Internet radio, mDNS, SSDP/UPnP, REST API |
| MP3, AAC, Ogg Vorbis, ALAC, LPCM | Audio formats | MP3, AAC, FLAC, Ogg Vorbis, WMA, ALAC, MQA, DSD, M4A, WAV, AIFF, LPCM |

Compared to newer speakers, the OD-11 appears outdated, and it lacks
capabilities that should be considered a bare minimum for a premium
speaker in this price range and targeted high-end customer group, such
as playback of AAC or FLAC from HTTPS, or segmented streaming.

By combining audio protocols and formats the OD-11 is already capable
of encoding, and utilizing its existing software stack properly, these
seem fairly straightforward to add.


### The wishlist

- HTTPS, including http/2 and HSTS,
  e.g. modern web server configurations
- AAC (.m4a) over HTTPS: AAC is already supported
  for Bluetooth, and maybe Spotify Connect
- Remove the strict URL filtering
  requiring the URL to match `http://*.mp3`

Next, the OD-11 should offer direct play of lossless audio,
and modern chunked streaming protocols:

- FLAC over HTTPS -- used by Tidal, Qobuz, Bandcamp, Deezer, Amazon Music
- AAC over HLS (.m3u8) is the de-facto streaming (used by SoundCloud)
- Progressive HTTP streaming (Range header in GET request)
- aptX (used by Android devices) for high-quality Bluetooth playback
  from other than Apple devices
- Adding tracks from playlists (.m3u)

To my understanding, most of this would be drop-in functionality.
We'll get back to that after a brief overview of audio streaming.


### Audio streaming capabilities

The above technical specifications lists a lot of audio formats,
streaming standards and services. They are related in layers:

- **Music catalogs**
  : Spotify, Tidal, Qobuz, Navidrome, Plex, InTune
- **Control layer**
  : Spotify Connect, Google Cast, AirPlay 2, DLNA/UPnP AV, Subsonic
- **Transport** protocol (delivery method)
  : HLS, DASH, progressive and continuous HTTP streaming, ICY-metadata, RTP
- **Container** format (packaging)
  : M4A, Ogg, WAV, AIFF, MPEG-TS, WebM
- **Codec** (audio quality)
  : AAC, MP3, FLAC, Vorbis, Opus, ALAC
- **Raw** (uncompressed) representation
  : LPCM (linear PCM), AC-3 (Dolby Digital), DTS
- Acoustic **output** stage
  : DSP → DAC → class-D amplifier → speaker driver

Using this layer architecture model, let's look into which
technologies that are implemented in the OD-11:

![OD-11 audio protocol layers](assets/audio_protocol_layers.svg)

Or we can view these playback capabilities organized by
audio payload/codec and transport/link/session layer
to show that it would be basic to combine
these to offer the basics above:

*) SoundCloud is no longer officially supported by Teenage Engineering,
   and the integration stopped working either due to HTTPS or
   when the service switched to AAC-based HLS in 2025.

![OD-11 audio capabilities](assets/audio_capabilities.svg)

As you can see, it should be merely about connecting what is already there.


### Signs of neglect

HTTPS and IPv6 are prerequisites today.

The OD-11 network client is based on libcurl, which supports HTTPS.
It is simply a matter of enabling it, and not reject adding URLs not
matching `http://*.mp3`. A proxy server rewriting URLs can be used as
a workaround for playing MP3 files and continuous MP3 streams.

To further illustrate how little effort Teenage Engineering seems to
put into keeping the firmware up-to-date, the OD-11 identifies itself
with `'User-Agent': 'libcurl-agent/1.0'` which is the default
user-agent string libcurl uses when the developer omits
`CURLOPT_USERAGENT`.

The speaker web interface runs on
nginx 1.4.4 which was released 24 April 2013,
and the WebSocket server runs
AutobahnPython 0.5.14 (released 25 February 2013),
meaning no library patches or security fixes have been applied.

Maybe the OD-11 is simply an abandoned product?
