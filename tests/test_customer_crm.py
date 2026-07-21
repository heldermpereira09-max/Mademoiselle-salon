from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from salon.app import db
from salon.models.models import Booking, Customer, Salon, Service, ServiceCategory


def _next_weekday():
    days_until_tuesday = (1 - date.today().weekday()) % 7
    return date.today() + timedelta(days=days_until_tuesday or 7)


def _create_catalog():
    salon = Salon(name="Test Salon", slug="lagos")
    category = ServiceCategory(
        salon=salon,
        name_pt="Teste",
        name_en="Test",
    )
    service = Service(
        category=category,
        name_pt="Serviço",
        name_en="Service",
        duration_minutes=30,
        price=25.50,
        active=True,
    )
    db.session.add_all([salon, category, service])
    db.session.commit()
    return salon, service


def test_new_booking_stores_historical_price_and_updates_customer_total(app, client):
    with app.app_context():
        salon, service = _create_catalog()
        salon_slug = salon.slug
        service_id = service.id

    with client.session_transaction() as session:
        session["salon_slug"] = salon_slug
        session["lang"] = "pt"

    with (
        patch("salon.routes.get_calendar_events", return_value=[]),
        patch(
            "salon.routes.create_calendar_event",
            return_value="test-event-id",
        ),
        patch("salon.routes.send_confirmation_email", return_value=True),
    ):
        response = client.post(
            "/book",
            data={
                "client_name": "Ana Silva",
                "client_email": "ana@example.com",
                "client_phone": "912 345 678",
                "service_id": str(service_id),
                "appointment_date": _next_weekday().isoformat(),
                "appointment_time": "10:00",
                "notes": "",
            },
        )

    assert response.status_code == 302

    with app.app_context():
        booking = Booking.query.one()
        customer = Customer.query.one()
        assert booking.service_price == Decimal("25.50")
        assert customer.total_spent == booking.service_price
        assert customer.total_bookings == 1


def test_service_price_change_does_not_change_historical_total(app, client):
    test_new_booking_stores_historical_price_and_updates_customer_total(app, client)

    with app.app_context():
        booking = Booking.query.one()
        original_booking_price = booking.service_price
        original_total = booking.customer.total_spent

        booking.service.price = 999.00
        db.session.commit()
        db.session.expire_all()

        booking = Booking.query.one()
        customer = Customer.query.one()
        assert booking.service_price == original_booking_price
        assert customer.total_spent == original_total
        assert customer.total_spent == booking.service_price
