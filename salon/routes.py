from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from email.message import EmailMessage
import os
import smtplib
from .app import db
from .graph import (
    GraphError,
    create_calendar_event,
    get_calendar_events,
    send_confirmation_email,
)
from .models.models import Salon, ServiceCategory, Service, Booking
from .customer_service import record_customer_booking, resolve_customer
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

main = Blueprint("main", __name__)


BOOKING_WINDOWS = {
    "lagos": {
        1: [("09:00", "13:00")],
        2: [("14:00", "19:00")],
        3: [("09:00", "13:00")],
        4: [("09:00", "13:00")],
    },
    "praia-da-luz": {
        0: [("09:00", "19:00")],
        1: [("14:00", "19:00")],
        2: [("09:00", "13:00")],
        3: [("14:00", "19:00")],
        4: [("14:00", "19:00")],
    },
}


def get_booking_windows(salon_slug, appointment_date):
    """Períodos permitidos apenas para as marcações online."""

    configured = BOOKING_WINDOWS.get(
        salon_slug,
        {},
    ).get(
        appointment_date.weekday(),
        [],
    )

    windows = []

    for start_text, end_text in configured:
        start_time = datetime.strptime(
            start_text,
            "%H:%M",
        ).time()

        end_time = datetime.strptime(
            end_text,
            "%H:%M",
        ).time()

        windows.append((
            datetime.combine(appointment_date, start_time),
            datetime.combine(appointment_date, end_time),
        ))

    return windows


def get_lang():
    return session.get("lang", "pt")


def get_selected_salon():
    slug = session.get("salon_slug")

    if not slug:
        return None

    return Salon.query.filter_by(slug=slug).first()


def send_feedback_email(
    rating,
    comment,
    salon_name,
    language,
    submitted_at,
    remote_addr,
    user_agent,
):
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = int(os.environ.get("MAIL_PORT", "587"))
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    recipient = os.environ.get("FEEDBACK_RECIPIENT")

    if not all([
        mail_server,
        mail_username,
        mail_password,
        recipient,
    ]):
        raise RuntimeError("Website feedback email settings are incomplete.")

    message = EmailMessage()
    message["Subject"] = "⭐ Nova avaliação do website Mademoiselle"
    message["From"] = mail_username
    message["To"] = recipient
    message.set_content(
        "\n".join([
            "New Mademoiselle website feedback",
            "",
            f"Rating: {rating}/5",
            f"Comment: {comment or 'No comment provided'}",
            f"Salon: {salon_name or 'Not selected'}",
            f"Language: {language}",
            f"Submitted at: {submitted_at.isoformat()}",
            f"IP address: {remote_addr or 'Unavailable'}",
            f"User agent: {user_agent or 'Unavailable'}",
        ])
    )

    with smtplib.SMTP(mail_server, mail_port, timeout=10) as smtp:
        smtp.ehlo()

        if mail_use_tls:
            smtp.starttls()
            smtp.ehlo()

        smtp.login(mail_username, mail_password)
        smtp.send_message(message)


@main.route("/website-feedback", methods=["POST"])
def website_feedback():
    language = request.form.get("language", "").strip()

    if language not in ["pt", "en"]:
        language = get_lang()

    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()
    salon = get_selected_salon()
    submitted_at = datetime.now(ZoneInfo("Europe/Lisbon"))

    if rating not in range(1, 6):
        return jsonify({
            "success": False,
            "message": (
                "Selecione uma avaliação de 1 a 5."
                if language == "pt"
                else "Please select a rating from 1 to 5."
            ),
        }), 400

    try:
        send_feedback_email(
            rating=rating,
            comment=comment,
            salon_name=salon.name if salon else None,
            language=language,
            submitted_at=submitted_at,
            remote_addr=request.remote_addr,
            user_agent=request.user_agent.string,
        )
    except Exception as error:
        print("Erro ao enviar feedback do website:", error)

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível enviar a sua avaliação. Tente novamente."
                if language == "pt"
                else "We could not send your feedback. Please try again."
            ),
        }), 502

    return jsonify({
        "success": True,
        "message": (
            "Obrigada pela sua opinião!"
            if language == "pt"
            else "Thank you for your feedback!"
        ),
    })


@main.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ["pt", "en"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))


@main.route("/set-salon/<slug>")
def set_salon(slug):
    salon = Salon.query.filter_by(slug=slug).first_or_404()
    session["salon_slug"] = salon.slug

    next_page = request.args.get("next")

    if next_page and next_page.startswith("/"):
        return redirect(next_page)

    return redirect(url_for("main.index"))

