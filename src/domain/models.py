from dataclasses import dataclass


@dataclass
class PlaybackSettings:
    """Configuração definida pelo usuário na interface."""

    bpm: int = 120
    volume: int = 100
    octave: int = 5
    instrument_id: int = 0


class ParsingContext:
    """Estado transitório usado apenas durante o processo de análise."""

    def __init__(self, settings: PlaybackSettings) -> None:
        self.octave: int = settings.octave
        self.volume: int = settings.volume
        self.bpm: int = settings.bpm
        self.instrument_id: int = settings.instrument_id
        self.default_length: float = 4.0  # Default to Quarter note (1/4)
        self.event_time: float = 0.0
