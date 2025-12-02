from dataclasses import dataclass


@dataclass
class MusicalEvent:
    """Classe base para todos os eventos musicais."""

    time: float
    source_index: int
    source_length: int


@dataclass
class TempoEvent(MusicalEvent):
    """Evento de mudança de tempo (BPM)."""

    bpm: int


@dataclass
class InstrumentEvent(MusicalEvent):
    """Evento de mudança de instrumento."""

    instrument_id: int


@dataclass
class NoteEvent(MusicalEvent):
    """Evento de nota musical."""

    pitch: int
    volume: int
    duration: float


@dataclass
class SpecificNoteEvent(MusicalEvent):
    """Evento de nota com instrumento específico."""

    instrument_id: int
    pitch: int
    volume: int
    duration: float


@dataclass
class RestEvent(MusicalEvent):
    """Evento de pausa (silêncio)."""

    duration: float
