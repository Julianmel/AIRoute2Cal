"""Modelos de dados Pydantic para estruturação de todos os eventos da Linha do Tempo."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DisplacementEvent(BaseModel):
    """Representa qualquer deslocamento (a pé, carro, bicicleta, transporte público, etc.)."""
    mode: str = Field(
        default="Dirigindo",
        description="Modo de transporte/deslocamento: 'Caminhando', 'A pé', 'Dirigindo', 'Bicicleta', 'Transporte público', etc.",
    )
    origin_name: str = Field(..., description="Nome do local de onde partiu (ex: Casa, Trabalho)")
    destination_name: str = Field(..., description="Nome do local de chegada (ex: Supermercado)")
    origin_address: Optional[str] = Field(None, description="Endereço da origem, se visível")
    destination_address: Optional[str] = Field(None, description="Endereço do destino, se visível")
    start_time: str = Field(..., description="Horário de início no formato HH:MM (ex: 07:03)")
    end_time: str = Field(..., description="Horário de chegada no formato HH:MM (ex: 07:25)")
    distance_km: Optional[float] = Field(None, description="Distância percorrida em km (ex: 0.4 para 400m ou 11.0)")
    duration_min: Optional[int] = Field(None, description="Duração do deslocamento em minutos")
    details: Optional[str] = Field(None, description="Informações extras visíveis (passos, calorias, observações)")


class VisitEvent(BaseModel):
    """Representa uma visita, parada ou permanência em um local."""
    place_name: str = Field(..., description="Nome do local visitado (ex: Supermercado Portal)")
    address: Optional[str] = Field(None, description="Endereço do local, se visível")
    start_time: str = Field(..., description="Horário de chegada no formato HH:MM (ex: 07:25)")
    end_time: str = Field(..., description="Horário de saída no formato HH:MM (ex: 07:36)")
    duration_min: Optional[int] = Field(None, description="Tempo de permanência em minutos, se informado")
    details: Optional[str] = Field(None, description="Notas extras visíveis (ex: 'Saiu às 07:03', 'Chegada às 19:33')")


class TimelineDay(BaseModel):
    """Estrutura completa com absolutamente todos os dados capturados da tela."""
    date: str = Field(..., description="Data dos eventos no formato YYYY-MM-DD")
    summary_stats: Optional[str] = Field(None, description="Resumo do cabeçalho da tela (ex: '73 km, 2h 33 min, 9 visitas')")
    total_km: Optional[float] = Field(None, description="Quilometragem total do dia reportada no cabeçalho")
    total_driving_min: Optional[int] = Field(None, description="Tempo total dirigindo em minutos")
    total_walking_min: Optional[int] = Field(None, description="Tempo total caminhando/a pé em minutos, se informado")
    total_steps: Optional[int] = Field(None, description="Total de passos registrados no dia, se visível")
    displacements: List[DisplacementEvent] = Field(
        default_factory=list,
        description="Lista de todos os deslocamentos (carro, a pé, bicicleta, ônibus, etc.)",
    )
    visits: List[VisitEvent] = Field(
        default_factory=list,
        description="Lista de todas as visitas, estadias e paradas",
    )
    additional_notes: Optional[str] = Field(None, description="Qualquer outro texto, anotação ou dado presente na tela")
