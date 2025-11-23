import logging
from pathlib import Path

from midiutil import MIDIFile

from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoNotaEspecifica,
    EventoTempo,
)

logger = logging.getLogger(__name__)


class MIDIExporter:
    """Gera e salva um arquivo MIDI a partir da lista de eventos."""

    def save(
        self,
        eventos: list[EventoMusical],
        caminho_arquivo: Path,
    ) -> None:
        """Criar o objeto `MIDIFile` e o salvar no disco."""
        midi = MIDIFile(1, deinterleave=False)

        track = 0
        channel = 0
        tempo_inicial_definido = False
        instrumento_inicial_definido = False

        for evento in eventos:
            if isinstance(evento, EventoTempo) and not tempo_inicial_definido:
                midi.addTempo(
                    track=track,
                    time=evento.tempo,
                    tempo=evento.bpm,
                )
                tempo_inicial_definido = True

            elif (
                isinstance(evento, EventoInstrumento)
                and not instrumento_inicial_definido
            ):
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=evento.tempo,
                    program=evento.instrument_id,
                )
                instrumento_inicial_definido = True

            elif isinstance(evento, (EventoNota, EventoNotaEspecifica)):
                midi.addNote(
                    track=track,
                    channel=channel,
                    pitch=evento.pitch,
                    time=evento.tempo,
                    duration=evento.duracao,
                    volume=evento.volume,
                )

            # Mudanças de tempo/instrumento no meio da música
            if isinstance(evento, EventoTempo) and tempo_inicial_definido:
                midi.addTempo(
                    track=track,
                    time=evento.tempo,
                    tempo=evento.bpm,
                )

            if isinstance(evento, EventoInstrumento) and instrumento_inicial_definido:
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=evento.tempo,
                    program=evento.instrument_id,
                )

        with caminho_arquivo.open('wb') as output_file:
            midi.writeFile(output_file)
