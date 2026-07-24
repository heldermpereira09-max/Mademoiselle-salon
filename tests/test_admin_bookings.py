from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest

from salon.app import db
from salon.graph import GraphError
from salon.models.models import (
    AdminUser,
    Booking,
    Salon,
    Service,
    ServiceCategory,
)


def _authenticate(client):
    admin_user = AdminUser(
        name="Admin Marcações",
        email="bookings-admin@example.com",
        is_active=True,
    )
    admin_user.set_password("correct-password")
    db.session.add(admin_user)
    db.session.commit()

    with client.session_transaction() as flask_session:
        flask_session["admin_user_id"] = admin_user.id


def _create_catalog():
    salon = Salon(name="Lagos", slug="lagos")
    category = ServiceCategory(
        salon=salon,
        name_pt="Manicure",
        name_en="Manicure",
    )
    service = Service(
        category=category,
        name_pt="Manicure Completa",
        name_en="Complete Manicure",
        duration_minutes=30,
        price=25.00,
        active=True,
    )
    db.session.add_all([salon, category, service])
    db.session.commit()
    return salon, service


def _create_booking(
    salon,
    service,
    name,
    appointment_date,
    appointment_time=time(10, 0),
    phone="912 345 678",
    email="cliente@example.com",
    outlook_event_id="test-event-id",
):
    booking = Booking(
        salon=salon,
        service=service,
        service_price=Decimal("25.00"),
        client_name=name,
        client_phone=phone,
        client_email=email,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status="confirmed",
        outlook_event_id=outlook_event_id,
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def _next_lagos_booking_date():
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()
    days_until_tuesday = (1 - today.weekday()) % 7
    return today + timedelta(days=days_until_tuesday or 7)


def _valid_edit_data(service_id, appointment_date, appointment_time="10:00"):
    return {
        "service_id": str(service_id),
        "appointment_date": appointment_date.isoformat(),
        "appointment_time": appointment_time,
        "notes": "Observações alteradas",
    }


def test_bookings_page_requires_authentication(client):
    response = client.get("/admin/bookings")

    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


@pytest.mark.parametrize(
    ("query", "matching_name"),
    [
        ("Maria Especial", "Maria Especial"),
        ("969 111 222", "Cliente Telefone"),
        ("email-unico@example.com", "Cliente Email"),
    ],
)
def test_bookings_searches_name_phone_and_email(
    app,
    client,
    query,
    matching_name,
):
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        _create_booking(salon, service, "Maria Especial", today)
        _create_booking(
            salon,
            service,
            "Cliente Telefone",
            today,
            phone="969 111 222",
        )
        _create_booking(
            salon,
            service,
            "Cliente Email",
            today,
            email="email-unico@example.com",
        )

    response = client.get(
        "/admin/bookings",
        query_string={"period": "all", "q": query},
    )
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert matching_name in content


def test_bookings_date_filters(app, client):
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()
    tomorrow = today + timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    next_week = week_start + timedelta(days=7)

    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        _create_booking(salon, service, "Cliente Hoje", today)
        _create_booking(salon, service, "Cliente Amanhã", tomorrow)
        _create_booking(salon, service, "Cliente Próxima Semana", next_week)

    today_content = client.get(
        "/admin/bookings?period=today"
    ).get_data(as_text=True)
    tomorrow_content = client.get(
        "/admin/bookings?period=tomorrow"
    ).get_data(as_text=True)
    week_content = client.get(
        "/admin/bookings?period=week"
    ).get_data(as_text=True)
    all_content = client.get(
        "/admin/bookings?period=all"
    ).get_data(as_text=True)

    assert "Cliente Hoje" in today_content
    assert "Cliente Amanhã" not in today_content
    assert "Cliente Amanhã" in tomorrow_content
    assert "Cliente Hoje" not in tomorrow_content
    assert "Cliente Hoje" in week_content
    assert "Cliente Próxima Semana" not in week_content
    assert "Cliente Próxima Semana" in all_content


def test_bookings_are_paginated(app, client):
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()

    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        for index in range(21):
            _create_booking(
                salon,
                service,
                f"Cliente {index:02d}",
                today + timedelta(days=index),
            )

    first_page = client.get(
        "/admin/bookings?period=all&page=1"
    ).get_data(as_text=True)
    second_page = client.get(
        "/admin/bookings?period=all&page=2"
    ).get_data(as_text=True)

    assert "Cliente 00" in first_page
    assert "Cliente 20" not in first_page
    assert "Cliente 20" in second_page
    assert "Cliente 00" not in second_page


def test_dashboard_shows_today_booking_count(app, client):
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()

    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        _create_booking(salon, service, "Cliente Um", today)
        _create_booking(salon, service, "Cliente Dois", today)
        _create_booking(
            salon,
            service,
            "Cliente Amanhã",
            today + timedelta(days=1),
        )

    response = client.get("/admin/")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-testid="bookings-today-count">2<' in content
    assert "/admin/bookings" in content


def test_booking_edit_requires_authentication(app, client):
    with app.app_context():
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Protegido",
            _next_lagos_booking_date(),
        )
        booking_id = booking.id

    response = client.get(f"/admin/bookings/{booking_id}/edit")

    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_booking_edit_get_shows_current_data(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Atual",
            appointment_date,
            email="atual@example.com",
        )
        booking_id = booking.id
        service_name = service.name_pt

    response = client.get(f"/admin/bookings/{booking_id}/edit")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Cliente Atual" in content
    assert "atual@example.com" in content
    assert service_name in content
    assert appointment_date.isoformat() in content


