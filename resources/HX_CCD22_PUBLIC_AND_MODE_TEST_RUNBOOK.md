# HX-CCD22 Public Receiver And Data Mode Test Runbook

Use this runbook before writing the final PDF/report. It keeps the local,
public-domain, Increment, and Total-mode tests separate so the counts are easy
to explain.

## What Increment Upload Windows Mean

In **Increment** mode, each `dataUpload` payload is one statistics window. The
payload fields `startTime` and `endTime` identify that window, and the count
fields describe only what happened inside that window.

Example:

```json
{
  "startTime": 1782465900,
  "endTime": 1782465960,
  "in": 2,
  "out": 1
}
```

This means 2 people entered and 1 exited during that 60-second window. The
receiver dashboard total is therefore the sum of all accepted upload windows in
the current SQLite database.

The camera website can show different totals because it displays the camera's
own current internal statistics. If the camera was not cleared at the same time
as the receiver DB was started, the two totals will not have the same baseline.

## Recommended Default

Keep **Data Scale = Increment** for production analytics unless Total mode is
proven better in testing.

Increment mode is better for:

- minute/hour/day charts
- replaying raw uploads
- avoiding ambiguity after camera/statistics resets
- detecting missed windows or duplicate retries

Total mode may be useful if it matches the camera website directly, but it must
be tested for reset behavior, repeated values, and negative jumps.

## Local Increment Baseline Test

1. Start a fresh receiver DB:

   ```bash
   cd /home/p21-0217/Documents/Bus-AI-Dashboard
   DB_PATH=hx_camera_increment_test.db DATA_MODE=Add python3 camera_data_audit_receiver.py
   ```

2. Configure the camera:

   ```text
   Protocol: HTTP
   Server Address: 172.16.16.118
   Server Port: 8088
   Format: JSON
   Data API: /api/camera/dataUpload
   Heartbeat API: /api/camera/heartBeat
   Data Scale: Increment
   Upload Mode: Interval mode
   Supplement: enabled
   Device Info: enabled
   ```

3. Clear the camera statistics from the camera website only if you want the
   website and receiver to start from the same baseline.

4. Walk a small controlled count, for example 5 IN and 3 OUT.

5. Check:

   ```text
   http://172.16.16.118:8088/health
   http://172.16.16.118:8088/api/config
   http://172.16.16.118:8088/api/status/current
   http://172.16.16.118:8088/api/debug/requests
   http://172.16.16.118:8088/api/debug/uploads
   http://172.16.16.118:8088/api/debug/events
   http://172.16.16.118:8088/api/debug/report
   http://172.16.16.118:8088/api/debug/child-mode
   ```

6. Record the camera website totals and the receiver totals.

## Total Mode Test

Run this in a separate DB so Total mode does not mix with Increment mode.

1. Stop the Increment receiver.

2. Start a fresh Total-mode test receiver:

   ```bash
   cd /home/p21-0217/Documents/Bus-AI-Dashboard
   DB_PATH=hx_camera_total_mode_test.db DATA_MODE=Total python3 camera_data_audit_receiver.py
   ```

3. Change the camera:

   ```text
   Data Scale: Total
   ```

4. Keep all other camera fields the same.

5. Walk a controlled count again.

6. Compare consecutive `/api/debug/uploads` rows:

   - If `in_count` and `out_count` increase cumulatively, the camera is sending
     total values.
   - If only the latest window count appears, it still behaves like Increment.
   - If values reset after clearing statistics or time changes, document the
     reset behavior before using Total mode in production.

7. Decision rule:

   - Use Increment if uploads are clean time windows.
   - Use Total only if it reliably matches the camera website and reset handling
     is understood.

## Public Test With ngrok

Use ngrok when you need a quick public HTTPS URL.

1. Start the receiver:

   ```bash
   cd /home/p21-0217/Documents/Bus-AI-Dashboard
   DB_PATH=hx_camera_ngrok_test.db DATA_MODE=Add python3 camera_data_audit_receiver.py
   ```

2. In another terminal:

   ```bash
   ngrok http 8088
   ```

3. Copy the HTTPS host, for example:

   ```text
   abc123.ngrok-free.app
   ```

4. Configure the camera:

   ```text
   Protocol: HTTPS
   Server Address: abc123.ngrok-free.app
   Server Port: 443
   Data API: /api/camera/dataUpload
   Heartbeat API: /api/camera/heartBeat
   Format: JSON
   Data Scale: Increment
   ```

