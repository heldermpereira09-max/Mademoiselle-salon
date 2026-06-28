import unittest
from types import SimpleNamespace

from salon.routes import build_make_payload


class MakeWebhookPayloadTests(unittest.TestCase):
    def test_build_make_payload_includes_booking_fields(self):
        booking = SimpleNamespace(
            client_name="Ana Silva",
            client_email="ana@example.com",
            client_phone="912345678",
            notes="Preferência por horário da manhã",
            appointment_date="2026-07-15",
            appointment_time="14:30",
            service=SimpleNamespace(name_pt="Manicure", duration_minutes=60, price=25.0),
        )

        payload = build_make_payload(booking)

        self.assertEqual(payload["service"], "Manicure")
        self.assertEqual(payload["date"], "2026-07-15")
        self.assertEqual(payload["time"], "14:30")
        self.assertEqual(payload["duration"], 60)
        self.assertEqual(payload["price"], 25.0)
        self.assertEqual(payload["client"], "Ana Silva")
        self.assertEqual(payload["email"], "ana@example.com")
        self.assertEqual(payload["phone"], "912345678")
        self.assertEqual(payload["notes"], "Preferência por horário da manhã")
        self.assertEqual(payload["start_datetime"], "2026-07-15T14:30:00")
        self.assertEqual(payload["end_datetime"], "2026-07-15T15:30:00")


if __name__ == "__main__":
    unittest.main()