def test_booking_edit_missing_booking_returns_404(app, client):
    with app.app_context():
        _authenticate(client)

    response = client.get("/admin/bookings/999999/edit")

    assert response.status_code == 404


def test_booking_edit_rejects_service_from_another_salon(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon, service, "Cliente Serviço", appointment_date
        )
        other_salon = Salon(name="Praia da Luz", slug="praia-da-luz")
        other_category = ServiceCategory(
            salon=other_salon,
            name_pt="Outro",
            name_en="Other",
        )
        other_service = Service(
            category=other_category,
            name_pt="Serviço de Outro Salão",
            name_en="Other Salon Service",
            duration_minutes=30,
            price=30,
            active=True,
        )
        db.session.add_all([other_salon, other_category, other_service])
        db.session.commit()
        booking_id = booking.id
        other_service_id = other_service.id

    response = client.post(
        f"/admin/bookings/{booking_id}/edit",
        data={
            "service_id": str(other_service_id),
            "appointment_date": appointment_date.isoformat(),
            "appointment_time": "10:00",
            "notes": "",
        },
    )

    assert response.status_code == 200
    assert "serviço válido deste salão" in response.get_data(as_text=True)


def test_booking_edit_rejects_invalid_date_and_time(app, client):
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Inválido",
            _next_lagos_booking_date(),
        )
        booking_id = booking.id
        service_id = service.id

    response = client.post(
        f"/admin/bookings/{booking_id}/edit",
        data={
            "service_id": str(service_id),
            "appointment_date": "data-invalida",
            "appointment_time": "hora-invalida",
            "notes": "",
        },
    )
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Introduza uma data válida." in content
    assert "Introduza uma hora válida." in content


def test_booking_edit_rejects_conflict_with_another_booking(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Editado",
            appointment_date,
            appointment_time=time(9, 0),
        )
        _create_booking(
            salon,
            service,
            "Cliente Conflito",
            appointment_date,
            appointment_time=time(10, 0),
        )
        booking_id = booking.id
        service_id = service.id

    response = client.post(
        f"/admin/bookings/{booking_id}/edit",
        data=_valid_edit_data(service_id, appointment_date),
    )

    assert response.status_code == 200
    assert "já não está disponível" in response.get_data(as_text=True)


