import os
import tempfile
import unittest

import database.sqlite_db as sqlite_db_module
from database.sqlite_db import SQLiteDatabase
from services.customer_support_service import CustomerSupportService


class CustomerToolsTests(unittest.TestCase):
    def setUp(self):
        sqlite_db_module._instance = None
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="wisdomsystem-customer-tools-",
            ignore_cleanup_errors=True,
        )
        self.db = SQLiteDatabase(db_path=os.path.join(self.temp_dir.name, "memory.db"))
        self.db.create_user(
            user_id="user_1",
            username="alice",
            password_hash="hash",
            role="user",
            display_name="Alice",
            is_active=True,
        )
        self.db.create_user(
            user_id="user_2",
            username="bob",
            password_hash="hash",
            role="user",
            display_name="Bob",
            is_active=True,
        )
        self.db.upsert_customer_device(
            device_id="device_1",
            user_id="user_1",
            product_name="Wisdom Sweeper X1",
            model="X1",
            serial_number="SN-001",
            status="online",
            purchase_date="2026-01-01",
            warranty_expires_at="2028-01-01",
            is_default=True,
        )
        self.db.upsert_customer_device(
            device_id="device_2",
            user_id="user_2",
            product_name="Wisdom Sweeper Z9",
            model="Z9",
            serial_number="SN-002",
            status="offline",
            purchase_date="2026-02-01",
            warranty_expires_at="2028-02-01",
            is_default=True,
        )
        self.db.upsert_device_consumable(
            record_id="consumable_1",
            device_id="device_1",
            consumable_type="main_brush",
            status="warning",
            remaining_percent=12,
            remaining_days=7,
            maintenance_tip="Replace soon.",
        )

        from agent.tools import customer_tools

        customer_tools.customer_support_service = CustomerSupportService(db=self.db)

    def tearDown(self):
        sqlite_db_module._instance = None
        self.temp_dir.cleanup()

    def test_lookup_user_devices_uses_current_user_scope_and_collects_sources(self):
        from agent.tools.customer_tools import lookup_user_devices
        from agent.tools.runtime import get_source_references, reset_request_context, start_request_context

        token = start_request_context(user_id="user_1", session_id="session_1")
        try:
            result = lookup_user_devices.invoke({})
            sources = get_source_references()
        finally:
            reset_request_context(token)

        self.assertIn("Wisdom Sweeper X1", result)
        self.assertNotIn("Wisdom Sweeper Z9", result)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_type"], "business_tool")
        self.assertEqual(sources[0]["tool_name"], "lookup_user_devices")

    def test_lookup_device_consumables_returns_device_specific_data(self):
        from agent.tools.customer_tools import lookup_device_consumables
        from agent.tools.runtime import reset_request_context, start_request_context

        token = start_request_context(user_id="user_1", session_id="session_1")
        try:
            result = lookup_device_consumables.invoke({"device_id": ""})
        finally:
            reset_request_context(token)

        self.assertIn("main_brush", result)
        self.assertIn("Replace soon.", result)

    def test_missing_request_context_creates_failed_audit_log(self):
        from agent.tools.customer_tools import lookup_user_devices

        with self.assertRaises(RuntimeError):
            lookup_user_devices.invoke({})

        audit_logs = self.db.list_tool_audit_logs()
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs[0]["tool_name"], "lookup_user_devices")
        self.assertEqual(audit_logs[0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
