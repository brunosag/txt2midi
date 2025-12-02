import logging
from pathlib import Path

from midiutil import MIDIFile

from domain.events import (
    InstrumentEvent,
    MusicalEvent,
    NoteEvent,
    SpecificNoteEvent,
    TempoEvent,
)

logger = logging.getLogger(__name__)


class MIDIExporter:
    """Gera e salva um arquivo MIDI a partir da lista de eventos."""

    def save(
        self,
        events: list[MusicalEvent],
        file_path: Path,
    ) -> None:
        """Criar o objeto `MIDIFile` e o salvar no disco."""
        midi = MIDIFile(1, deinterleave=False)

        track = 0
        channel = 0
        initial_tempo_defined = False
        initial_instrument_defined = False

        for event in events:
            if isinstance(event, TempoEvent) and not initial_tempo_defined:
                midi.addTempo(
                    track=track,
                    time=event.time,
                    tempo=event.bpm,
                )
                initial_tempo_defined = True

            elif isinstance(event, InstrumentEvent) and not initial_instrument_defined:
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=event.time,
                    program=event.instrument_id,
                )
                initial_instrument_defined = True

            elif isinstance(event, (NoteEvent, SpecificNoteEvent)):
                midi.addNote(
                    track=track,
                    channel=channel,
                    pitch=event.pitch,
                    time=event.time,
                    duration=event.duration,
                    volume=event.volume,
                )

            # Mudanças de tempo/instrumento no meio da música
            if isinstance(event, TempoEvent) and initial_tempo_defined:
                midi.addTempo(
                    track=track,
                    time=event.time,
                    tempo=event.bpm,
                )

            if isinstance(event, InstrumentEvent) and initial_instrument_defined:
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=event.time,
                    program=event.instrument_id,
                )

        with file_path.open('wb') as output_file:
            midi.writeFile(output_file)