def test_booking_edit_does_not_conflict_with_itself(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Sem Falso Conflito",
            appointment_date,
        )
        booking_id = booking.id
        service_id = service.id

    with (
        patch("salon.admin.routes.get_calendar_events", return_value=[]),
        patch(
            "salon.admin.routes.update_calendar_event",
            return_value=True,
        ),
        patch(
            "salon.admin.routes.send_booking_updated_email",
            return_value=True,
        ),
    ):
        response = client.post(
            f"/admin/bookings/{booking_id}/edit",
            data=_valid_edit_data(service_id, appointment_date),
        )

    assert response.status_code == 302


def test_valid_booking_edit_updates_database_graph_and_email(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        new_service = Service(
            category=service.category,
            name_pt="Novo Serviço",
            name_en="New Service",
            duration_minutes=45,
            price=35,
            active=True,
        )
        db.session.add(new_service)
        booking = _create_booking(
            salon,
            service,
            "Cliente Alterado",
            appointment_date,
            appointment_time=time(9, 0),
        )
        db.session.add(new_service)
        db.session.commit()
        booking_id = booking.id
        new_service_id = new_service.id

    with (
        patch(
            "salon.admin.routes.get_calendar_events",
            return_value=[],
        ) as calendar_mock,
        patch(
            "salon.admin.routes.update_calendar_event",
            return_value=True,
        ) as update_mock,
        patch(
            "salon.admin.routes.send_booking_updated_email",
            return_value=True,
        ) as email_mock,
    ):
        response = client.post(
            f"/admin/bookings/{booking_id}/edit",
            data={
                "service_id": str(new_service_id),
                "appointment_date": appointment_date.isoformat(),
                "appointment_time": "11:00",
                "notes": "Nova nota",
            },
        )

    assert response.status_code == 302
    calendar_mock.assert_called_once_with(
        appointment_date,
        exclude_event_id="test-event-id",
    )
    update_mock.assert_called_once()
    assert update_mock.call_args.kwargs["event_id"] == "test-event-id"
    email_mock.assert_called_once()

    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.service_id == new_service_id
        assert booking.service_price == Decimal("35.00")
        assert booking.appointment_time == time(11, 0)
        assert booking.notes == "Nova nota"


def test_graph_failure_does_not_update_database(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Graph",
            appointment_date,
            appointment_time=time(9, 0),
        )
        booking_id = booking.id
        service_id = service.id

    with (
        patch("salon.admin.routes.get_calendar_events", return_value=[]),
        patch(
            "salon.admin.routes.update_calendar_event",
            side_effect=GraphError("Graph indisponível"),
        ),
    ):
        response = client.post(
            f"/admin/bookings/{booking_id}/edit",
            data=_valid_edit_data(
                service_id,
                appointment_date,
                appointment_time="11:00",
            ),
        )

    assert response.status_code == 200
    assert "não foi alterada" in response.get_data(as_text=True)
    with app.app_context():
        booking = db.session.get(Booking, booking_id)
        assert booking.appointment_time == time(9, 0)


def test_booking_without_email_can_be_edited(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Sem Email",
            appointment_date,
            appointment_time=time(9, 0),
            email=None,
        )
        booking_id = booking.id
        service_id = service.id

    with (
        patch("salon.admin.routes.get_calendar_events", return_value=[]),
        patch("salon.admin.routes.update_calendar_event", return_value=True),
        patch(
            "salon.admin.routes.send_booking_updated_email"
        ) as email_mock,
    ):
        response = client.post(
            f"/admin/bookings/{booking_id}/edit",
            data=_valid_edit_data(
                service_id,
                appointment_date,
                appointment_time="11:00",
            ),
        )

    assert response.status_code == 302
    email_mock.assert_not_called()


def test_booking_list_has_edit_link(app, client):
    appointment_date = _next_lagos_booking_date()
    with app.app_context():
        _authenticate(client)
        salon, service = _create_catalog()
        booking = _create_booking(
            salon,
            service,
            "Cliente Botão",
            appointment_date,
        )
        booking_id = booking.id

    response = client.get("/admin/bookings?period=all")
    content = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f"/admin/bookings/{booking_id}/edit" in content
    assert 'data-action="edit"' in content