@main.route("/welcome", methods=["GET", "POST"])
def welcome():
    salons = Salon.query.order_by(Salon.name).all()

    if request.method == "POST":
        lang = request.form.get("lang")
        salon_slug = request.form.get("salon_slug")

        if lang not in ["pt", "en"]:
            flash("Please select a language.", "danger")
            return render_template(
                "welcome.html",
                salons=salons,
                lang="pt",
            )

        salon = Salon.query.filter_by(slug=salon_slug).first()

        if not salon:
            flash(
                "Selecione uma localização válida."
                if lang == "pt"
                else "Please select a valid location.",
                "danger",
            )

            return render_template(
                "welcome.html",
                salons=salons,
                lang=lang,
            )

        session["lang"] = lang
        session["salon_slug"] = salon.slug

        return redirect(url_for("main.index"))

    return render_template(
        "welcome.html",
        salons=salons,
        lang=session.get("lang", "pt"),
    )

@main.route("/")
def index():
    salon = get_selected_salon()
    lang = session.get("lang")

    if not salon or lang not in ["pt", "en"]:
        return redirect(url_for("main.welcome"))

    salons = Salon.query.order_by(Salon.name).all()

    categories = (
        ServiceCategory.query
        .filter_by(salon_id=salon.id)
        .order_by(ServiceCategory.display_order)
        .all()
    )

    return render_template(
        "index.html",
        salons=salons,
        salon=salon,
        categories=categories,
        lang=lang,
    )


@main.route("/services")
def services():
    salon = get_selected_salon()

    if not salon:
        return redirect(
            url_for(
                "main.welcome",
                next=request.path
            )
        )

    salons = Salon.query.order_by(Salon.name).all()

    categories = (
        ServiceCategory.query
        .filter_by(salon_id=salon.id)
        .order_by(ServiceCategory.display_order)
        .all()
    )

    return render_template(
        "services.html",
        salons=salons,
        salon=salon,
        categories=categories,
        lang=get_lang(),
    )

