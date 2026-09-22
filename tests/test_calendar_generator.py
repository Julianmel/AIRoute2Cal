"""Testes unitários para o gerador de arquivos iCalendar e CSV."""

from src.models import TimelineDay, DisplacementEvent, VisitEvent
from src.calendar_generator import generate_ics, generate_outlook_csv


def test_generate_ics_and_csv():
    # Cria dados simulados
    day = TimelineDay(
        date="2026-09-21",
        total_km=13.5,
        total_driving_min=27,
        displacements=[
            DisplacementEvent(
                origin_name="Casa",
                destination_name="Supermercado",
                start_time="07:03",
                end_time="07:25",
                distance_km=11.0,
                duration_min=22,
            )
        ],
        visits=[
            VisitEvent(
                place_name="Supermercado",
                address="Rua Castro Alves",
                start_time="07:25",
                end_time="07:36",
                duration_min=11,
            )
        ],
    )

    # 1. Testa ICS
    ics = generate_ics(day, include_displacements=True, include_visits=True)
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "Deslocamento: Casa ➔ Supermercado" in ics
    assert "Visita: Supermercado" in ics

    # 2. Testa CSV
    csv_content = generate_outlook_csv(day, include_displacements=True, include_visits=False)
    assert "Subject" in csv_content
    assert "21/09/2026" in csv_content
    assert "Casa" in csv_content
