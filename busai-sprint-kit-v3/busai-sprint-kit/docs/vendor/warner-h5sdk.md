# Warner H5 SDK v1 — what Claude Code needs to know

Source: `WARNER_H5SDK_V1.zip` from the camera vendor (12 Oct 2026). Docs inside: `doc/H5SDK_en.md`, `doc/DevceSetting.md`. Facts below are read from those docs and the shipped JavaScript; anything marked **measure** must be confirmed by S1-05 on pilot cameras.

## Where the SDK lives

- Never commit the SDK. `connector.js` contains an embedded vendor access token and app key. Keep the zip in `vendor/warner_h5sdk/` (git-ignored) on dev machines and in the private staging bucket for CI, pinned by SHA-256 in `vendor/warner_h5sdk.sha256`.
- Never read, copy, log or use the token or app key embedded in the SDK. Our bridge authenticates with the pilot account from environment variables (H-02).

## What it is

- A **browser** library (JavaScript + WebAssembly). `connector.js` uses `window`, `document`, `localStorage`, `Worker`, `WebAssembly`, `navigator`. It will not run in plain Node; run it in headless Chromium (Playwright) — the "Warner bridge" (S1-14).
- Video reaches us through the vendor's **P2P relay over WSS**. Connection by device ID resolves a relay on `dvr163.com` (`ngw-cli*.dvr163.com`, `*.kp2p.dvr163.com`, `openapi.dvr163.com`). Connection by LAN IP (port 10000 per docs; the demo uses 10010) only works on the bus LAN.
- Device settings and status go over **MQTT** after a vendor-cloud login (`ConnectApi.userLogin`, base `https://app-api.warner.co.in`), which also returns each device's `deviceSecret`.

## Calls the bridge uses

| Need | SDK call | Callback | Notes |
| --- | --- | --- | --- |
| Pre-connect when the bus slows | `Player.ConnectDevice(deviceid, "", user, pwd, idx, port, 0, ch, sid, "wss", cb)` | `ConnectApi.onconnect(session, code)` → `ConnectApi.login(...)` → `onloginresult` | `connectType 0` = connect only |
| Open sub stream at the stop | `Player.OpenStream(deviceid, "", 0, 0, idx)` | `onopenstream`, then `onrecvframeex(session, frametype, data, len, ch, w, h, enc, fps, ts)` | `streamid 0` = sub, 1 = main. **No API sets width, height or fps** |
| Close at window end | `Player.CloseStream(idx)`; `Player.DisConnectDevice(deviceid, ip)` | `onclosestream`, `ondisconnect` | |
| SD-card fill overnight | `Player.SreachRecord(...)` → `Player.StartPlayBack(...)` | `onsearchrec`, `onsearchrecend`, `onrecvrecframe` | One search per device at a time (docs). Playback speed: **measure** |
| Clock | MQTT get `System.Time.TimeUtc`, `System.Time.TimeZone` | `getDevicePropertyResponse` | Compare with Katch GPS time |
| Health | MQTT actions `R.Sync.Stat.TF`, `R.Sync.Stat.NetWork`; get `Stat.DeviceInfo.DevSoftVer` | action / property responses | |
| Capabilities | `ConnectApi.getDeviceModal(devId)` | promise | Check for any encoder/sub-stream setting; **measure** |

Frame types: 0 audio, 1 I-frame, 2 P-frame. `enc` is H.264 or H.265. Error codes: 0 ok, -2 timeout, -10 local closed, -11 remote closed, -12 addressing failed, -13 device offline, -20 wrong password.

## Rules for our code

1. **Drop audio.** Discard `frametype 0` inside the bridge. Audio never reaches the recorder, the store or a log.
2. **Allow-list the vendor API.** The vendor account can change anything (privacy mode, users, alarms, PTZ, SD format). The bridge may call only: connect/login/open/close/disconnect, search/playback, `getDeviceModal`, and MQTT **gets** of the properties named in this file. The single permitted write is `System.Time.TimeUtc` (clock sync), and only if `DECISIONS.md` records approval. Everything else is refused in code.
3. **Never read `User.List`.** It returns device user names and passwords.
4. **Known-bad credentials.** Device user `admin` with an **empty password** (the factory default) must make the bridge refuse to connect, alongside the FOORIR defaults.
5. **Never derive passwords.** The demo (`index.js`) computes a LAN password from the device ID with a fixed salt. Do not copy or use that logic; credentials come only from the vault/env.
6. **Pre-connect.** Connecting, logging in and opening a stream may take longer than the 3 s pre-roll. Connect (`connectType 0`) when speed drops below ~10 km/h; open the stream when the stop window opens; keep the last GOP in memory so the clip can start on an I-frame. Time-to-first-frame: **measure**.
7. **Remux, don't decode.** Write Annex-B frames to MP4 with FFmpeg `-c copy`. If `enc` is H.265, also write a small H.264 proxy for the review screen, because Android WebViews may not play HEVC.

## Privacy posture to check daily (MQTT gets, report only)

| Property | Want | Why |
| --- | --- | --- |
| `Alarm.MsgToApp.Enabled` | false | Alarm pop-ups send events to the vendor app |
| `Alarm.Enabled` | false | Alarm snapshots and pushes |
| `SmartDetect.Human.DrwBox` | false | Draws boxes into the video and pollutes training frames |
| `Audio.Input[0].Enabled` | false | We never want audio |
| `System.PrivateMode.Enabled` | false | If true, the camera sends no video |
| `Record.RecordTriggers.Continuous` | true | SD fill needs continuous recording |
| `Record.Stream` | `Sub` | SD fill should pull the sub stream |
| `Protocol.OnvifServer.Enabled` | report | ONVIF/RTSP would allow an on-bus LAN path later |

Changing these is a commissioning step a person runs (`tools/commission_warner.py --apply`, H-15), not something the bridge does at runtime.

## Open questions for the vendor (H-14)

1. Where are the P2P relay (`dvr163.com`) and the cloud API hosted? Can our pilot devices use an India-hosted relay?
2. Can the sub stream be set to 640×360, 5–6 fps, ≤ 300 kbps (capability set or device config), or is it fixed?
3. Is there a supported server-side SDK (C, Linux, Node) or an RTSP/ONVIF path, so we do not need a headless browser?
4. Please rotate the access token embedded in `connector.js`, and confirm whether LAN passwords can be derived from device IDs on shipped firmware.
5. Is there a read-only or limited-scope account type for the pilot?
6. Does SD playback run faster than real time, and is any vendor cloud recording enabled by default?
