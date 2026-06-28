import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, has_request_context
from flask_babel import gettext as _, get_locale
from .app import db
from .models import ServiceCategory, Service, Booking
from datetime import datetime, date, timedelta

main = Blueprint("main", __name__)
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/i8usajk6gi1jvi2cyo02h2ylwptwqabi"


def _get_service_name(service, lang=None):
    if not service:
        return ""

    if hasattr(service, "name"):
        try:
            return service.name(lang or "pt")
        except TypeError:
            return service.name()

    if lang == "en":
        return getattr(service, "name_en", "") or getattr(service, "name_pt", "")

    return getattr(service, "name_pt", "") or getattr(service, "name_en", "")


def _format_booking_date(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d")


def _format_booking_time(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%H:%M")


def build_make_payload(booking):
    service = booking.service if getattr(booking, "service", None) is not None else Service.query.get(booking.service_id)
    return {
        "service": _get_service_name(service, get_lang() if has_request_context() else "pt"),
        "date": _format_booking_date(booking.appointment_date),
        "time": _format_booking_time(booking.appointment_time),
        "duration": service.duration_minutes if service else None,
        "price": service.price if service else None,
        "client": booking.client_name,
        "email": booking.client_email,
        "phone": booking.client_phone,
        "notes": booking.notes or "",
    }


def send_make_webhook(booking):
    payload = build_make_payload(booking)
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        MAKE_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=10) as response:
            return response.status
    except (urllib_error.URLError, TimeoutError, ValueError) as exc:
        current_app.logger.exception("Failed to send booking webhook for booking %s: %s", booking.id, exc)
        return None


def get_lang():
    return str(get_locale())


@main.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ["pt", "en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))


@main.route("/")
def index():
    categories = ServiceCategory.query.order_by(ServiceCategory.display_order).all()
    return render_template("index.html", categories=categories, lang=get_lang())


@main.route("/services")
def services():
    categories = ServiceCategory.query.order_by(ServiceCategory.display_order).all()
    return render_template("services.html", categories=categories, lang=get_lang())


@main.route("/book", methods=["GET", "POST"])
def book():
    categories = ServiceCategory.query.order_by(ServiceCategory.display_order).all()
    service_id = request.args.get("service_id", type=int)
    selected_service = Service.query.get(service_id) if service_id else None

    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        client_phone = request.form.get("client_phone", "").strip()
        service_id = request.form.get("service_id", type=int)
        appt_date_str = request.form.get("appointment_date", "").strip()
        appt_time_str = request.form.get("appointment_time", "").strip()
        notes = request.form.get("notes", "").strip()

        errors = []
        if not client_name:
            errors.append(_("Name is required."))
        if not client_phone:
            errors.append(_("Phone is required."))   
        if not service_id:
            errors.append(_("Please select a service."))
        if not appt_date_str:
            errors.append(_("Please select a date."))
        if not appt_time_str:
            errors.append(_("Please select a time."))

        appt_date = None
        appt_time = None
        if appt_date_str:
            try:
                appt_date = datetime.strptime(appt_date_str, "%Y-%m-%d").date()
                if appt_date < date.today():
                    errors.append(_("Please select a future date."))
            except ValueError:
                errors.append(_("Invalid date format."))
        if appt_time_str:
            try:
                appt_time = datetime.strptime(appt_time_str, "%H:%M").time()
            except ValueError:
                errors.append(_("Invalid time format."))

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "book.html",
                categories=categories,
                selected_service=Service.query.get(service_id) if service_id else None,
                lang=get_lang(),
                form_data=request.form,
                today=date.today().isoformat(),
            )

        booking = Booking(
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            service_id=service_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            notes=notes,
            status="pending",
        )
        db.session.add(booking)
        db.session.commit()
        send_make_webhook(booking)

        flash(
            _("Your appointment has been booked successfully! We've sent you a confirmation email with all the details of your appointment."),
            "success",
        )
        return redirect(url_for("main.booking_success", booking_id=booking.id))

    return render_template(
        "book.html",
        categories=categories,
        selected_service=selected_service,
        lang=get_lang(),
        form_data={},
        today=date.today().isoformat(),
    )


@main.route("/booking-success/<int:booking_id>")
def booking_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template("booking_success.html", booking=booking, lang=get_lang())


@main.route("/api/services")
def api_services():
    lang = get_lang()
    categories = ServiceCategory.query.order_by(ServiceCategory.display_order).all()
    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name(lang),
            "services": [
                {
                    "id": s.id,
                    "name": s.name(lang),
                    "description": s.description(lang),
                    "duration_minutes": s.duration_minutes,
                    "price": s.price,
                }
                for s in cat.services if s.active
            ],
        })
    return jsonify(result)


@main.route("/api/available-times")
def api_available_times():
    date_str = request.args.get("date")
    service_id = request.args.get("service_id", type=int)
    if not date_str or not service_id:
        return jsonify([])

    try:
        appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify([])

    if appt_date < date.today():
        return jsonify([])

    service = Service.query.get(service_id)
    if not service:
        return jsonify([])

    existing = Booking.query.filter_by(appointment_date=appt_date).all()
    booked_times = set()
    for b in existing:
        start = datetime.combine(appt_date, b.appointment_time)
        end = start + timedelta(minutes=b.service.duration_minutes)
        t = start
        while t < end:
            booked_times.add(t.strftime("%H:%M"))
            t += timedelta(minutes=30)

    slots = []
    start_hour = 9
    end_hour = 19
    t = datetime.combine(appt_date, datetime.min.time().replace(hour=start_hour))
    end = datetime.combine(appt_date, datetime.min.time().replace(hour=end_hour))

    while t + timedelta(minutes=service.duration_minutes) <= end:
        slot_str = t.strftime("%H:%M")
        if slot_str not in booked_times:
            slots.append(slot_str)
        t += timedelta(minutes=30)

    return jsonify(slots)


@main.route("/contact")
def contact():
    return render_template("contact.html", lang=get_lang())
