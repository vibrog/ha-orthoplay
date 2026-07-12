
## "the latest technology at heart."

The wireless OD-11 was released in 2014, and is a reengineered version
of the legendary ortho directional loudspeaker by [Stig Carlsson][] from
1974.

In this text I will explore the technical specifications of the
speaker and explain why I think there is an untapped potential,
as Teenage Engineering is not actively maintaining or improving
the firmware.

Details compared against a representative modern competitor:

| OD-11 | Spec | [KEF LS50][] |
|---|---|---|
| 100 W, 28–20k Hz (-3dB) | Audio | 280 W, 40-28k Hz (±3dB) |
| 262,262,272 mm | Dimensions | 305,200,311 mm (hwd) |
| $1,998 (2 pcs) | Price | $2,999.99 (/set) |
| 2014 | Launch | 2020 |
| 802.11 a/b/g/n, IPv4 | Network | 802.11 a/b/g/n/ac, RJ45 ethernet, IPv4, IPv6 |
| TOSLINK, analog 3.5mm | Inputs | TOSLINK, analog 3.5mm, HDMI eARC |
| AirPlay 2, Bluetooth 4 LE | Streaming | AirPlay 2, Google Cast, Bluetooth 5.0, Roon, UPnP |
| Spotify, WebSocket API | Services | Spotify, Tidal, Amazon Music, Qobuz, Deezer, Internet radio, REST API |
| MP3, AAC, FLAC, Ogg Vorbis, ALAC, LPCM | Formats | MP3, AAC/M4A, FLAC, Ogg Vorbis, WMA, ALAC, MQA, WAV, AIFF, DSD, LPCM |
| 16-bit/44.1 kHz | DAC | 24-bit/384 kHz |

Compared to newer speakers, the OD-11 appears outdated, and it lacks
capabilities that should be considered a bare minimum for a premium
speaker in this price range and targeted high-end customer group, such
as playback of AAC or FLAC from HTTPS, or segmented streaming.

[Stig Carlsson]: https://carlssonplanet.com/en/speakers/produced/sonab-od-11/
[KEF LS50]: https://kef.com/products/ls50-wireless-2


### The wishlist

By combining audio protocols and formats the OD-11 is already capable
of encoding, and utilizing its existing software stack properly, these
seem fairly straightforward to add:

- HTTPS, including http/2 and HSTS,
  e.g. modern web server configurations
- AAC is already supported for Bluetooth
- FLAC is already supported for Spotify -- also
  used by Tidal, Qobuz, Bandcamp, Deezer, Amazon Music
- Remove the strict URL filtering
  requiring the URL to match `http://*.mp3`

Next, the OD-11 should offer direct play of lossless audio,
and modern chunked streaming protocols:

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
  : Spotify, Tidal, Qobuz, Bandcamp, Deezer, SoundCloud, Navidrome, Plex
- **Control** layer
  : Spotify Connect, Google Cast, AirPlay 2, DLNA/UPnP AV
- **Transport** protocol (delivery method)
  : HLS, DASH, progressive and continuous HTTP streaming, ICY-metadata, RTP
- **Container** format (packaging)
  : M4A (MP4), Ogg, MPEG-TS, WebM, WAV, AIFF
- **Codec** (audio quality)
  : AAC, MP3, Vorbis, Opus, FLAC, ALAC, AC-3, DTS
- **Raw** (uncompressed) representation
  : LPCM (linear PCM), DSD
- Acoustic **output** stage
  : DSP → DAC → class-D amplifier → speaker driver

Using this layer architecture model, let's look into which
technologies that are implemented in the OD-11:

![OD-11 audio protocol layers](assets/audio_protocol_layers.svg)

<!--
            Spotify           SoundCloud*   AirPlay   Bluetooth
            ---------------   -----------   -------   ---------
  Control   Spotify Connect   WebSocket     RTSP      AVRCP*
Transport   HTTPS             HTTP          RTP       AVDTP
Container   Ogg
    Codec   Vorbis, FLAC      MP3           ALAC      AAC
-->

Remarks:
- Spotify streams audio over HTTPS. The OD-11 uses Ogg Vorbis and FLAC
  for Spotify Connect playback, and the Spotify app shows lossless
  16-bit/44.1 kHz FLAC as the highest quality the OD-11 can play.
  Whether adaptive delivery mechanisms such as HLS and DASH are used
  is not publicly documented.
- SoundCloud is no longer officially supported by the OD-11,
  and the integration stopped working either due to HTTPS or
  when the service switched to AAC-based HLS in 2025.
- Bluetooth [AVRCP][] playback control is not supported.

We can view these playback capabilities organized by
audio payload/codec and transport/link/session layer
to show that it would be basic to combine
these to offer the basics above:

![OD-11 audio capabilities](assets/audio_capabilities.svg)

<!--
          AAC        MP3         Vorbis   FLAC     ALAC     LPCM
          ---------  ----------  -------  -------  -------  -------
   A2DP   Bluetooth
   HTTP              SoundCloud
  HTTPS   +          +           Spotify  Spotify  +        +
    RTP                                            AirPlay
 S/PDIF                                                     Optical
    HLS   +
-->

As you can see, it should be merely about connecting what is already there.

Direct cloud playback will reject URLs not matching `http://*.mp3`.
Many streaming sources would become available by simply removing this
limitation, and a proxy server rewriting URLs can be used as a
workaround for playing MP3 files and continuous MP3 streams.
Support for additional formats such as AAC/M4A, Ogg Vorbis, and FLAC
is already there, or it could likely be added via an open source
decoder library such as libav/[FFmpeg][], including Opus.

[AVRCP]: https://www.bluetooth.com/specifications/
[FFmpeg]: https://ffmpeg.org/


### Signs of neglect

HTTPS and IPv6 are prerequisites today.
The OD-11 network client is based on [libcurl][], which supports HTTPS.
It is simply a matter of enabling it.
Note that the libcurl software version is unknown: The speaker
identifies itself with `'User-Agent': 'libcurl-agent/1.0'` which is
the default user-agent string libcurl uses when the developer omits
`CURLOPT_USERAGENT`.

To further illustrate how little effort Teenage Engineering seems to
put into keeping the firmware up-to-date, the OD-11 web interface runs on
[nginx][] 1.4.4 which was released 24 April 2013,
and the WebSocket server runs
[AutobahnPython][] 0.5.14 (released 25 February 2013),
meaning no library patches or security fixes have been applied.

Has the OD-11 effectively been abandoned?

[libcurl]: https://curl.se/
[nginx]: https://nginx.org/
[AutobahnPython]: https://github.com/crossbario/autobahn-python


### Connected, then abandoned

Unlike analog speakers, which can be perceived as improving in tone as
mechanical components settle, connected devices such as the OD-11 have
a functional expiry date.

The Spotify Connect feature uses a persistent outbound, encrypted
connection to cloud services (likely WebSocket, HTTP/2, or similar)
to deliver remote control commands.
Devices that rely on persistent cloud-connected control layers
remain exposed to security vulnerabilities.

The EU's [Cyber Resilience Act][] (2024) requires manufacturers of
products with digital elements to indicate the product's support
period and maintain security support during that period.

[Cyber Resilience Act]: https://www.cyberresilienceact.eu/
