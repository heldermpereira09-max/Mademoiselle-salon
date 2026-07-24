import re
from decimal import Decimal

from .models.models import Customer


def normalize_phone(phone):
    """Return a stable lookup key without making validation stricter."""
    value = (phone or "").strip()
    digits = re.sub(r"\D", "", value)

    if value.startswith("+"):
        return f"+{digits}"
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if len(digits) == 9:
        return f"+351{digits}"
    return digits


def resolve_customer(name, email, phone, language=None):
    normalized_phone = normalize_phone(phone)
    customer = Customer.query.filter_by(
        phone_normalized=normalized_phone
    ).one_or_none()

    if customer is None:
        return Customer(
            name=name,
            email=email or None,
            phone=phone,
            phone_normalized=normalized_phone,
            preferred_language=language,
            marketing_consent=False,
            total_bookings=0,
            total_spent=Decimal("0.00"),
            loyalty_points=0,
            loyalty_level="STANDARD",
        )

    if customer.name != name:
        customer.name = name
    if email and customer.email != email:
        customer.email = email
    if customer.phone != phone:
        customer.phone = phone
    if language and customer.preferred_language != language:
        customer.preferred_language = language

    return customer


def record_customer_booking(customer, booking):
    """Update CRM aggregates from the booking's historical price snapshot."""
    if booking.service_price is None:
        raise ValueError("Booking.service_price is required for CRM totals")

    customer.total_bookings = (customer.total_bookings or 0) + 1
    customer.total_spent = (
        Decimal(customer.total_spent or 0)
        + Decimal(booking.service_price)
    )

    appointment_date = booking.appointment_date
    if customer.first_visit is None or appointment_date < customer.first_visit:
        customer.first_visit = appointment_date
    if customer.last_visit is None or appointment_date > customer.last_visit:
        customer.last_visit = appointment_date


def refresh_customer_booking_metrics(customer):
    """Recalcula agregados após editar uma marcação existente."""
    if customer is None:
        return

    bookings = list(customer.bookings)
    customer.total_bookings = len(bookings)
    customer.total_spent = sum(
        (
            Decimal(booking.service_price)
            for booking in bookings
            if booking.service_price is not None
        ),
        Decimal("0.00"),
    )
    customer.first_visit = min(
        (booking.appointment_date for booking in bookings),
        default=None,
    )
    customer.last_visit = max(
        (booking.appointment_date for booking in bookings),
        default=None,
    )
