# HX-CCD22 Bus Setup Requirements

## 1. Overview

This document describes the hardware, network, configuration, backend, and rollout requirements for deploying HX-CCD22 people-counting cameras in buses.

The HX-CCD22 performs passenger counting on the device and sends count metadata to a backend server using HTTP or HTTPS JSON push requests. The backend is responsible for storing the data, mapping cameras to buses and doors, aggregating counts, and serving the fleet dashboard.

Recommended production flow:

```text
HX-CCD22 camera
  -> bus LAN / PoE switch / bus router
  -> mobile internet
  -> HTTPS ingestion backend
  -> database and analytics services
  -> fleet dashboard
```

## 2. Camera Hardware Requirements

| Item | Requirement |
| --- | --- |
| Camera model | HX-CCD22 people counter |
| Installation type | Top-mounted horizontal installation |
| Power input | 9-36V DC power or PoE through RJ45, depending on bus wiring design |
| Network interface | RJ45 Ethernet / PoE port |
| Optional interfaces | RS485 and DI/DO, if required by the installation design |
| Configuration access | Camera web interface or vendor-provided configuration/search tool |
| Data protocols | HTTP/HTTPS JSON push for backend integration |
| Video protocol | ONVIF may be available depending on firmware and deployment requirements |

The backend receives count metadata through the push API. Live video, if required, should be designed as a separate feature workstream.

## 3. Physical Installation Requirements

The camera should be mounted above the passenger doorway or counting area where passengers naturally pass through a controlled detection zone.

Installation guidelines:

- Mount the camera horizontally from the top.
- Keep the lens fully visible and unobstructed.
- Avoid blocking the camera with panels, stickers, luggage racks, wiring, or signage.
- Install at a height that covers the full walking path.
- Enter the measured installation height in the camera configuration.
- Keep the configured height as close as possible to the physical mounting height.
- Configure the detection area to cover only the valid passenger walking channel.
- Place the detection line near the center of the detection area.
- Set the direction arrow according to the intended entry/exit direction.
- Recalibrate after changing height, angle, detection area, or detection line.

Accuracy can be affected by:

- Incorrect mounting height.
- Camera tilt or angle mismatch.
- Poor detection-line placement.
- Strong reflections, shadows, or lighting changes.
- Occlusion from passengers standing under the camera.
- Doorway geometry that allows passengers to bypass the detection zone.

## 4. Power Requirements

The HX-CCD22 can be powered through DC power or PoE, depending on the bus wiring design.

| Option | Requirement | Notes |
| --- | --- | --- |
| DC power | 9-36V DC | Suitable when the bus provides stable DC power near the mounting point. |
| PoE | PoE switch or PoE injector through RJ45 | Provides network and power through one Ethernet cable. |

For bus deployment:

- Use a stable power source during vehicle operation.
- Protect connectors from vibration and accidental disconnection.
- Avoid wiring paths that may be damaged during maintenance.
- Confirm power behavior during ignition, shutdown, and route operation.

## 5. Network Requirements

### 5.1 Local Installation Access

During installation and calibration, the camera should be reachable from a local device on the same network.

The camera IP can be found using:

- Router DHCP client list.
- Vendor-provided search/configuration tool.
- Camera web interface discovery workflow.
- Approved network scan tools, if allowed by the client network policy.

Once the IP is known, technicians can access the camera web interface for configuration, calibration, and diagnostic checks.

### 5.2 Production Bus Connectivity

Each bus should have a router or gateway with internet connectivity, typically 4G/5G.

Network requirements:

- Camera must reach the public backend hostname and port.
- Production ingestion should use HTTPS on port `443`.
- The bus router must allow outbound traffic to the backend.
- The backend firewall must allow inbound HTTPS traffic from the expected networks.
- Wired Ethernet is preferred inside the bus for stability.
- If WiFi is used, confirm supported bands and signal quality during operation.
- The bus does not need a public IP address for push ingestion because the camera initiates outbound requests.

### 5.3 DHCP And Static IP

DHCP is usually the simplest option for bus LAN deployment. Static addressing may be used if required by the client network plan.

If static IPs are used:

- Reserve the camera IP in the bus network plan.
- Avoid conflicts with routers, switches, and other onboard devices.
- Record camera IP, serial number, bus ID, and door position.
- Confirm that the camera still reaches the backend after network changes.

## 6. Camera Data Push Configuration

Configure the camera HTTP/HTTPS data push settings to point to the backend ingestion service.

Recommended production configuration:

| Setting | Recommended value |
| --- | --- |
| Protocol | HTTPS |
| Server address | Production backend hostname, for example `api.example.com` |
| Server port | `443` |
| Data API | `/api/camera/dataUpload` |
| Heartbeat API | `/api/camera/heartBeat` |
| Format | JSON |
| Data scale | Increment / Add |
| Upload mode | Interval mode |
| Upload interval | Based on dashboard freshness and bandwidth requirements |
| Device info | Enabled |
| Supplement / attributes | Enabled when height, stay-time, or per-person events are required |
| Child mode | Enabled only when adult/child height-category reporting is required |