@main.route("/book", methods=["GET", "POST"])
def book():

    salon = get_selected_salon()

    if not salon:
        return redirect(
            url_for(
                "main.welcome",
                next=request.path
            )
        )

    categories = (
        ServiceCategory.query
        .filter_by(salon_id=salon.id)
        .order_by(ServiceCategory.display_order)
        .all()
    )

    service_id = request.args.get("service_id", type=int)

    selected_service = None

    if service_id:
        selected_service = (
            Service.query
            .join(ServiceCategory)
            .filter(
                Service.id == service_id,
                ServiceCategory.salon_id == salon.id
            )
            .first()
        )

    if request.method == "POST":

        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        client_phone = request.form.get("client_phone", "").strip()

        service_id = request.form.get("service_id", type=int)

        appt_date_str = request.form.get("appointment_date", "").strip()
        appt_time_str = request.form.get("appointment_time", "").strip()

        notes = request.form.get("notes", "").strip()
        lang = get_lang()

        service = (
            Service.query
            .join(ServiceCategory)
            .filter(
                Service.id == service_id,
                ServiceCategory.salon_id == salon.id,
                Service.active.is_(True),
            )
            .first()
        )

        errors = []

        if not client_name:
            errors.append("Name is required.")

        if not client_phone:
            errors.append("Phone is required.")

        if not service:
            errors.append(
                "Selecione um serviço válido e ativo."
                if lang == "pt"
                else "Please select a valid, active service."
            )

        if not appt_date_str:
            errors.append("Please select a date.")

        if not appt_time_str:
            errors.append("Please select a time.")

        appt_date = None
        appt_time = None

        if appt_date_str:
            try:
                appt_date = datetime.strptime(
                    appt_date_str,
                    "%Y-%m-%d"
                ).date()

                if appt_date < date.today():
                    errors.append("Please select a future date.")

            except ValueError:
                errors.append("Invalid date format.")

        if appt_time_str:
            try:
                appt_time = datetime.strptime(
                    appt_time_str,
                    "%H:%M"
                ).time()

            except ValueError:
                errors.append("Invalid time format.")

        if errors:

            for err in errors:
                flash(err, "danger")

            return render_template(
                "book.html",
                salon=salon,
                salons=Salon.query.order_by(Salon.name).all(),
                categories=categories,
                selected_service=service,
                lang=get_lang(),
                form_data=request.form,
                today=date.today().isoformat(),
            )

        slot_start = datetime.combine(appt_date, appt_time)
        slot_end = slot_start + timedelta(minutes=service.duration_minutes)

        booking_windows = get_booking_windows(
            salon.slug,
            appt_date,
        )

        now_lisbon = datetime.now(
            ZoneInfo("Europe/Lisbon")
        ).replace(tzinfo=None)

        fits_booking_window = any(
            slot_start >= window_start
            and slot_end <= window_end
            for window_start, window_end in booking_windows
        )

        if not booking_windows:
            errors.append(
                "Não existem marcações online disponíveis neste salão neste dia."
                if lang == "pt"
                else "Online bookings are not available at this salon on this day."
            )
        elif not fits_booking_window:
            errors.append(
                "O horário escolhido não está disponível para marcações online neste salão."
                if lang == "pt"
                else "The selected time is not available for online bookings at this salon."
            )

        if appt_time.minute % 15 != 0 or appt_time.second:
            errors.append(
                "Escolha um horário em intervalos de 15 minutos."
                if lang == "pt"
                else "Please choose a time aligned to a 15-minute interval."
            )

        if slot_start < now_lisbon + timedelta(hours=2):
            errors.append(
                "A marcação deve ser feita com pelo menos 2 horas de antecedência."
                if lang == "pt"
                else "Bookings require at least 2 hours' notice."
            )

        # Serialize submissions for this salon on databases that support
        # SELECT FOR UPDATE, then recheck conflicts before committing.
        Salon.query.filter_by(
            id=salon.id
        ).with_for_update().one()

        existing_bookings = (
            Booking.query
            .filter(
                Booking.appointment_date == appt_date,
                Booking.status.notin_(["cancelled", "rejected"]),
            )
            .all()
        )

        for existing_booking in existing_bookings:
            existing_start = datetime.combine(
                appt_date,
                existing_booking.appointment_time,
            )
            existing_end = existing_start + timedelta(
                minutes=existing_booking.service.duration_minutes
            )

            if slot_start < existing_end and slot_end > existing_start:
                errors.append(
                    "Este horário já não está disponível. Escolha outro horário."
                    if lang == "pt"
                    else "This time is no longer available. Please choose another time."
                )
                break

        try:
            outlook_busy = get_calendar_events(appt_date)

            for existing_start, existing_end in outlook_busy:
                if (
                    slot_start < existing_end
                    and slot_end > existing_start
                ):
                    errors.append(
                        "Este horário já não está disponível. Escolha outro horário."
                        if lang == "pt"
                        else "This time is no longer available. Please choose another time."
                    )
                    break

        except GraphError as error:
            print(
                "Erro ao confirmar disponibilidade na Microsoft Graph:",
                error,
            )
            errors.append(
                "Não foi possível confirmar a disponibilidade. Tente novamente dentro de instantes."
                if lang == "pt"
                else "We could not confirm availability. Please try again shortly."
            )

        if errors:
            db.session.rollback()

            for err in errors:
                flash(err, "danger")

            return render_template(
                "book.html",
                salon=salon,
                salons=Salon.query.order_by(Salon.name).all(),
                categories=categories,
                selected_service=service,
                lang=lang,
                form_data=request.form,
                today=date.today().isoformat(),
            )

        customer = resolve_customer(
            name=client_name,
            email=client_email,
            phone=client_phone,
            language=lang,
        )
        db.session.add(customer)

        booking = Booking(

            salon_id=salon.id,

            customer=customer,

            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,

            service_id=service.id,
            service_price=service.price,

            appointment_date=appt_date,
            appointment_time=appt_time,

            notes=notes,

            status="pending",
        )

        record_customer_booking(customer, booking)

        db.session.add(booking)
        db.session.commit()

        try:
            start_datetime = datetime.combine(
                appt_date,
                appt_time,
            )

            end_datetime = (
                start_datetime
                + timedelta(minutes=service.duration_minutes)
            )

            event_id = create_calendar_event(
                salon_name=salon.name,
                salon_address=salon.address,
                service_name=service.name_pt,
                client_name=client_name,
                client_phone=client_phone,
                client_email=client_email,
                notes=notes,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )

            booking.outlook_event_id = event_id
            booking.status = "confirmed"
            db.session.commit()

            if client_email:
                try:
                    send_confirmation_email(
                        recipient=client_email,
                        language=lang,
                        client_name=client_name,
                        salon_name=salon.name,
                        salon_address=salon.address or "",
                        salon_phone=salon.phone or "",
                        service_name=service.name(lang),
                        appointment_date=appt_date,
                        appointment_time=appt_time,
                        duration_minutes=service.duration_minutes,
                        price=float(service.price),
                    )
                except GraphError as email_error:
                    print(
                        "Evento criado, mas ocorreu um erro ao enviar "
                        "o email de confirmação:",
                        email_error,
                    )

        except GraphError as error:
            print(
                "Erro ao criar evento na Microsoft Graph:",
                error,
            )

            booking.status = "pending"
            db.session.commit()

            flash(
                "A marcação foi registada, mas a sincronização com o calendário ficou pendente."
                if lang == "pt"
                else "The booking was registered, but calendar synchronisation is pending.",
                "warning",
            )

        flash(
            "A sua marcação foi confirmada com sucesso!",
            "success",
        )

        return redirect(
            url_for(
                "main.booking_success",
                booking_id=booking.id,
            )
        )

    return render_template(
        "book.html",
        salon=salon,
        salons=Salon.query.order_by(Salon.name).all(),
        categories=categories,
        selected_service=selected_service,
        lang=get_lang(),
        form_data={},
        today=date.today().isoformat(),
    )


