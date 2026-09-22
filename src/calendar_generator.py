"""Geração de arquivos de calendário nos formatos iCalendar (.ics - RFC 5545) e CSV (Outlook)."""

from datetime import datetime, timezone
from typing import List, Optional
import csv
import io
from .models import TimelineDay, DisplacementEvent, VisitEvent


def format_decimal_br(value: Optional[float], decimals: int = 1) -> str:
    """Formata número decimal usando vírgula como separador (padrão brasileiro)."""
    if value is None:
        return "-"
    return f"{value:.{decimals}f}".replace(".", ",")


def format_currency_br(value: Optional[float]) -> str:
    """Formata valor monetário em Reais no padrão brasileiro (ex: R$ 12,50)."""
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:.2f}".replace(".", ",")


def get_mode_icon(mode: str) -> str:
    """Retorna um emoji representativo para o modo de deslocamento."""
    m = (mode or "").lower()
    if any(k in m for k in ["caminh", "pé", "pe", "walk", "pedestre"]):
        return "🚶"
    elif any(k in m for k in ["bici", "pedal", "cycl", "bike"]):
        return "🚲"
    elif any(k in m for k in ["onibus", "ônibus", "bus", "transit", "metro", "metrô", "trem"]):
        return "🚌"
    elif any(k in m for k in ["corr", "run"]):
        return "🏃"
    elif any(k in m for k in ["moto", "scooter"]):
        return "🛵"
    elif any(k in m for k in ["não há", "nao ha", "sem modo", "desconhecido", "?"]):
        return "❓"
    else:
        return "🚗"


_get_mode_icon = get_mode_icon


