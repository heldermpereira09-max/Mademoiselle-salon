import os
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from msal import ConfidentialClientApplication


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
LISBON_TZ = ZoneInfo("Europe/Lisbon")
REQUEST_TIMEOUT = 20


class GraphError(RuntimeError):
    """Erro numa operação da Microsoft Graph."""


def _settings():
    names = (
        "MS_TENANT_ID",
        "MS_CLIENT_ID",
        "MS_CLIENT_SECRET",
        "MS_MAILBOX",
        "MS_CALENDAR_ID",
    )

    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]

    if missing:
        raise GraphError(
            "Faltam variáveis Microsoft Graph: " + ", ".join(missing)
        )

    return values


def _access_token():
    settings = _settings()

    app = ConfidentialClientApplication(
        client_id=settings["MS_CLIENT_ID"],
        authority=(
            "https://login.microsoftonline.com/"
            + settings["MS_TENANT_ID"]
        ),
        client_credential=settings["MS_CLIENT_SECRET"],
    )

    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )

    token = result.get("access_token")

    if not token:
        description = result.get(
            "error_description",
            result.get("error", "Erro desconhecido"),
        )
        raise GraphError(
            "Não foi possível obter o token da Microsoft Graph: "
            + description
        )

    return token


def _request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {_access_token()}",
        "Accept": "application/json",
    })

    response = requests.request(
        method,
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )

    if not response.ok:
        try:
            details = response.json()
        except ValueError:
            details = response.text

        raise GraphError(
            f"Microsoft Graph devolveu HTTP {response.status_code}: "
            f"{details}"
        )

    if response.status_code == 204 or not response.content:
        return None

    return response.json()


