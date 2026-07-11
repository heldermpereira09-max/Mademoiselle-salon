from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
from .app import db
from .models.models import Salon, ServiceCategory, Service, Booking
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

main = Blueprint("main", __name__)
AVAILABILITY_WEBHOOK_URL = "https://hook.eu1.make.com/awukxncixk8n2guc1bon25f2oi27krfv"
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/i8usajk6gi1jvi2cyo02h2ylwptwqabi"


def get_lang():
    return session.get("lang", "pt")


def get_selected_salon():
    slug = session.get("salon_slug")

    if not slug:
        return None

    return Salon.query.filter_by(slug=slug).first()


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

        service = (
            Service.query
            .join(ServiceCategory)
            .filter(
                Service.id == service_id,
                ServiceCategory.salon_id == salon.id
            )
            .first()
        )

        errors = []

        if not client_name:
            errors.append("Name is required.")

        if not client_phone:
            errors.append("Phone is required.")

        if not service:
            errors.append("Please select a valid service.")

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

        booking = Booking(

            salon_id=salon.id,

            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,

            service_id=service.id,

            appointment_date=appt_date,
            appointment_time=appt_time,

            notes=notes,

            status="pending",
        )

        db.session.add(booking)
        db.session.commit()

        try:

            start_datetime = datetime.combine(
                appt_date,
                appt_time
            )

            end_datetime = (
                start_datetime +
                timedelta(minutes=service.duration_minutes)
            )

            payload = {

                "salon": salon.slug,
                "salon_name": salon.name,

                "service": service.name_pt,

                "date": appt_date.strftime("%d/%m/%Y"),
                "time": appt_time.strftime("%H:%M"),

                "duration": service.duration_minutes,
                "price": float(service.price),

                "client": client_name,
                "email": client_email,
                "phone": client_phone,

                "notes": notes,

                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat(),
            }

            requests.post(
                MAKE_WEBHOOK_URL,
                json=payload,
                timeout=10
            )

        except Exception as e:
            print(f"Erro ao enviar webhook para Make: {e}")

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

    # Consultar os eventos do Outlook através do Make
    try:
        response = requests.post(
            AVAILABILITY_WEBHOOK_URL,
            json={
                "date": date_str,
                "salon": salon.slug,
                "salon_name": salon.name,
            },
            timeout=10,
        )

        if response.status_code == 200:
            outlook_events = response.json()
        else:
            outlook_events = []

    except Exception as e:
        print("Erro ao consultar Outlook:", e)
        outlook_events = []

    outlook_busy = []

    if isinstance(outlook_events, dict):
        for event in outlook_events.get("value", []):
            try:
                start_str = event["start"]["dateTime"]
                end_str = event["end"]["dateTime"]

                # Remover milissegundos enviados pelo Outlook
                start_str = start_str.split(".")[0]
                end_str = end_str.split(".")[0]

                start_dt = (
                    datetime.fromisoformat(start_str)
                    .replace(tzinfo=timezone.utc)
                    .astimezone(ZoneInfo("Europe/Lisbon"))
                    .replace(tzinfo=None)
                )

                end_dt = (
                    datetime.fromisoformat(end_str)
                    .replace(tzinfo=timezone.utc)
                    .astimezone(ZoneInfo("Europe/Lisbon"))
                    .replace(tzinfo=None)
                )

                outlook_busy.append((start_dt, end_dt))

            except Exception as e:
                print("Erro ao ler evento Outlook:", e)

    # Só consultar marcações da localização escolhida
    existing = Booking.query.filter_by(
        salon_id=salon.id,
        appointment_date=appt_date,
    ).all()

    slots = []
    start_hour = 9
    end_hour = 19

    current_slot = datetime.combine(
        appt_date,
        datetime.min.time().replace(hour=start_hour),
    )

    closing_time = datetime.combine(
        appt_date,
        datetime.min.time().replace(hour=end_hour),
    )

    service_duration = timedelta(minutes=service.duration_minutes)
    booking_limit = datetime.now() + timedelta(hours=2)

    while current_slot + service_duration <= closing_time:
        slot_start = current_slot
        slot_end = current_slot + service_duration

        # No próprio dia, exige pelo menos duas horas de antecedência
        if appt_date == date.today() and slot_start < booking_limit:
            current_slot += timedelta(minutes=15)
            continue

        overlaps = False

        # Verificar marcações guardadas na base de dados
        for booking in existing:
            existing_start = datetime.combine(
                appt_date,
                booking.appointment_time,
            )

            existing_end = existing_start + timedelta(
                minutes=booking.service.duration_minutes
            )

            if slot_start < existing_end and slot_end > existing_start:
                overlaps = True
                break

        # Verificar eventos existentes no calendário Outlook
        if not overlaps:
            for existing_start, existing_end in outlook_busy:
                if slot_start < existing_end and slot_end > existing_start:
                    overlaps = True
                    break

        if not overlaps:
            slots.append(slot_start.strftime("%H:%M"))

        current_slot += timedelta(minutes=15)

    return jsonify(slots)


@main.route("/contact")
def contact():
    return render_template("contact.html", lang=get_lang())
