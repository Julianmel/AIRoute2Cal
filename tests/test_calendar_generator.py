"""Testes unitários para o gerador de arquivos iCalendar e CSV."""

from src.models import TimelineDay, DisplacementEvent, VisitEvent
from src.calendar_generator import generate_ics, generate_outlook_csv


def test_generate_ics_and_csv():
    day = TimelineDay(
        date="2026-09-21",
        total_km=13.5,
        total_driving_min=22,
        total_walking_min=15,
        displacements=[
            DisplacementEvent(
                mode="Dirigindo",
                origin_name="Casa",
                destination_name="Supermercado",
                start_time="07:03",
                end_time="07:25",
                distance_km=11.0,
                duration_min=22,
            ),
            DisplacementEvent(
                mode="Caminhando",
                origin_name="Supermercado",
                destination_name="Padaria",
                start_time="07:36",
                end_time="07:51",
                distance_km=0.8,
                duration_min=15,
                details="1.200 passos",
            ),
        ],
        visits=[
            VisitEvent(
                place_name="Supermercado",
                address="Rua Castro Alves",
                start_time="07:25",
                end_time="07:36",
                duration_min=11,
                details="Saiu às 07:36",
            )
        ],
    )

    # 1. Testa ICS
    ics = generate_ics(day, include_displacements=True, include_visits=True)
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "Dirigindo: Casa ➔ Supermercado" in ics
    assert "Caminhando: Supermercado ➔ Padaria" in ics
    assert "Visita: Supermercado" in ics

    # 2. Testa CSV
    csv_content = generate_outlook_csv(day, include_displacements=True, include_visits=True)
    assert "Subject" in csv_content
    assert "21/09/2026" in csv_content
    assert "Caminhando" in csv_content
    assert "Padaria" in csv_content
