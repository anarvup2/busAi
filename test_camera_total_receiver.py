import importlib
from datetime import datetime
import unittest
from unittest.mock import patch

import camera_total_receiver


class CameraTotalReceiverTests(unittest.TestCase):
    def setUp(self):
        self.app = importlib.reload(camera_total_receiver)

    def camera_response(self, enter=25, leave=12):
        return {
            "enter": enter,
            "leave": leave,
            "pass": 30,
            "return": 4,
            "stay": 2,
            "stayTimePerPerson": 1.5,
            "result": {"code": "0", "isError": "false"},
        }

    def test_display_response_replaces_totals(self):
        self.app.apply_display_response(self.camera_response(25, 12))
        self.app.apply_display_response(self.camera_response(26, 12))
        data = self.app.snapshot_state()
        self.assertEqual(data["in"], 26)
        self.assertEqual(data["out"], 12)
        self.assertEqual(data["current_stay"], 2)
        self.assertEqual(data["estimated_onboard"], 14)
        self.assertEqual(data["avg_stay_time_seconds"], 1.5)

    def test_push_payload_never_changes_display_totals(self):
        self.app.apply_display_response(self.camera_response(25, 12))
        self.app.record_push(
            "/api/camera/dataUpload",
            "172.16.17.50",
            {
                "sn": "CAM",
                "in": 0,
                "out": 1,
                "passby": 0,
                "turnback": 1,
            },
        )
        data = self.app.snapshot_state()
        self.assertEqual(data["in"], 25)
        self.assertEqual(data["out"], 12)
        self.assertEqual(data["last_sn"], "CAM")
        self.assertEqual(data["push_messages"], 1)

    def test_invalid_display_response_is_rejected(self):
        with self.assertRaises(ValueError):
            self.app.apply_display_response(
                {"result": {"code": "1", "message": "failed"}}
            )

    @patch("camera_total_receiver.fetch_camera_display")
    def test_poll_once_uses_camera_display_response(self, fetch):
        fetch.return_value = self.camera_response(35, 16)
        self.app.poll_camera_once()
        data = self.app.snapshot_state()
        self.assertEqual((data["in"], data["out"]), (35, 16))
        self.assertIsNone(data["last_poll_error"])
        self.assertEqual(data["poll_successes"], 1)

    @patch("camera_total_receiver.fetch_camera_display")
    def test_poll_failure_keeps_last_good_totals(self, fetch):
        self.app.apply_display_response(self.camera_response(35, 16))
        fetch.side_effect = OSError("camera unreachable")
        self.app.poll_camera_once()
        data = self.app.snapshot_state()
        self.assertEqual((data["in"], data["out"]), (35, 16))
        self.assertEqual(data["last_poll_error"], "camera unreachable")

    @patch("camera_total_receiver.fetch_camera_display")
    def test_manual_refresh_returns_new_camera_totals(self, fetch):
        fetch.return_value = self.camera_response(40, 18)
        data = self.app.refresh_camera()
        self.assertEqual((data["in"], data["out"]), (40, 18))

    @patch("camera_total_receiver.fetch_camera_display")
    @patch("camera_total_receiver.fetch_camera_reset")
    def test_clear_verifies_zero_totals(self, reset, display):
        reset.return_value = {
            "result": {"code": "0", "isError": "false"}
        }
        display.return_value = self.camera_response(0, 0) | {
            "pass": 0,
            "return": 0,
            "stay": 0,
        }
        data = self.app.clear_camera_totals()
        self.assertEqual(
            (
                data["in"],
                data["out"],
                data["passby"],
                data["turnback"],
                data["current_stay"],
            ),
            (0, 0, 0, 0, 0),
        )

    @patch("camera_total_receiver.fetch_camera_display")
    @patch("camera_total_receiver.fetch_camera_reset")
    def test_failed_clear_preserves_last_good_totals(self, reset, display):
        self.app.apply_display_response(self.camera_response(35, 16))
        reset.return_value = {
            "result": {"code": "0", "isError": "false"}
        }
        display.return_value = self.camera_response(35, 16)
        with patch("camera_total_receiver.time.monotonic") as monotonic:
            monotonic.side_effect = [0, 4]
            with self.assertRaisesRegex(ValueError, "did not become zero"):
                self.app.clear_camera_totals()
        data = self.app.snapshot_state()
        self.assertEqual((data["in"], data["out"]), (35, 16))

    def test_snapshot_includes_stream_metadata(self):
        data = self.app.snapshot_state()
        self.assertIn("/media/webrtc?", data["webrtc_url"])
        self.assertTrue(data["rtc_client_url"].endswith("/js/rtcClient.js"))

    def test_clear_requires_dashboard_header(self):
        with self.assertRaisesRegex(PermissionError, "header required"):
            self.app.validate_clear_request(None, {"confirm": "CLEAR"})

    def test_clear_requires_explicit_confirmation(self):
        with self.assertRaisesRegex(ValueError, "explicit CLEAR"):
            self.app.validate_clear_request(
                self.app.DASHBOARD_REQUEST_VALUE, {"confirm": "NO"}
            )

    def test_bus_has_two_logical_cameras_and_counts_once(self):
        self.app.apply_display_response(self.camera_response(25, 12))
        bus = self.app.bus_snapshot("B-101")
        self.assertEqual(bus["capacity"], 65)
        self.assertEqual(len(bus["cameras"]), 2)
        self.assertEqual(
            {camera["physical_source_id"] for camera in bus["cameras"]},
            {"hx-primary"},
        )
        self.assertEqual(bus["totals"]["in"], 25)
        self.assertEqual(bus["totals"]["out"], 12)
        self.assertTrue(bus["cameras"][0]["include_in_aggregation"])
        self.assertFalse(bus["cameras"][1]["include_in_aggregation"])

    def test_fleet_totals_match_single_physical_source(self):
        self.app.apply_display_response(self.camera_response(31, 14))
        fleet = self.app.fleet_snapshot()
        self.assertEqual(fleet["totals"]["in"], 31)
        self.assertEqual(fleet["totals"]["out"], 14)
        self.assertEqual(fleet["totals"]["logical_cameras_total"], 2)
        self.assertEqual(fleet["totals"]["physical_devices_total"], 1)

    def test_heartbeat_status_thresholds(self):
        stamp = datetime.fromtimestamp(1_000).isoformat(timespec="seconds")
        self.assertEqual(
            self.app.heartbeat_status(stamp, 1_090)[0], "online"
        )
        self.assertEqual(
            self.app.heartbeat_status(stamp, 1_091)[0], "delayed"
        )
        self.assertEqual(
            self.app.heartbeat_status(stamp, 1_180)[0], "delayed"
        )
        self.assertEqual(
            self.app.heartbeat_status(stamp, 1_181)[0], "offline"
        )

    def test_heartbeat_records_device_and_server_time(self):
        self.app.record_push(
            "/api/camera/heartBeat",
            "172.16.17.50",
            {"sn": "CAM", "time": 123456},
        )
        data = self.app.snapshot_state()
        self.assertEqual(data["last_heartbeat_device_time"], 123456)
        self.assertIsNotNone(data["last_heartbeat"])

    def test_session_sample_is_added_once_per_minute(self):
        self.app.apply_display_response(self.camera_response(4, 1))
        self.app.apply_display_response(self.camera_response(5, 1))
        samples = self.app.snapshot_state()["session_samples"]
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["in"], 4)

    def test_csv_contains_bus_camera_and_sample_rows(self):
        self.app.apply_display_response(self.camera_response(7, 3))
        content = self.app.export_csv().decode()
        self.assertIn("type,bus_id,camera_id", content)
        self.assertIn("bus,B-101", content)
        self.assertIn("camera,B-101,B-101-front", content)
        self.assertIn("camera,B-101,B-101-rear", content)
        self.assertIn("sample,B-101", content)

    def test_unknown_bus_and_camera_are_rejected(self):
        with self.assertRaises(KeyError):
            self.app.bus_snapshot("missing")
        with self.assertRaises(KeyError):
            self.app.find_camera("missing")


if __name__ == "__main__":
    unittest.main()
