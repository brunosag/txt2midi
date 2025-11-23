from dataclasses import dataclass


@dataclass
class EventoMusical:
    """Classe base para todos os eventos musicais."""

    tempo: float  # Tempo em batidas


@dataclass
class EventoTempo(EventoMusical):
    """Evento de mudança de tempo (BPM)."""

    bpm: int


@dataclass
class EventoInstrumento(EventoMusical):
    """Evento de mudança de instrumento."""

    instrument_id: int


@dataclass
class EventoNota(EventoMusical):
    """Evento de nota musical."""

    pitch: int
    volume: int
    duracao: float


@dataclass
class EventoNotaEspecifica(EventoMusical):
    """Evento de nota com instrumento específico."""

    instrument_id: int
    pitch: int
    volume: int
    duracao: float


@dataclass
class EventoPausa(EventoMusical):
    """Evento de pausa (silêncio)."""

    duracao: float
