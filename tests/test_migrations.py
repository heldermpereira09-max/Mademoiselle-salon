from decimal import Decimal

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from salon.app import create_app, db


def test_crm_migration_backfills_without_losing_bookings(tmp_path):
    database_path = tmp_path / "legacy.db"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
    })
    config = Config("migrations/alembic.ini")

    with app.app_context():
        command.upgrade(config, "20260720_01")
        engine = db.engine

        legacy_booking = {
            "id": 1,
            "client_name": "Legacy Client",
            "client_email": "legacy@example.com",
            "client_phone": "+351 912 345 678",
            "salon_id": 1,
            "service_id": 1,
            "appointment_date": "2025-05-20",
            "appointment_time": "11:30:00.000000",
            "notes": "Keep this note",
            "status": "pending",
            "created_at": "2025-01-01 12:00:00.000000",
            "outlook_event_id": "existing-event-id",
        }

        with engine.begin() as connection:
            connection.execute(sa.text(
                "INSERT INTO salons (id, name, slug) "
                "VALUES (1, 'Legacy Salon', 'legacy-salon')"
            ))
            connection.execute(sa.text(
                "INSERT INTO service_categories "
                "(id, salon_id, name_pt, name_en) "
                "VALUES (1, 1, 'Categoria', 'Category')"
            ))
            connection.execute(sa.text(
                "INSERT INTO services "
                "(id, name_pt, name_en, price, category_id, active) "
                "VALUES (1, 'Serviço', 'Service', 42.75, 1, 1)"
            ))
            connection.execute(
                sa.text(
                    "INSERT INTO bookings "
                    "(id, client_name, client_email, client_phone, salon_id, "
                    "service_id, appointment_date, appointment_time, notes, "
                    "status, created_at, outlook_event_id) "
                    "VALUES (:id, :client_name, :client_email, :client_phone, "
                    ":salon_id, :service_id, :appointment_date, "
                    ":appointment_time, :notes, :status, :created_at, "
                    ":outlook_event_id)"
                ),
                legacy_booking,
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            booking = connection.execute(sa.text(
                "SELECT * FROM bookings WHERE id = 1"
            )).mappings().one()
            customer = connection.execute(sa.text(
                "SELECT * FROM customers"
            )).mappings().one()
            count = connection.execute(sa.text(
                "SELECT COUNT(*) FROM bookings"
            )).scalar_one()

        assert count == 1
        for field in (
            "client_name",
            "client_email",
            "client_phone",
            "notes",
            "status",
            "outlook_event_id",
        ):
            assert booking[field] == legacy_booking[field]
        assert Decimal(str(booking["service_price"])) == Decimal("42.75")
        assert booking["customer_id"] == customer["id"]
        assert customer["total_bookings"] == 1
        assert Decimal(str(customer["total_spent"])) == Decimal("42.75")
