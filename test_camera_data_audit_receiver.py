import importlib
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import camera_data_audit_receiver


class CameraDataAuditReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app = importlib.reload(camera_data_audit_receiver)
        self.app.DB_PATH = Path(self.tmpdir.name) / "audit.db"
        self.app.init_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def upload_payload(self):
        return {
            "sn": "2100002507152593",
            "startTime": 1751230000,
            "endTime": 1751230060,
            "time": 1751230060,
            "in": 3,
            "out": 1,
            "passby": 2,
            "turnback": 1,
            "avgStayTime": 1200,
            "inAdult": 2,
            "outAdult": 1,
            "inChild": 1,
            "outChild": 0,
            "passbyAdult": 2,
            "passbyChild": 0,
            "turnbackAdult": 1,
            "turnbackChild": 0,
            "total": 8,
            "eventList": [
                {
                    "id": 10,
                    "timestamp": 1751230059000000,
                    "eventType": 0,
                    "height": 172,
                    "stayTime": 900,
                }
            ],
        }

    def attributes_payload(self, height=149):
        return {
            "sn": "221000002507152593",
            "startTime": 1782395380,
            "endTime": 1782395381,
            "time": 1782395380,
            "in": 1,
            "out": 0,
            "passby": 0,
            "turnback": 0,
            "avgStayTime": 1360,
            "len": 1,
            "connectionType": "Wired",
            "hostName": "CAM-0",
            "hwPlatform": "V5.0",
            "ipAddress": "0.0.0.0",
            "ipAddressMethod": "DHCP",
            "macAddress": "4C:BC:98:66:0C:C8",
            "swRelease": "V7.2.5.5-V5-22-GJ",
            "timeZone": -5,
            "attributes": [
                {
                    "eventType": 0,
                    "height": height,
                    "idIndex": 178207,
                    "lineId": 0,
                    "personId": 178207,
                    "stayTime": 1360,
                    "timeStamp": 1782395380000000,
                }
            ],
        }

    def test_records_heartbeat_raw_and_device(self):
        self.app.record_heartbeat(
            "/api/camera/heartBeat",
            "172.16.17.50",
            {"sn": "CAM-1", "time": 1751230000},
        )

        summary = self.app.dashboard_summary()
        self.assertEqual(summary["devices"][0]["sn"], "CAM-1")
        self.assertEqual(summary["devices"][0]["heartbeat_count"], 1)
        self.assertEqual(summary["latest_payload"]["payload"]["sn"], "CAM-1")

    def test_records_upload_counts_events_and_observed_fields(self):
        inserted = self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.upload_payload(),
        )

        self.assertEqual(inserted, 1)
        summary = self.app.dashboard_summary()
        self.assertEqual(summary["totals"]["in_total"], 3)
        self.assertEqual(summary["totals"]["out_total"], 1)
        self.assertEqual(summary["totals"]["estimated_onboard"], 2)

        fields = self.app.observed_fields()
        self.assertIn("inAdult", fields["upload_records"])
        self.assertIn("passbyAdult", fields["upload_records"])
        self.assertIn("eventList", fields["upload_records"])
        self.assertIn("height", fields["eventList"])

        upload = self.app.recent_uploads()[0]
        self.assertEqual(upload["passby_adult"], 2)
        self.assertEqual(upload["passby_child"], 0)
        self.assertEqual(upload["turnback_adult"], 1)
        self.assertEqual(upload["turnback_child"], 0)

        events = self.app.recent_events()
        self.assertEqual(events[0]["event_type"], 0)
        self.assertEqual(events[0]["height_cm"], 172)

    def test_records_firmware_attributes_as_person_events(self):
        inserted = self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.attributes_payload(),
        )

        self.assertEqual(inserted, 1)
        events = self.app.recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], 178207)
        self.assertEqual(events[0]["event_timestamp"], 1782395380000000)
        self.assertEqual(events[0]["event_type"], 0)
        self.assertEqual(events[0]["height_cm"], 149)
        self.assertEqual(events[0]["stay_time_ms"], 1360)

        fields = self.app.observed_fields()
        self.assertIn("attributes", fields["upload_records"])
        self.assertIn("height", fields["attributes"])
        self.assertIn("stayTime", fields["attributes"])
        self.assertIn("eventType", fields["attributes"])

    def test_init_db_backfills_attributes_from_existing_raw_uploads(self):
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.attributes_payload(),
        )
        with self.app.db_lock, self.app.sqlite3.connect(self.app.DB_PATH) as conn:
            conn.execute("DELETE FROM person_events")

        self.assertEqual(self.app.recent_events(), [])
        self.app.init_db()

        events = self.app.recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], 178207)
        self.assertEqual(events[0]["height_cm"], 149)

    def test_duplicate_upload_is_not_counted_twice(self):
        payload = self.upload_payload()
        self.assertEqual(
            self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", payload),
            1,
        )
        self.assertEqual(
            self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", payload),
            0,
        )

        summary = self.app.dashboard_summary()
        self.assertEqual(summary["totals"]["upload_rows"], 1)
        self.assertEqual(summary["totals"]["in_total"], 3)

    def test_duplicate_fingerprint_includes_attributes(self):
        first = self.attributes_payload(height=149)
        second = self.attributes_payload(height=150)

        self.assertEqual(
            self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", first),
            1,
        )
        self.assertEqual(
            self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", second),
            1,
        )

        summary = self.app.dashboard_summary()
        self.assertEqual(summary["totals"]["upload_rows"], 2)
        self.assertEqual(summary["totals"]["in_total"], 2)

    def test_historical_batch_records_each_item_with_parent_sn(self):
        payload = {
            "sn": "CAM-H",
            "len": 2,
            "data": [
                {
                    "time": 1751230000,
                    "startTime": 1751229940,
                    "endTime": 1751230000,
                    "in": 1,
                    "out": 0,
                    "passby": 0,
                    "turnback": 0,
                    "avgStayTime": 500,
                },
                {
                    "time": 1751230060,
                    "startTime": 1751230000,
                    "endTime": 1751230060,
                    "in": 2,
                    "out": 1,
                    "passby": 1,
                    "turnback": 0,
                    "avgStayTime": 700,
                },
            ],
        }

        inserted = self.app.record_upload(
            "/api/camera/dataUpload", "172.16.17.50", payload
        )

        self.assertEqual(inserted, 2)
        summary = self.app.dashboard_summary()
        self.assertEqual(summary["totals"]["upload_rows"], 2)
        self.assertEqual(summary["totals"]["in_total"], 3)
        self.assertEqual(summary["devices"][0]["sn"], "CAM-H")

    def test_capability_report_flags_seen_payload_features(self):
        self.app.record_heartbeat(
            "/api/camera/heartBeat",
            "172.16.17.50",
            {"sn": "221000002507152593", "time": 1751230000},
        )
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.upload_payload(),
        )

        report = self.app.capability_report()
        self.assertTrue(report["capabilities_seen"]["heartbeat"])
        self.assertTrue(report["capabilities_seen"]["data_upload"])
        self.assertTrue(report["capabilities_seen"]["adult_child_counts"])
        self.assertTrue(report["capabilities_seen"]["event_list"])
        self.assertTrue(report["capabilities_seen"]["event_heights"])

    def test_capability_report_detects_attributes_without_event_list(self):
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.attributes_payload(),
        )

        report = self.app.capability_report()
        self.assertFalse(report["capabilities_seen"]["event_list"])
        self.assertTrue(report["capabilities_seen"]["attributes"])
        self.assertTrue(report["capabilities_seen"]["per_person_events"])
        self.assertTrue(report["capabilities_seen"]["event_heights"])
        self.assertTrue(report["capabilities_seen"]["event_stay_time"])
        self.assertTrue(report["capabilities_seen"]["event_types"])

    def test_current_status_returns_counts_when_online_delayed_and_offline(self):
        self.app.record_heartbeat(
            "/api/camera/heartBeat",
            "172.16.17.50",
            {"sn": "221000002507152593", "time": 1751230000},
        )
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.attributes_payload(),
        )
        heartbeat_at = self.app.parse_iso_timestamp(
            self.app.current_status()["last_heartbeat_at"]
        )

        online = self.app.current_status(now=heartbeat_at + timedelta(seconds=90))
        delayed = self.app.current_status(now=heartbeat_at + timedelta(seconds=91))
        offline = self.app.current_status(now=heartbeat_at + timedelta(seconds=181))

        self.assertEqual(online["status"], "online")
        self.assertEqual(delayed["status"], "delayed")
        self.assertEqual(offline["status"], "offline")
        self.assertEqual(offline["device"]["sn"], "221000002507152593")
        self.assertEqual(offline["totals"]["in"], 1)
        self.assertEqual(offline["totals"]["out"], 0)
        self.assertEqual(offline["totals"]["estimated_onboard"], 1)
        self.assertEqual(offline["latest_payload_summary"]["attributes_count"], 1)
        self.assertEqual(offline["receiver_config"]["data_mode"], self.app.DATA_MODE)
        self.assertEqual(
            offline["receiver_config"]["camera_endpoints"]["data_upload"],
            "/api/camera/dataUpload",
        )

    def test_receiver_config_documents_test_settings_and_endpoints(self):
        config = self.app.receiver_config()

        self.assertEqual(config["db_path"], str(self.app.DB_PATH))
        self.assertEqual(config["upload_interval_minutes"], 1)
        self.assertEqual(config["data_mode"], "Add")
        self.assertEqual(config["child_height_threshold_cm"], 140)
        self.assertEqual(config["camera_endpoints"]["heartbeat"], "/api/camera/heartBeat")
        self.assertEqual(config["debug_endpoints"]["current_status"], "/api/status/current")
        self.assertEqual(config["debug_endpoints"]["child_mode"], "/api/debug/child-mode")
        self.assertEqual(config["debug_endpoints"]["session"], "/api/debug/session")
        self.assertEqual(
            config["debug_endpoints"]["session_reset"], "/api/debug/session-reset"
        )
        self.assertEqual(config["debug_endpoints"]["schema"], "/api/debug/schema")
        self.assertEqual(
            config["debug_endpoints"]["data_catalog"], "/api/debug/data-catalog"
        )
        self.assertEqual(
            config["debug_endpoints"]["integration_proof"],
            "/api/debug/integration-proof",
        )

    def test_child_mode_report_detects_explicit_adult_child_fields(self):
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.upload_payload(),
        )

        report = self.app.child_mode_report()

        self.assertTrue(report["camera_explicit_adult_child_counts_seen"])
        self.assertTrue(report["height_based_child_classification_possible"])
        self.assertEqual(report["explicit_adult_child_totals"]["in_adult"], 2)
        self.assertEqual(report["explicit_adult_child_totals"]["out_adult"], 1)
        self.assertEqual(report["explicit_adult_child_totals"]["in_child"], 1)
        self.assertEqual(report["explicit_adult_child_totals"]["out_child"], 0)
        self.assertEqual(report["explicit_adult_child_totals"]["passby_adult"], 2)
        self.assertEqual(report["explicit_adult_child_totals"]["turnback_adult"], 1)
        self.assertEqual(report["height_summary"]["inferred_adult_events"], 1)
        self.assertIn("camera-provided", report["recommendation"])

    def test_child_mode_report_classifies_from_heights_when_no_explicit_counts(self):
        short_payload = self.attributes_payload(height=120)
        tall_payload = self.attributes_payload(height=171)
        tall_payload["time"] += 60
        tall_payload["startTime"] += 60
        tall_payload["endTime"] += 60
        tall_payload["attributes"][0]["idIndex"] = 178208
        tall_payload["attributes"][0]["personId"] = 178208
        tall_payload["attributes"][0]["timeStamp"] += 60000000

        self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", short_payload)
        self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", tall_payload)

        report = self.app.child_mode_report()

        self.assertFalse(report["camera_explicit_adult_child_counts_seen"])
        self.assertTrue(report["height_based_child_classification_possible"])
        self.assertEqual(report["height_summary"]["rows_with_height"], 2)
        self.assertEqual(report["height_summary"]["inferred_child_events"], 1)
        self.assertEqual(report["height_summary"]["inferred_adult_events"], 1)
        self.assertIn("height-based", report["recommendation"])

    def test_init_db_migrates_existing_count_uploads_columns(self):
        with self.app.db_lock, self.app.sqlite3.connect(self.app.DB_PATH) as conn:
            conn.execute("DROP TABLE count_uploads")
            conn.execute(
                """
                CREATE TABLE count_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at TEXT NOT NULL,
                    client_ip TEXT NOT NULL,
                    sn TEXT NOT NULL,
                    camera_time INTEGER,
                    start_time INTEGER,
                    end_time INTEGER,
                    in_count INTEGER NOT NULL DEFAULT 0,
                    out_count INTEGER NOT NULL DEFAULT 0,
                    passby_count INTEGER NOT NULL DEFAULT 0,
                    turnback_count INTEGER NOT NULL DEFAULT 0,
                    avg_stay_time_ms INTEGER,
                    in_adult INTEGER,
                    out_adult INTEGER,
                    in_child INTEGER,
                    out_child INTEGER,
                    total INTEGER,
                    payload_hash TEXT NOT NULL UNIQUE,
                    raw_request_id INTEGER NOT NULL
                )
                """
            )

        self.app.init_db()
        columns = {column["name"] for column in self.app.table_schema("count_uploads")}

        self.assertIn("passby_adult", columns)
        self.assertIn("passby_child", columns)
        self.assertIn("turnback_adult", columns)
        self.assertIn("turnback_child", columns)

    def test_schema_report_describes_custom_database_schema(self):
        schema = self.app.schema_report()

        self.assertEqual(schema["schema_owner"], "custom_receiver")
        self.assertIn("camera sends JSON", schema["important_note"])
        self.assertIn("raw_requests", schema["tables"])
        self.assertIn("count_uploads", schema["tables"])
        self.assertIn("receiver_sessions", schema["tables"])
        self.assertEqual(schema["source_of_truth"]["raw_json_column"], "payload_json")

    def test_data_catalog_lists_observed_camera_fields_and_storage_mapping(self):
        self.app.record_upload(
            "/api/camera/dataUpload",
            "172.16.17.50",
            self.upload_payload(),
        )

        catalog = self.app.data_catalog()
        upload_fields = {
            field["field"] for field in catalog["field_catalog"]["data_upload"]
        }

        self.assertIsNone(catalog["camera_database_schema"])
        self.assertIn("inAdult", upload_fields)
        self.assertIn("turnbackChild", upload_fields)
        self.assertIn("passbyAdult", catalog["observed_fields"]["upload_records"])
        self.assertEqual(catalog["storage_mapping"]["full_payload"], "raw_requests.payload_json")

    def test_integration_proof_documents_ngrok_and_demo_db(self):
        proof = self.app.integration_proof()

        self.assertIn("validated", proof["result"])
        self.assertIn("hx_camera_demo.db", proof["local_receiver"]["demo_db_command"])
        self.assertEqual(
            proof["camera_configuration"]["data_api"], "/api/camera/dataUpload"
        )
        self.assertEqual(
            proof["ngrok_example"]["public_url_tested"],
            "https://passivism-dimness-gigabyte.ngrok-free.dev",
        )

    def test_receiver_sessions_table_exists(self):
        columns = {column["name"] for column in self.app.table_schema("receiver_sessions")}

        self.assertEqual(
            columns,
            {
                "id",
                "started_at",
                "baseline_upload_id",
                "baseline_raw_request_id",
                "note",
            },
        )

    def test_session_reset_baselines_after_current_uploads(self):
        first = self.attributes_payload(height=160)
        second = self.attributes_payload(height=171)
        second["time"] += 60
        second["startTime"] += 60
        second["endTime"] += 60
        second["in"] = 2
        second["out"] = 1
        second["attributes"][0]["idIndex"] = 178208
        second["attributes"][0]["personId"] = 178208
        second["attributes"][0]["timeStamp"] += 60000000

        self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", first)
        reset = self.app.create_session_reset("camera website cleared")
        self.app.record_upload("/api/camera/dataUpload", "172.16.17.50", second)

        self.assertEqual(reset["session"]["baseline_upload_id"], 1)
        self.assertEqual(reset["session"]["baseline_raw_request_id"], 1)

        status = self.app.current_status()
        self.assertEqual(status["totals"]["in"], 3)
        self.assertEqual(status["totals"]["out"], 1)
        self.assertEqual(status["all_time_totals"]["upload_rows"], 2)
        self.assertEqual(status["session"]["baseline_upload_id"], 1)
        self.assertEqual(status["session_totals"]["upload_rows"], 1)
        self.assertEqual(status["session_totals"]["in"], 2)
        self.assertEqual(status["session_totals"]["out"], 1)
        self.assertEqual(status["session_totals"]["estimated_onboard"], 1)

    def test_session_report_shows_all_time_and_session_windows(self):
        self.app.record_upload(
            "/api/camera/dataUpload", "172.16.17.50", self.attributes_payload()
        )
        self.app.create_session_reset()

        report = self.app.session_report()

        self.assertEqual(report["all_time_totals"]["upload_rows"], 1)
        self.assertEqual(report["session_totals"]["upload_rows"], 0)
        self.assertEqual(report["active_session"]["baseline_upload_id"], 1)
        self.assertEqual(len(report["recent_upload_windows"]), 1)
        self.assertIn("session_totals", report["comparison_note"])


if __name__ == "__main__":
    unittest.main()