@main.route("/booking-success/<int:booking_id>")
def booking_success(booking_id):

    salon = get_selected_salon()

    if not salon:
        return redirect(url_for("main.welcome"))

    booking = Booking.query.filter_by(
        id=booking_id,
        salon_id=salon.id
    ).first_or_404()

    return render_template(
        "booking_success.html",
        booking=booking,
        salon=salon,
        lang=get_lang()
    )


@main.route("/api/services")
def api_services():

    salon = get_selected_salon()

    if not salon:
        return jsonify([])
    
    lang = get_lang()

    categories = (
        ServiceCategory.query
        .filter_by(salon_id=salon.id)
        .order_by(ServiceCategory.display_order)
        .all()
    )

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

                for s in cat.services

                if s.active

            ],

        })

    return jsonify(result)


@main.route("/api/available-times")
def api_available_times():
    salon = get_selected_salon()

    # Obriga o cliente a escolher uma localização
    if not salon:
        return jsonify([])

    date_str = request.args.get("date")
    service_id = request.args.get("service_id", type=int)

    if not date_str or not service_id:
        return jsonify([])

    try:
        appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify([])

    # Não permitir datas anteriores
    if appt_date < date.today():
        return jsonify([])

    # Fechado ao sábado e domingo
    if appt_date.weekday() in [5, 6]:
        return jsonify([])

    # Confirma que o serviço pertence à localização escolhida
    service = (
        Service.query
        .join(ServiceCategory)
        .filter(
            Service.id == service_id,
            ServiceCategory.salon_id == salon.id,
            Service.active.is_(True),
        )
        .first()
    )

    if not service:
        return jsonify([])

    try:
        outlook_busy = get_calendar_events(appt_date)
    except GraphError as error:
        print(
            "Erro ao consultar o calendário na Microsoft Graph:",
            error,
        )
        return jsonify([]), 503

    existing = (
        Booking.query
        .filter(
            Booking.appointment_date == appt_date,
            Booking.status.notin_(["cancelled", "rejected"]),
        )
        .all()
    )

    booking_windows = get_booking_windows(
        salon.slug,
        appt_date,
    )

    if not booking_windows:
        return jsonify([])

    slots = []
    service_duration = timedelta(
        minutes=service.duration_minutes
    )

    booking_limit = (
        datetime.now(ZoneInfo("Europe/Lisbon"))
        .replace(tzinfo=None)
        + timedelta(hours=2)
    )

    for window_start, window_end in booking_windows:
        current_slot = window_start

        while current_slot + service_duration <= window_end:
            slot_start = current_slot
            slot_end = current_slot + service_duration

            if slot_start < booking_limit:
                current_slot += timedelta(minutes=15)
                continue

            overlaps = False

            for booking in existing:
                existing_start = datetime.combine(
                    appt_date,
                    booking.appointment_time,
                )

                existing_end = (
                    existing_start
                    + timedelta(
                        minutes=booking.service.duration_minutes
                    )
                )

                if (
                    slot_start < existing_end
                    and slot_end > existing_start
                ):
                    overlaps = True
                    break

            if not overlaps:
                for existing_start, existing_end in outlook_busy:
                    if (
                        slot_start < existing_end
                        and slot_end > existing_start
                    ):
                        overlaps = True
                        break

            if not overlaps:
                slots.append(
                    slot_start.strftime("%H:%M")
                )

            current_slot += timedelta(minutes=15)

    return jsonify(slots)


@main.route("/contact")
def contact():
    salon = get_selected_salon()

    if not salon:
        return redirect(url_for("main.welcome"))

    return render_template(
        "contact.html",
        salon=salon,
        lang=get_lang(),
    )
