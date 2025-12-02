from dataclasses import dataclass
from pathlib import Path
from typing import Final, NamedTuple

import mido  # pyright: ignore[reportMissingTypeStubs]

from config import MIDI_BASE_NOTES

MIN_DURATION_THRESHOLD: Final[float] = 0.01
DURATION_EPSILON: Final[float] = 1e-5
DEFAULT_BPM: Final[int] = 120


@dataclass
class NoteEvent:
    start_ticks: int
    duration_ticks: int
    pitch: int
    velocity: int
    instrument: int

    @property
    def end_ticks(self) -> int:
        return self.start_ticks + self.duration_ticks


class ConversionResult(NamedTuple):
    text: str
    initial_instrument: int
    initial_velocity: int
    initial_bpm: int


class MIDIImporter:
    """Converte arquivos MIDI para o formato de texto da aplicação, forçando monofonia."""

    def __init__(self) -> None:
        self._pitch_map: dict[int, str] = {
            v % 12: k for k, v in MIDI_BASE_NOTES.items()
        }
        self._duration_lookup: list[tuple[float, int, int]] = (
            self._build_duration_table()
        )

    def load(self, filepath: Path) -> ConversionResult:
        """Carrega um arquivo MIDI e retorna o resultado da conversão."""
        mid: mido.MidiFile = mido.MidiFile(filename=filepath)
        ticks_per_beat = mid.ticks_per_beat

        raw_events: list[NoteEvent] = self._parse_track_events(mid)
        processed_events: list[NoteEvent] = self._resolve_monophony(events=raw_events)

        initial_bpm: int = self._get_initial_bpm(mid)

        if not processed_events:
            return ConversionResult(
                text='',
                initial_instrument=0,
                initial_velocity=100,
                initial_bpm=initial_bpm,
            )

        initial_inst: int = processed_events[0].instrument
        initial_vol: int = processed_events[0].velocity

        text_output: str = self._transpile_to_text(
            events=processed_events,
            tpb=ticks_per_beat,
            init_inst=initial_inst,
            init_vol=initial_vol,
        )

        return ConversionResult(
            text=text_output,
            initial_instrument=initial_inst,
            initial_velocity=initial_vol,
            initial_bpm=initial_bpm,
        )

    def _get_initial_bpm(self, mid: mido.MidiFile) -> int:
        """Escaneia as faixas em busca da primeira mensagem `set_tempo`."""
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    return int(mido.tempo2bpm(msg.tempo))
        return DEFAULT_BPM

    def _parse_track_events(self, mid: mido.MidiFile) -> list[NoteEvent]:
        """Extrai eventos lineares de todas as faixas."""
        events = []

        for track in mid.tracks:
            curr_ticks = 0
            curr_inst = 0
            active_notes: dict[int, tuple[int, int, int]] = {}

            for msg in track:
                curr_ticks += msg.time

                if msg.type == 'program_change':
                    curr_inst = msg.program
                    continue

                is_note_on = msg.type == 'note_on' and msg.velocity > 0
                is_note_off = msg.type == 'note_off' or (
                    msg.type == 'note_on' and msg.velocity == 0
                )

                if is_note_on:
                    if msg.note not in active_notes:
                        active_notes[msg.note] = (curr_ticks, msg.velocity, curr_inst)

                elif is_note_off and msg.note in active_notes:
                    start, vel, inst = active_notes.pop(msg.note)
                    duration = curr_ticks - start
                    if duration > 0:
                        events.append(
                            NoteEvent(
                                start_ticks=start,
                                duration_ticks=duration,
                                pitch=msg.note,
                                velocity=vel,
                                instrument=inst,
                            )
                        )

        return events

    def _resolve_monophony(self, events: list[NoteEvent]) -> list[NoteEvent]:
        """Ordena eventos e trata sobreposições.

        Estratégia: Prioridade de melodia (Nota mais aguda) -> Truncar sobreposições.
        """
        events.sort(key=lambda x: (x.start_ticks, -x.pitch))

        if not events:
            return []

        unique_events = []
        last_start = -1

        for note in events:
            if note.start_ticks > last_start:
                unique_events.append(note)
                last_start: int = note.start_ticks

        processed = []
        count: int = len(unique_events)

        for i in range(count):
            curr = unique_events[i]

            if i < count - 1:
                nxt = unique_events[i + 1]
                delta = nxt.start_ticks - curr.start_ticks
                curr.duration_ticks = min(curr.duration_ticks, delta)

            processed.append(curr)

        return processed

    def _transpile_to_text(
        self, events: list[NoteEvent], tpb: int, init_inst: int, init_vol: int
    ) -> str:
        """Converte eventos limpos para o formato de string específico do domínio."""
        parts = []
        curr_ticks = 0
        curr_octave = 5
        curr_vol: int = init_vol
        curr_inst: int = init_inst

        for note in events:
            gap: int = note.start_ticks - curr_ticks
            if gap > 0:
                rest_str: str = self._format_duration(char='R', beats=gap / tpb)
                if rest_str:
                    parts.append(rest_str)

            curr_ticks: int = note.start_ticks

            if note.instrument != curr_inst:
                parts.append(f'I{note.instrument}')
                curr_inst: int = note.instrument

            if note.velocity != curr_vol:
                parts.append(f'V{note.velocity}')
                curr_vol: int = note.velocity

            target_octave: int = note.pitch // 12
            diff: int = target_octave - curr_octave
            if diff == 1:
                parts.append('>')
            elif diff == -1:
                parts.append('<')
            elif diff != 0:
                parts.append(f'O{target_octave}')
            curr_octave: int = target_octave

            pitch_class: int = note.pitch % 12
            char: str | None = self._pitch_map.get(pitch_class)

            if not char:
                prev_pitch: int = (pitch_class - 1) % 12
                base: str = self._pitch_map.get(prev_pitch, 'C')
                char = f'{base}#'

            duration_str: str = self._format_duration(
                char, beats=note.duration_ticks / tpb
            )
            parts.append(duration_str)

            curr_ticks += note.duration_ticks

        return ' '.join(parts)

    def _build_duration_table(self) -> list[tuple[float, int, int]]:
        """Cria uma tabela de consulta para durações de notas padrão."""
        table = []
        base_lengths: list[int] = [1, 2, 4, 8, 16, 32, 64]

        for length in base_lengths:
            base_dur: float = 4.0 / length
            table.append((base_dur, length, 0))
            table.append((base_dur * 1.5, length, 1))
            table.append((base_dur * 1.75, length, 2))

        return table

    def _format_duration(self, char: str, beats: float) -> str:
        """Encontra a duração padrão mais próxima usando a tabela de consulta."""
        if beats <= MIN_DURATION_THRESHOLD:
            return ''

        best_match: tuple[int, int] = (0, 0)
        min_error: float = float('inf')

        for dur, length, dots in self._duration_lookup:
            error: float = abs(dur - beats)
            if error < min_error:
                min_error = error
                best_match = (length, dots)

                if error < DURATION_EPSILON:
                    break

        length, dots = best_match
        return f'{char}{length}{"." * dots}'
