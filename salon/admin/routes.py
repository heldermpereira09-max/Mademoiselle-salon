from datetime import datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from . import admin
from .auth import ADMIN_SESSION_KEY, admin_required, get_current_admin
from ..app import db
from ..customer_service import refresh_customer_booking_metrics
from ..graph import (
    GraphError,
    get_calendar_events,
    send_booking_updated_email,
    update_calendar_event,
)
from ..models.models import (
    AdminUser,
    Booking,
    Salon,
    Service,
    ServiceCategory,
)
from ..routes import get_booking_windows


BOOKINGS_PER_PAGE = 20


def _safe_next_url(value):
    if not value:
        return None

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/"):
        return None

    return value


@admin.route("/login", methods=["GET", "POST"])
def login():
    if get_current_admin() is not None:
        return redirect(url_for("admin.dashboard"))

    next_url = _safe_next_url(request.values.get("next"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin_user = AdminUser.query.filter_by(email=email).first()

        if (
            admin_user is None
            or not admin_user.is_active
            or not admin_user.check_password(password)
        ):
            flash("Email ou palavra-passe inválidos.", "danger")
        else:
            session.clear()
            session[ADMIN_SESSION_KEY] = admin_user.id
            session.permanent = True
            return redirect(next_url or url_for("admin.dashboard"))

    return render_template("admin/login.html", next_url=next_url)


@admin.route("/logout", methods=["POST"])
def logout():
    session.pop(ADMIN_SESSION_KEY, None)
    flash("Sessão terminada com sucesso.", "success")
    return redirect(url_for("admin.login"))


@admin.route("/")
@admin_required
def dashboard():
    now = datetime.now(ZoneInfo("Europe/Lisbon")).replace(tzinfo=None)
    today_bookings = Booking.query.filter(
        Booking.appointment_date == now.date()
    )
    bookings_today_count = today_bookings.count()
    upcoming_bookings = (
        today_bookings
        .filter(Booking.appointment_time >= now.time())
        .options(joinedload(Booking.service), joinedload(Booking.salon))
        .order_by(Booking.appointment_time, Booking.id)
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        admin_user=get_current_admin(),
        bookings_today_count=bookings_today_count,
        upcoming_bookings=upcoming_bookings,
    )


@admin.route("/bookings")
@admin_required
def bookings():
    search = request.args.get("q", "").strip()
    period = request.args.get("period", "today")
    page = request.args.get("page", 1, type=int)
    today = datetime.now(ZoneInfo("Europe/Lisbon")).date()

    query = Booking.query.options(
        joinedload(Booking.service),
        joinedload(Booking.salon),
    )

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Booking.client_name.ilike(pattern),
                Booking.client_phone.ilike(pattern),
                Booking.client_email.ilike(pattern),
            )
        )

    if period == "today":
        query = query.filter(Booking.appointment_date == today)
    elif period == "tomorrow":
        query = query.filter(
            Booking.appointment_date == today + timedelta(days=1)
        )
    elif period == "week":
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(
            Booking.appointment_date.between(week_start, week_end)
        )
    elif period != "all":
        period = "today"
        query = query.filter(Booking.appointment_date == today)

    pagination = (
        query
        .order_by(
            Booking.appointment_date,
            Booking.appointment_time,
            Booking.id,
        )
        .paginate(
            page=max(page, 1),
            per_page=BOOKINGS_PER_PAGE,
            error_out=False,
        )
    )

    return render_template(
        "admin/bookings.html",
        admin_user=get_current_admin(),
        pagination=pagination,
        bookings=pagination.items,
        search=search,
        period=period,
    )


@admin.route("/bookings/<int:booking_id>")
@admin_required
def booking_detail(booking_id):
    booking = (
        Booking.query
        .options(joinedload(Booking.service), joinedload(Booking.salon))
        .filter_by(id=booking_id)
        .first_or_404()
    )

    return_to = _safe_next_url(request.args.get("return_to"))

    return render_template(
        "admin/booking_detail.html",
        admin_user=get_current_admin(),
        booking=booking,
        return_to=return_to,
    )