def _parse_graph_datetime(value):
    date_time = value.get("dateTime", "")
    timezone_name = value.get("timeZone", "")

    parsed = datetime.fromisoformat(
        date_time.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        if timezone_name in ("UTC", "Coordinated Universal Time"):
            parsed = parsed.replace(tzinfo=timezone.utc)
        elif timezone_name in (
            "GMT Standard Time",
            "Europe/Lisbon",
        ):
            parsed = parsed.replace(tzinfo=LISBON_TZ)
        else:
            parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(LISBON_TZ).replace(tzinfo=None)


def get_calendar_events(appointment_date):
    """Devolve os períodos ocupados do calendário num determinado dia."""

    if not isinstance(appointment_date, date):
        raise TypeError("appointment_date tem de ser uma data.")

    settings = _settings()
    mailbox = quote(settings["MS_MAILBOX"], safe="")
    calendar_id = quote(settings["MS_CALENDAR_ID"], safe="")

    start_lisbon = datetime.combine(
        appointment_date,
        time.min,
        tzinfo=LISBON_TZ,
    )
    end_lisbon = start_lisbon + timedelta(days=1)

    start_utc = start_lisbon.astimezone(timezone.utc)
    end_utc = end_lisbon.astimezone(timezone.utc)

    url = (
        f"{GRAPH_BASE_URL}/users/{mailbox}"
        f"/calendars/{calendar_id}/calendarView"
    )

    data = _request(
        "GET",
        url,
        params={
            "startDateTime": start_utc.isoformat().replace("+00:00", "Z"),
            "endDateTime": end_utc.isoformat().replace("+00:00", "Z"),
            "$select": "id,subject,start,end,isCancelled,showAs",
            "$top": "100",
        },
        headers={
            "Prefer": 'outlook.timezone="Europe/Lisbon"',
        },
    )

    busy_periods = []

    for event in data.get("value", []):
        if event.get("isCancelled"):
            continue

        if event.get("showAs") == "free":
            continue

        event_start = _parse_graph_datetime(event["start"])
        event_end = _parse_graph_datetime(event["end"])

        busy_periods.append((event_start, event_end))

    return busy_periods


def create_calendar_event(
    *,
    salon_name,
    salon_address,
    service_name,
    client_name,
    client_phone,
    client_email,
    notes,
    start_datetime,
    end_datetime,
):
    """Cria uma marcação no calendário e devolve o ID do evento."""

    settings = _settings()
    mailbox = quote(settings["MS_MAILBOX"], safe="")
    calendar_id = quote(settings["MS_CALENDAR_ID"], safe="")

    start_lisbon = start_datetime.replace(tzinfo=LISBON_TZ)
    end_lisbon = end_datetime.replace(tzinfo=LISBON_TZ)

    start_utc = start_lisbon.astimezone(timezone.utc)
    end_utc = end_lisbon.astimezone(timezone.utc)

    description_lines = [
        f"Salão: {salon_name}",
        f"Serviço: {service_name}",
        f"Cliente: {client_name}",
        f"Telefone: {client_phone}",
        f"Email: {client_email or 'Não indicado'}",
        f"Observações: {notes or 'Sem observações'}",
    ]

    payload = {
        "subject": f"[{salon_name}] {service_name} — {client_name}",
        "body": {
            "contentType": "text",
            "content": "\n".join(description_lines),
        },
        "start": {
            "dateTime": start_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "UTC",
        },
        "location": {
            "displayName": salon_address or salon_name,
        },
        "showAs": "busy",
        "isReminderOn": True,
        "reminderMinutesBeforeStart": 60,
    }

    url = (
        f"{GRAPH_BASE_URL}/users/{mailbox}"
        f"/calendars/{calendar_id}/events"
    )

    event = _request(
        "POST",
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    event_id = event.get("id")

    if not event_id:
        raise GraphError("A Microsoft Graph não devolveu o ID do evento.")

    return event_id


def send_confirmation_email(
    *,
    recipient,
    language,
    client_name,
    salon_name,
    salon_address,
    salon_phone,
    service_name,
    appointment_date,
    appointment_time,
    duration_minutes,
    price,
):
    """Envia a confirmação da marcação para o cliente."""

    if not recipient:
        return False

    settings = _settings()
    mailbox = quote(settings["MS_MAILBOX"], safe="")

    if language == "en":
        subject = "Booking confirmation — Mademoiselle"
        body = f"""
        <p>Hello {client_name},</p>
        <p>Your booking has been confirmed.</p>
        <p>
        <strong>Salon:</strong> {salon_name}<br>
        <strong>Service:</strong> {service_name}<br>
        <strong>Date:</strong> {appointment_date.strftime('%d/%m/%Y')}<br>
        <strong>Time:</strong> {appointment_time.strftime('%H:%M')}<br>
        <strong>Duration:</strong> {duration_minutes} minutes<br>
        <strong>Price:</strong> €{price:.2f}<br>
        <strong>Address:</strong> {salon_address}<br>
        <strong>Telephone:</strong> {salon_phone}
        </p>
        <p>Thank you,<br>Mademoiselle Estética &amp; Beleza</p>
        """
    else:
        subject = "Confirmação da sua marcação — Mademoiselle"
        body = f"""
        <p>Olá {client_name},</p>
        <p>A sua marcação foi confirmada.</p>
        <p>
        <strong>Salão:</strong> {salon_name}<br>
        <strong>Serviço:</strong> {service_name}<br>
        <strong>Data:</strong> {appointment_date.strftime('%d/%m/%Y')}<br>
        <strong>Hora:</strong> {appointment_time.strftime('%H:%M')}<br>
        <strong>Duração:</strong> {duration_minutes} minutos<br>
        <strong>Preço:</strong> {price:.2f} €<br>
        <strong>Morada:</strong> {salon_address}<br>
        <strong>Telefone:</strong> {salon_phone}
        </p>
        <p>Obrigada,<br>Mademoiselle Estética &amp; Beleza</p>
        """

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body,
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient,
                    }
                }
            ],
        },
        "saveToSentItems": True,
    }

    _request(
        "POST",
        f"{GRAPH_BASE_URL}/users/{mailbox}/sendMail",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    return True