Example production URLs:

```text
https://api.example.com/api/camera/heartBeat
https://api.example.com/api/camera/dataUpload
```

### Data Mode Recommendation

Increment/Add mode is recommended for analytics because each upload represents a reporting window. This makes it easier to:

- Build hourly and daily reports.
- Detect missing upload windows.
- Deduplicate retries.
- Recalculate aggregates from raw payloads.
- Handle camera or trip resets in a controlled way.

## 7. Backend Requirements

The backend should provide:

- HTTPS ingestion endpoints for heartbeat and data upload.
- Camera registry keyed by serial number.
- Bus registry and door-position mapping.
- Raw payload storage.
- Normalized heartbeat records.
- Normalized count upload records.
- Per-person attribute storage when enabled.
- Dashboard APIs for fleet, bus, and camera views.
- Export/reporting support.
- Authentication for dashboard and administrative users.
- Monitoring for heartbeat freshness and missing uploads.

Recommended production database:

- PostgreSQL or another durable relational database.
- SQLite may be used for prototypes, but it is not recommended for fleet production.

## 8. Multiple Cameras Per Bus

For buses with multiple passenger doors, install one camera per door or per counting zone.

Each physical camera should be registered with:

- Camera serial number.
- Bus ID.
- Door position, such as front, rear, middle, or custom label.
- Installation date.
- Installation height.
- Network mode.
- Active/inactive status.
- Whether the camera contributes to bus-level aggregation.

The camera payload includes the camera serial number, but bus, route, stop, and door context should be supplied by the backend registry.

Example bus aggregation:

```text
bus_in = front_camera_in + rear_camera_in
bus_out = front_camera_out + rear_camera_out
bus_passby = front_camera_passby + rear_camera_passby
bus_turnback = front_camera_turnback + rear_camera_turnback
```

## 9. Dashboard Requirements

The dashboard should separate device health from count data freshness.

Recommended dashboard health indicators:

- Heartbeat status.
- Last data upload time.
- Camera/device metadata.
- Missing or delayed upload windows.
- Backend ingestion status.
- Optional stream status, if a video feature is added separately.

Recommended dashboard sections:

- Fleet overview.
- Bus detail page.
- Camera/device detail page.
- IN/OUT/passby/turnback totals.
- Adult/child split, if enabled.
- Height distribution, if attributes are enabled.
- Stay-time analytics.
- Raw payload/support view for authorized technical users.
- Export and reporting page.

## 10. Occupancy And Trip Rules

Basic occupancy can be estimated as:

```text
occupancy = max(0, total_in - total_out)
```

This is an estimate, not a guaranteed passenger manifest. It can drift due to:

- Missed counts.
- Camera restart or counter reset.
- Passengers already onboard at trip start.
- Multiple doors not fully covered.
- Incorrect direction configuration.
- Network outage or delayed upload.
- Manual counter reset.

Before production rollout, define:

- Trip start and trip end rules.
- Counter reset rules.
- How counts are handled at depots and route breaks.
- How multiple cameras contribute to one bus total.
- Whether occupancy should reset per trip, per day, or by operational event.

## 11. Data And Feature Boundaries

The HTTP push payload provides passenger-count metadata. It does not provide:

- Live video stream.
- Images.
- GPS location.
- Bus ID.
- Route ID.
- Stop ID.
- Passenger identity.
- Ticketing or payment data.

If GPS, ticketing, route, stop, or live video is required, those should be integrated through separate systems or separately confirmed camera capabilities.

Adult/child reporting should be presented as height-based classification, not real age detection.

## 12. Production Rollout Checklist

Before production deployment, confirm:

- Camera is securely mounted and horizontally aligned.
- Lens is unobstructed.
- Installation height is measured and configured.
- Detection area, line, and direction are configured.
- Power is stable during bus operation.
- Camera can reach the production HTTPS backend.
- Heartbeat and data upload endpoints are configured correctly.
- Camera serial number is mapped to the correct bus and door.
- Required fields appear in backend ingestion.
- Raw and normalized storage are active.
- Dashboard shows the correct bus and camera status.
- Backup, monitoring, and alerting are configured.
- Client operations team understands trip/reset rules.

## 13. Information To Finalize With The Client

Confirm these items before final production sizing:

- Total number of buses.
- Number of cameras per bus.
- Required upload interval.
- Required data retention period.
- Hosting environment or cloud provider.
- Production domain name.
- Certificate management process.
- Expected number of dashboard users.
- Required route/trip/stop integration.
- Whether GPS integration is required.
- Whether live video is required.
- Whether adult/child reporting is required.
