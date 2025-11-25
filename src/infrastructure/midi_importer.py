from dataclasses import dataclass
from pathlib import Path

import mido

from config import NOTAS_MIDI_BASE


@dataclass
class NoteEvent:
    start_ticks: int
    duration_ticks: int
    pitch: int
    velocity: int
    instrument: int


class MIDIImporter:
    """Converts MIDI files into the application's text format."""

    def load(self, filepath: Path) -> str:
        mid = mido.MidiFile(filepath)
        ticks_per_beat = mid.ticks_per_beat

        # 1. Read all notes from all tracks
        raw_events = []
        for track in mid.tracks:
            current_ticks = 0
            current_instrument = 0
            active_notes = {}  # pitch -> (start_ticks, velocity, instrument)

            for msg in track:
                current_ticks += msg.time

                if msg.type == 'program_change':
                    current_instrument = msg.program

                elif msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note not in active_notes:
                        active_notes[msg.note] = (
                            current_ticks,
                            msg.velocity,
                            current_instrument,
                        )

                elif (msg.type == 'note_off') or (
                    msg.type == 'note_on' and msg.velocity == 0
                ):
                    if msg.note in active_notes:
                        start_tick, vel, instr = active_notes.pop(msg.note)
                        duration = current_ticks - start_tick
                        if duration > 0:
                            raw_events.append(
                                NoteEvent(start_tick, duration, msg.note, vel, instr)
                            )

        # 2. Sort by Time ASC, then Pitch DESC (Melody priority)
        raw_events.sort(key=lambda x: (x.start_ticks, -x.pitch))

        # 3. Handle Polyphony (Truncation)
        processed_events = []
        if raw_events:
            unique_events = []
            last_start = -1
            # A. Filter simultaneous chords (keep highest)
            for note in raw_events:
                if note.start_ticks > last_start:
                    unique_events.append(note)
                    last_start = note.start_ticks

            # B. Truncate overlaps
            for i in range(len(unique_events) - 1):
                curr = unique_events[i]
                nxt = unique_events[i + 1]
                delta = nxt.start_ticks - curr.start_ticks
                curr.duration_ticks = min(curr.duration_ticks, delta)
                processed_events.append(curr)

            processed_events.append(unique_events[-1])

        # 4. Convert to Text
        current_ticks = 0
        current_octave = 5
        current_vol = -1
        current_inst = -1
        output_parts = []

        # UPDATED: Filter 'H' out of the map so we generate A# instead
        base_pitch_map = {v % 12: k for k, v in NOTAS_MIDI_BASE.items() if k != 'H'}

        for note in processed_events:
            # Rest logic
            gap_ticks = note.start_ticks - current_ticks
            if gap_ticks > 0:
                gap_beats = gap_ticks / ticks_per_beat
                rest_str = self._format_duration('R', gap_beats)
                if rest_str:
                    output_parts.append(rest_str)

            current_ticks = note.start_ticks

            # Instrument
            if note.instrument != current_inst:
                output_parts.append(f'I{note.instrument}')
                current_inst = note.instrument

            # Volume
            if note.velocity != current_vol:
                output_parts.append(f'V{note.velocity}')
                current_vol = note.velocity

            # Octave
            target_octave = note.pitch // 12
            if target_octave != current_octave:
                diff = target_octave - current_octave
                if diff == 1:
                    output_parts.append('>')
                elif diff == -1:
                    output_parts.append('<')
                else:
                    output_parts.append(f'O{target_octave}')
                current_octave = target_octave

            # Note Name
            pitch_class = note.pitch % 12
            note_char = base_pitch_map.get(pitch_class)

            if not note_char:
                # Fallback to sharp notation (e.g. A# for H/Bb)
                prev_pitch = (pitch_class - 1) % 12
                if prev_pitch in base_pitch_map:
                    note_char = base_pitch_map[prev_pitch] + '#'
                else:
                    note_char = 'C'

            # Duration
            beats = note.duration_ticks / ticks_per_beat
            note_str = self._format_duration(note_char, beats)
            output_parts.append(note_str)

            current_ticks += note.duration_ticks

        return ' '.join(output_parts)

    def _format_duration(self, char: str, beats: float) -> str:
        """Converts beat duration to syntax (C4, C4., etc)."""
        if beats <= 0.01:
            return ''

        target_beats = beats
        best_str = ''
        min_error = float('inf')
        base_lengths = [1, 2, 4, 8, 16, 32, 64]

        for length in base_lengths:
            base_dur = 4.0 / length
            for dots in range(3):  # 0, 1, or 2 dots
                dur = base_dur
                adder = base_dur * 0.5
                for _ in range(dots):
                    dur += adder
                    adder *= 0.5

                error = abs(dur - target_beats)
                if error < min_error:
                    min_error = error
                    dot_str = '.' * dots
                    best_str = f'{char}{length}{dot_str}'

        return best_str