def _escape_ics_text(text: str) -> str:
    """Escapa caracteres reservados no formato iCalendar."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def generate_ics(
    timeline: TimelineDay,
    include_displacements: bool = True,
    include_visits: bool = True,
    only_mode: Optional[str] = None,
    timezone_name: str = "America/Sao_Paulo",
) -> str:
    """Gera o conteúdo de um arquivo iCalendar (.ics) RFC 5545 completo."""
    cal_name = f"Linha do Tempo - {timeline.date}"
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    clean_date = timeline.date.replace("-", "")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JulianMel//AIRoute2Cal//PT-BR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        f"X-WR-TIMEZONE:{timezone_name}",
        "BEGIN:VTIMEZONE",
        f"TZID:{timezone_name}",
        f"X-LIC-LOCATION:{timezone_name}",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0300",
        "TZOFFSETTO:-0300",
        "TZNAME:-03",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    events = []

    if include_displacements:
        for idx, disp in enumerate(timeline.displacements, 1):
            mode = getattr(disp, "mode", "Dirigindo")
            if only_mode and only_mode.lower() not in mode.lower():
                continue

            s_time = disp.start_time.replace(":", "") + "00"
            e_time = disp.end_time.replace(":", "") + "00"
            icon = _get_mode_icon(mode)

            dist_str = f" ({format_decimal_br(getattr(disp, 'distance_km', None))} km)" if getattr(disp, "distance_km", None) is not None else ""
            summary = f"{icon} {mode}: {disp.origin_name} ➔ {disp.destination_name}{dist_str}"

            desc_parts = [
                f"Deslocamento ({mode}) registrado no Google Maps Linha do Tempo."
            ]
            if getattr(disp, "distance_km", None) is not None:
                desc_parts.append(f"Distância: {format_decimal_br(disp.distance_km)} km")
            if getattr(disp, "duration_min", None) is not None:
                desc_parts.append(f"Duração: {disp.duration_min} min")
            details = getattr(disp, "details", None)
            if details:
                desc_parts.append(f"Detalhes: {details}")
            desc_parts.append(f"Origem: {disp.origin_name} ({getattr(disp, 'origin_address', None) or ''})")
            desc_parts.append(f"Destino: {disp.destination_name} ({getattr(disp, 'destination_address', None) or ''})")

            desc = "\n".join(desc_parts)
            loc = getattr(disp, "destination_address", None) or disp.destination_name
            cat = f"Deslocamento ({mode})"

            events.append({
                "uid": f"disp-{idx}-{clean_date}T{s_time}@airoute2cal",
                "start": f"{clean_date}T{s_time}",
                "end": f"{clean_date}T{e_time}",
                "summary": summary,
                "description": desc,
                "location": loc,
                "category": cat,
                "order_key": disp.start_time,
            })

    if include_visits:
        for idx, visit in enumerate(timeline.visits, 1):
            s_time = visit.start_time.replace(":", "") + "00"
            e_time = visit.end_time.replace(":", "") + "00"
            dur_str = f" ({visit.duration_min} min)" if visit.duration_min else ""
            summary = f"📍 Visita: {visit.place_name}{dur_str}"

            desc_parts = [
                "Visita/parada registrada no Google Maps Linha do Tempo.",
                f"Local: {visit.place_name}",
                f"Endereço: {visit.address or 'Não informado'}",
                f"Horário: {visit.start_time} - {visit.end_time}",
            ]
            dur_min = getattr(visit, "duration_min", None)
            if dur_min:
                desc_parts.append(f"Duração: {dur_min} min")
            details = getattr(visit, "details", None)
            if details:
                desc_parts.append(f"Observações: {details}")

            desc = "\n".join(desc_parts)
            loc = getattr(visit, "address", None) or visit.place_name

            events.append({
                "uid": f"visit-{idx}-{clean_date}T{s_time}@airoute2cal",
                "start": f"{clean_date}T{s_time}",
                "end": f"{clean_date}T{e_time}",
                "summary": summary,
                "description": desc,
                "location": loc,
                "category": "Visita",
                "order_key": visit.start_time,
            })

    events.sort(key=lambda x: x["order_key"])

    for evt in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{evt['uid']}")
        lines.append(f"DTSTAMP:{now_utc}")
        lines.append(f"DTSTART;TZID={timezone_name}:{evt['start']}")
        lines.append(f"DTEND;TZID={timezone_name}:{evt['end']}")
        lines.append(f"SUMMARY:{_escape_ics_text(evt['summary'])}")
        lines.append(f"DESCRIPTION:{_escape_ics_text(evt['description'])}")
        lines.append(f"LOCATION:{_escape_ics_text(evt['location'])}")
        lines.append(f"CATEGORIES:{evt['category']}")
        lines.append("STATUS:CONFIRMED")
        lines.append("TRANSP:OPAQUE")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def generate_outlook_csv(
    timeline: TimelineDay,
    include_displacements: bool = True,
    include_visits: bool = False,
) -> str:
    """Gera um arquivo CSV formatado para o assistente de importação do Microsoft Outlook."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow(["Subject", "Start Date", "Start Time", "End Date", "End Time", "Description", "Location", "Categories"])

    dt_obj = datetime.strptime(timeline.date, "%Y-%m-%d")
    formatted_date = dt_obj.strftime("%d/%m/%Y")

    if include_displacements:
        for disp in getattr(timeline, "displacements", []):
            mode = getattr(disp, "mode", "Dirigindo")
            subject = f"{mode}: {disp.origin_name} -> {disp.destination_name}"
            s_time = f"{disp.start_time}:00"
            e_time = f"{disp.end_time}:00"
            dist_km = getattr(disp, "distance_km", None)
            dur_min = getattr(disp, "duration_min", None)
            dist_str = f"{format_decimal_br(dist_km)} km" if dist_km is not None else "N/A"
            dur_str = f"{dur_min} min" if dur_min is not None else "N/A"
            desc = (
                f"Modo: {mode} | Distância: {dist_str} | Duração: {dur_str} | "
                f"De: {disp.origin_name} | Para: {disp.destination_name}"
            )
            details = getattr(disp, "details", None)
            if details:
                desc += f" | Detalhes: {details}"
            loc = getattr(disp, "destination_address", None) or disp.destination_name
            writer.writerow([subject, formatted_date, s_time, formatted_date, e_time, desc, loc, f"Deslocamento ({mode})"])

    if include_visits:
        for visit in getattr(timeline, "visits", []):
            subject = f"Visita: {visit.place_name}"
            s_time = f"{visit.start_time}:00"
            e_time = f"{visit.end_time}:00"
            desc = f"Visita registrada no Google Maps | Local: {visit.place_name} | Endereço: {getattr(visit, 'address', None) or ''}"
            details = getattr(visit, "details", None)
            if details:
                desc += f" | Obs: {details}"
            loc = getattr(visit, "address", None) or visit.place_name
            writer.writerow([subject, formatted_date, s_time, formatted_date, e_time, desc, loc, "Visita"])

    return output.getvalue()
