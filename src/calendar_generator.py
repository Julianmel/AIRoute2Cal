"""Geração de arquivos de calendário nos formatos iCalendar (.ics - RFC 5545) e CSV (Outlook)."""

from datetime import datetime
from typing import List
import csv
import io
from .models import TimelineDay, DisplacementEvent, VisitEvent


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
    timezone_name: str = "America/Sao_Paulo",
) -> str:
    """Gera o conteúdo de um arquivo iCalendar (.ics) RFC 5545 completo."""
    cal_name = f"Deslocamentos - {timeline.date}"
    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
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

    # Lista unificada de eventos ordenados por horário de início
    events = []

    if include_displacements:
        for idx, disp in enumerate(timeline.displacements, 1):
            s_time = disp.start_time.replace(":", "") + "00"
            e_time = disp.end_time.replace(":", "") + "00"
            summary = f"🚗 Deslocamento: {disp.origin_name} ➔ {disp.destination_name} ({disp.distance_km:.1f} km)"
            desc = (
                f"Trajeto de carro registrado no Google Maps Linha do Tempo.\n"
                f"Distância: {disp.distance_km:.1f} km\n"
                f"Duração: {disp.duration_min} min\n"
                f"Origem: {disp.origin_name} ({disp.origin_address or ''})\n"
                f"Destino: {disp.destination_name} ({disp.destination_address or ''})"
            )
            loc = disp.destination_address or disp.destination_name
            events.append({
                "uid": f"disp-{idx}-{clean_date}T{s_time}@airoute2cal",
                "start": f"{clean_date}T{s_time}",
                "end": f"{clean_date}T{e_time}",
                "summary": summary,
                "description": desc,
                "location": loc,
                "category": "Deslocamento",
                "order_key": disp.start_time,
            })

    if include_visits:
        for idx, visit in enumerate(timeline.visits, 1):
            s_time = visit.start_time.replace(":", "") + "00"
            e_time = visit.end_time.replace(":", "") + "00"
            dur_str = f" ({visit.duration_min} min)" if visit.duration_min else ""
            summary = f"📍 Visita: {visit.place_name}{dur_str}"
            desc = (
                f"Visita/parada registrada no Google Maps Linha do Tempo.\n"
                f"Local: {visit.place_name}\n"
                f"Endereço: {visit.address or 'Não informado'}\n"
                f"Horário: {visit.start_time} - {visit.end_time}"
            )
            loc = visit.address or visit.place_name
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


def generate_outlook_csv(timeline: TimelineDay, include_displacements: bool = True, include_visits: bool = False) -> str:
    """Gera um arquivo CSV formatado para o assistente de importação do Microsoft Outlook."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Cabeçalho padrão do Outlook
    writer.writerow(["Subject", "Start Date", "Start Time", "End Date", "End Time", "Description", "Location", "Categories"])

    # Formatação de data brasileira (DD/MM/YYYY)
    dt_obj = datetime.strptime(timeline.date, "%Y-%m-%d")
    formatted_date = dt_obj.strftime("%d/%m/%Y")

    if include_displacements:
        for disp in timeline.displacements:
            subject = f"Deslocamento: {disp.origin_name} -> {disp.destination_name}"
            s_time = f"{disp.start_time}:00"
            e_time = f"{disp.end_time}:00"
            desc = f"Distância: {disp.distance_km:.1f} km | Duração: {disp.duration_min} min | De: {disp.origin_name} | Para: {disp.destination_name}"
            loc = disp.destination_address or disp.destination_name
            writer.writerow([subject, formatted_date, s_time, formatted_date, e_time, desc, loc, "Deslocamento"])

    if include_visits:
        for visit in timeline.visits:
            subject = f"Visita: {visit.place_name}"
            s_time = f"{visit.start_time}:00"
            e_time = f"{visit.end_time}:00"
            desc = f"Visita registrada no Google Maps | Local: {visit.place_name} | Endereço: {visit.address or ''}"
            loc = visit.address or visit.place_name
            writer.writerow([subject, formatted_date, s_time, formatted_date, e_time, desc, loc, "Visita"])

    return output.getvalue()
