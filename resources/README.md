# HX-CCD22 Bus Counter Prototype

This prototype receives the HTTP JSON pushed by an HX-CCD22 camera, stores it
in SQLite, and shows a basic IN/OUT dashboard.

## Run the audit receiver first

Use this when answering the senior's question: "what data does the camera send,
and can it send to our server instead of Foorir?"

```bash
python3 camera_data_audit_receiver.py
```

Point the camera's HTTP Address1 to the laptop/server IP and this port. The
receiver stores all raw JSON in `hx_camera_audit.db` and exposes:

- `POST /api/camera/heartBeat`
- `POST /api/camera/dataUpload`
- `GET /health`
- `GET /api/config`
- `GET /api/status/current`
- `GET /api/dashboard`
- `GET /api/debug/report`
- `GET /api/debug/requests`
- `GET /api/debug/uploads`
- `GET /api/debug/events`
- `GET /api/debug/fields`
- `GET /api/debug/child-mode`

Open `http://localhost:8088/api/debug/report` to see which capabilities have
actually appeared from the real camera firmware: heartbeat, upload, adult/child
fields, event list, height, stay time, and historical batches.

For Increment-vs-Total mode testing and public ngrok/Cloudflare tunnel testing,
follow `resources/HX_CCD22_PUBLIC_AND_MODE_TEST_RUNBOOK.md`.

## Run the older live prototype

```bash
python3 camera_live_receiver.py
```

Open `http://localhost:8088` on the laptop running the server.

The receiver listens on all network interfaces (`0.0.0.0`) and exposes:

- `POST /api/camera/heartBeat`
- `POST /api/camera/dataUpload`
- `GET /api/dashboard`
- `GET /health`

No packages or database server are required. Data is saved in
`hx_counter.db`.

## Test without the camera

```bash
curl -X POST http://localhost:8088/api/camera/heartBeat \
  -H 'Content-Type: application/json' \
  -d '{"sn":"2100002507152593","time":1750660200}'

curl -X POST http://localhost:8088/api/camera/dataUpload \
  -H 'Content-Type: application/json' \
  -d '{
    "sn":"2100002507152593",
    "startTime":1750660200,
    "endTime":1750660260,
    "time":1750660260,
    "in":5,
    "out":3,
    "passby":1,
    "turnback":0,
    "avgStayTime":1200
  }'
```

## Connect the physical camera

1. Put the laptop and camera on a network where they can reach each other.
2. Find the laptop's LAN IP with `hostname -I`.
3. Start this server and allow inbound TCP port `8088` in the firewall.
4. In `PassengerFlowClient.exe`, open `Device Info > HTTP`.
5. Replace `op.foorir.com` with the laptop LAN IP, keep port `8088`, enable
   Address1, Attribute, Event, and StayPre, then click **Set**.
6. Use **Manual Upload** or walk across the configured detection line.
7. Watch the terminal and refresh `http://localhost:8088`.

Do not enter `127.0.0.1` or `localhost` in the camera. Those names refer to the
camera itself. A laptop LAN IP works only while both devices are on the same
reachable network.

For a bus over 4G, use a public HTTPS hostname such as
`counter.example.com:443`, backed by a hosted server. A public IP can work, but
a domain with TLS is easier to operate. The bus does not need a public IP:
the camera initiates the outbound connection through the bus router.

## Data contract

The backend replies to heartbeat with `dataMode: "Add"`, so each upload is an
increment for its statistics window. Dashboard totals therefore sum accepted
uploads. Duplicate retries are ignored using a payload fingerprint. The receiver
configuration is visible at `/api/config`.

Core upload fields:

| JSON field | Meaning | Stored column |
| --- | --- | --- |
| `sn` | Camera serial number | `sn` |
| `startTime`, `endTime`, `time` | UNIX timestamps in seconds | matching time columns |
| `in`, `out` | Entry and exit counts | `in_count`, `out_count` |
| `passby`, `turnback` | Other movement counts | matching count columns |
| `avgStayTime` | Average dwell in milliseconds | `avg_stay_time_ms` |
| `inAdult`, `outAdult` | Height-classified adult counts | matching columns |
| `inChild`, `outChild` | Height-classified child counts | matching columns |
| `eventList[]` | Per-person event, height, and dwell data | `person_events` |
| `attributes[]` | Actual firmware per-person event list | `person_events` |

The complete original JSON is also stored for debugging. Historical uploads
with `{sn, len, data: [...]}` are accepted.

The tested firmware has emitted `attributes[]` rather than `eventList[]`.
Observed attribute fields include `eventType`, `height`, `idIndex`, `lineId`,
`personId`, `stayTime`, and `timeStamp`.

Use separate DB files when comparing modes:

```bash
DB_PATH=hx_camera_increment_test.db DATA_MODE=Add python3 camera_data_audit_receiver.py
DB_PATH=hx_camera_total_mode_test.db DATA_MODE=Total python3 camera_data_audit_receiver.py
```

For child-mode validation, use a fresh DB and set the classification threshold
you want the backend to use if the camera does not emit explicit adult/child
fields:

```bash
DB_PATH=hx_camera_child_mode_test.db DATA_MODE=Add CHILD_HEIGHT_CM=140 python3 camera_data_audit_receiver.py
```

Then check `GET /api/debug/child-mode`. The report separates explicit camera
fields (`inAdult`, `outAdult`, `inChild`, `outChild`) from backend-inferred
height classification using `attributes[].height`.

## What to tell the reviewer

- The camera performs inference and counting on-device. We receive metadata,
  not the video stream.
- The camera pushes JSON to a configurable server address and port using HTTP.
- Heartbeat proves device/network health; data upload carries the counts.
- Localhost is suitable for a same-LAN lab test. Deployed buses need a hosted
  internet-reachable API because laptop LAN addresses are not reachable over
  mobile internet.
- `IN - OUT` is only an occupancy estimate. It can drift after missed events,
  restarts, multiple doors, or passengers already onboard at trip start.
- Adult/child is a height threshold, not age recognition.
- Before production, capture real payloads from this exact firmware and verify
  timestamps, event units, retry behavior, authentication support, and offline
  backfill.

## Prototype limitations

This intentionally has no login, TLS, PostgreSQL, bus/route management, or
production monitoring. It auto-registers any serial number that posts data.
Those belong in the next phase after one real camera successfully reports.