5. Validate from a browser/Postman:

   ```text
   https://abc123.ngrok-free.app/health
   https://abc123.ngrok-free.app/api/status/current
   https://abc123.ngrok-free.app/api/debug/report
   ```

6. Wait for at least one heartbeat and one upload.

## Public Test With Cloudflare Tunnel

Use Cloudflare Tunnel if ngrok is not available or if the camera has trouble
with the ngrok URL.

1. Start the receiver:

   ```bash
   cd /home/p21-0217/Documents/Bus-AI-Dashboard
   DB_PATH=hx_camera_cloudflare_test.db DATA_MODE=Add python3 camera_data_audit_receiver.py
   ```

2. In another terminal:

   ```bash
   cloudflared tunnel --url http://localhost:8088
   ```

3. Copy the HTTPS host, for example:

   ```text
   sample.trycloudflare.com
   ```

4. Configure the camera:

   ```text
   Protocol: HTTPS
   Server Address: sample.trycloudflare.com
   Server Port: 443
   Data API: /api/camera/dataUpload
   Heartbeat API: /api/camera/heartBeat
   Format: JSON
   Data Scale: Increment
   ```

5. Validate the same APIs:

   ```text
   https://sample.trycloudflare.com/health
   https://sample.trycloudflare.com/api/status/current
   https://sample.trycloudflare.com/api/debug/report
   ```

## Expected Result

The public test passes when:

- `/health` returns `status: ok`
- `/api/status/current` shows the camera `online`
- `/api/debug/report` shows `heartbeat: true` and `data_upload: true`
- `/api/debug/report` shows `attributes: true` after a person event is captured
- `/api/debug/events` contains height and stay-time rows from `attributes[]`

## Child Mode Test

Run this before writing the final PDF if adult/child analytics are required.
The receiver can detect two outcomes:

- explicit camera fields: `inAdult`, `outAdult`, `inChild`, `outChild`
- inferred child/adult split from `attributes[].height`

1. Start a fresh child-mode test DB:

   ```bash
   cd /home/p21-0217/Documents/Bus-AI-Dashboard
   DB_PATH=hx_camera_child_mode_test.db DATA_MODE=Add CHILD_HEIGHT_CM=140 python3 camera_data_audit_receiver.py
   ```

2. In the camera configuration, keep:

   ```text
   Data Scale: Increment
   Upload Mode: Interval mode
   Supplement: enabled
   Device Info: enabled
   ```

3. Enable child mode and use realistic height settings:

   ```text
   Installation height: measured physical mounting height
   Filter height: 100-120 cm
   Child threshold: 130-140 cm
   ```

   Do not set filter height too high. If filter height is 150 cm, many short
   people/children may be ignored instead of classified.

4. Run a controlled walk test:

   ```text
   2 adult-height IN crossings
   1 short/child-threshold IN crossing if available
   1 OUT crossing
   ```

5. Check:

   ```text
   http://172.16.16.118:8088/api/debug/child-mode
   http://172.16.16.118:8088/api/debug/fields
   http://172.16.16.118:8088/api/debug/uploads
   http://172.16.16.118:8088/api/debug/events
   ```

6. Interpret `/api/debug/child-mode`:

   - `camera_explicit_adult_child_counts_seen: true` means the camera emitted
     adult/child aggregate fields.
   - `height_based_child_classification_possible: true` means the backend can
     classify by `attributes[].height`.
   - `event_type_distribution` shows whether child mode changed `eventType`
     values.
   - `recommendation` gives the report-ready conclusion.

For reporting, be precise: child/adult from this camera is height-based
classification, not real age detection.

## Known Public-Tunnel Caveats

- Free ngrok URLs change after restart unless a reserved domain is configured.
- The receiver may see the tunnel proxy IP instead of the camera's real IP.
- The camera must be able to resolve DNS and make outbound HTTPS requests.
- If HTTPS fails from the camera, test HTTP on a public VPS or a production
  HTTPS domain with a normal certificate.
- Do not use free tunnels as production infrastructure.

## PDF Inputs To Capture

Before generating the final PDF, capture:

- camera Data Push settings screenshot
- `/api/config`
- `/api/status/current`
- `/api/debug/report`
- sample `/api/debug/uploads`
- sample `/api/debug/events`
- camera website Data tab totals
- notes from Increment mode test
- notes from Total mode test
- notes from ngrok or Cloudflare public test