def _booking_edit_form(booking, services, form_data, errors, return_to):
    return render_template(
        "admin/booking_edit.html",
        admin_user=get_current_admin(),
        booking=booking,
        services=services,
        form_data=form_data,
        errors=errors,
        return_to=return_to,
    )


def _update_outlook_event(booking, service, appointment_date, appointment_time, notes):
    start_datetime = datetime.combine(appointment_date, appointment_time)
    end_datetime = start_datetime + timedelta(
        minutes=service.duration_minutes
    )
    update_calendar_event(
        event_id=booking.outlook_event_id,
        salon_name=booking.salon.name,
        salon_address=booking.salon.address,
        service_name=service.name_pt,
        client_name=booking.client_name,
        client_phone=booking.client_phone,
        client_email=booking.client_email,
        notes=notes,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )


@admin.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
@admin_required
def booking_edit(booking_id):
    booking = (
        Booking.query
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.service),
            joinedload(Booking.salon),
        )
        .filter_by(id=booking_id)
        .first_or_404()
    )
    services = (
        Service.query
        .join(ServiceCategory)
        .filter(
            ServiceCategory.salon_id == booking.salon_id,
            Service.active.is_(True),
        )
        .order_by(Service.name_pt, Service.id)
        .all()
    )
    return_to = _safe_next_url(request.values.get("return_to"))

    if request.method == "GET":
        form_data = {
            "service_id": str(booking.service_id),
            "appointment_date": booking.appointment_date.isoformat(),
            "appointment_time": booking.appointment_time.strftime("%H:%M"),
            "notes": booking.notes or "",
        }
        return _booking_edit_form(
            booking, services, form_data, [], return_to
        )

    form_data = request.form
    service_id = request.form.get("service_id", type=int)
    appointment_date_text = request.form.get(
        "appointment_date", ""
    ).strip()
    appointment_time_text = request.form.get(
        "appointment_time", ""
    ).strip()
    notes = request.form.get("notes", "").strip()
    errors = []

    service = (
        Service.query
        .join(ServiceCategory)
        .filter(
            Service.id == service_id,
            ServiceCategory.salon_id == booking.salon_id,
            Service.active.is_(True),
        )
        .first()
    )
    if service is None:
        errors.append("Selecione um serviço válido deste salão.")

    appointment_date = None
    appointment_time = None
    try:
        appointment_date = datetime.strptime(
            appointment_date_text, "%Y-%m-%d"
        ).date()
    except ValueError:
        errors.append("Introduza uma data válida.")

    try:
        appointment_time = datetime.strptime(
            appointment_time_text, "%H:%M"
        ).time()
    except ValueError:
        errors.append("Introduza uma hora válida.")

    if not errors:
        slot_start = datetime.combine(appointment_date, appointment_time)
        slot_end = slot_start + timedelta(
            minutes=service.duration_minutes
        )
        now_lisbon = datetime.now(
            ZoneInfo("Europe/Lisbon")
        ).replace(tzinfo=None)
        booking_windows = get_booking_windows(
            booking.salon.slug,
            appointment_date,
        )
        fits_booking_window = any(
            slot_start >= window_start and slot_end <= window_end
            for window_start, window_end in booking_windows
        )

        if not booking_windows:
            errors.append(
                "Não existem marcações online disponíveis neste salão "
                "neste dia."
            )
        elif not fits_booking_window:
            errors.append(
                "O horário escolhido não está disponível para marcações "
                "online neste salão."
            )

        if appointment_time.minute % 15 != 0 or appointment_time.second:
            errors.append(
                "Escolha um horário em intervalos de 15 minutos."
            )

        if slot_start < now_lisbon + timedelta(hours=2):
            errors.append(
                "A marcação deve ter pelo menos 2 horas de antecedência."
            )

    if not errors:
        Salon.query.filter_by(
            id=booking.salon_id
        ).with_for_update().one()

        existing_bookings = (
            Booking.query
            .filter(
                Booking.id != booking.id,
                Booking.appointment_date == appointment_date,
                Booking.status.notin_(["cancelled", "rejected"]),
            )
            .all()
        )
        for existing_booking in existing_bookings:
            existing_start = datetime.combine(
                appointment_date,
                existing_booking.appointment_time,
            )
            existing_end = existing_start + timedelta(
                minutes=existing_booking.service.duration_minutes
            )
            if slot_start < existing_end and slot_end > existing_start:
                errors.append(
                    "Este horário já não está disponível. "
                    "Escolha outro horário."
                )
                break

    if not errors:
        try:
            outlook_busy = get_calendar_events(
                appointment_date,
                exclude_event_id=booking.outlook_event_id,
            )
            for existing_start, existing_end in outlook_busy:
                if slot_start < existing_end and slot_end > existing_start:
                    errors.append(
                        "Este horário já está ocupado no Outlook. "
                        "Escolha outro horário."
                    )
                    break
        except GraphError:
            current_app.logger.exception(
                "Erro ao validar disponibilidade Graph da marcação %s",
                booking.id,
            )
            errors.append(
                "Não foi possível confirmar a disponibilidade no Outlook. "
                "Tente novamente."
            )

    if errors:
        db.session.rollback()
        return _booking_edit_form(
            booking, services, form_data, errors, return_to
        )

    previous = {
        "service": booking.service,
        "appointment_date": booking.appointment_date,
        "appointment_time": booking.appointment_time,
        "notes": booking.notes or "",
    }

    try:
        _update_outlook_event(
            booking,
            service,
            appointment_date,
            appointment_time,
            notes,
        )
    except GraphError:
        db.session.rollback()
        current_app.logger.exception(
            "Erro ao atualizar evento Graph da marcação %s",
            booking.id,
        )
        errors.append(
            "Não foi possível sincronizar a alteração com o Outlook. "
            "A marcação não foi alterada."
        )
        return _booking_edit_form(
            booking, services, form_data, errors, return_to
        )

    try:
        booking.service = service
        booking.service_price = service.price
        booking.appointment_date = appointment_date
        booking.appointment_time = appointment_time
        booking.notes = notes
        refresh_customer_booking_metrics(booking.customer)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Erro ao guardar a edição da marcação %s",
            booking.id,
        )
        try:
            _update_outlook_event(
                booking,
                previous["service"],
                previous["appointment_date"],
                previous["appointment_time"],
                previous["notes"],
            )
        except GraphError:
            current_app.logger.exception(
                "Falhou a reposição do evento Graph da marcação %s",
                booking.id,
            )
        errors.append(
            "Não foi possível guardar a alteração. Tente novamente."
        )
        return _booking_edit_form(
            booking, services, form_data, errors, return_to
        )

    email_failed = False
    if booking.client_email:
        try:
            language = (
                booking.customer.preferred_language
                if booking.customer
                and booking.customer.preferred_language in ("pt", "en")
                else "pt"
            )
            send_booking_updated_email(
                recipient=booking.client_email,
                language=language,
                client_name=booking.client_name,
                salon_name=booking.salon.name,
                salon_address=booking.salon.address or "",
                salon_phone=booking.salon.phone or "",
                service_name=service.name(language),
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                duration_minutes=service.duration_minutes,
                price=float(booking.service_price),
            )
        except GraphError:
            email_failed = True
            current_app.logger.exception(
                "Marcação %s alterada, mas o email falhou",
                booking.id,
            )

    flash("Marcação alterada e sincronizada com o Outlook.", "success")
    if email_failed:
        flash(
            "A marcação foi alterada, mas não foi possível enviar o email "
            "ao cliente.",
            "warning",
        )

    return redirect(
        return_to
        or url_for("admin.booking_detail", booking_id=booking.id)
    )
