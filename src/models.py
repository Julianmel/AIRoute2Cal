"""Modelos de dados Pydantic para estruturação dos eventos da Linha do Tempo."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DisplacementEvent(BaseModel):
    """Representa um deslocamento / trajeto de carro entre dois pontos."""
    origin_name: str = Field(..., description="Nome do local de origem (ex: Casa)")
    destination_name: str = Field(..., description="Nome do local de destino (ex: Supermercado Portal)")
    origin_address: Optional[str] = Field(None, description="Endereço da origem, se visível")
    destination_address: Optional[str] = Field(None, description="Endereço do destino, se visível")
    start_time: str = Field(..., description="Horário de início no formato HH:MM (ex: 07:03)")
    end_time: str = Field(..., description="Horário de chegada no formato HH:MM (ex: 07:25)")
    distance_km: float = Field(..., description="Distância percorrida em quilômetros (ex: 11.0)")
    duration_min: int = Field(..., description="Duração do deslocamento em minutos (ex: 22)")


class VisitEvent(BaseModel):
    """Representa uma visita ou permanência em um local específico."""
    place_name: str = Field(..., description="Nome do local visitado (ex: Supermercado Portal)")
    address: Optional[str] = Field(None, description="Endereço do local, se visível")
    start_time: str = Field(..., description="Horário de chegada no formato HH:MM (ex: 07:25)")
    end_time: str = Field(..., description="Horário de saída no formato HH:MM (ex: 07:36)")
    duration_min: Optional[int] = Field(None, description="Tempo de permanência em minutos, se informado")


class TimelineDay(BaseModel):
    """Estrutura completa com todos os dados extraídos de uma captura da Linha do Tempo."""
    date: str = Field(..., description="Data dos deslocamentos no formato YYYY-MM-DD")
    total_km: Optional[float] = Field(None, description="Quilometragem total do dia reportada no cabeçalho")
    total_driving_min: Optional[int] = Field(None, description="Tempo total dirigindo em minutos reportado no cabeçalho")
    displacements: List[DisplacementEvent] = Field(default_factory=list, description="Lista de trajetos realizados")
    visits: List[VisitEvent] = Field(default_factory=list, description="Lista de locais visitados")
