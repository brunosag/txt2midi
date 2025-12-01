import random
import re
from typing import Literal

from config import NOTAS_MIDI_BASE
from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoPausa,
    EventoTempo,
)
from domain.models import ParsingContext, PlaybackSettings

ParsingMode = Literal['mml', 'standard']


class TextParser:
    """Parses text into musical events using specific strategies."""

    TOKEN_REGEX_MML = re.compile(
        r"""
        (?P<note>[A-H][#\+\-b]?)      # Notes: A-H, plus accidentals
        |(?P<rest>[RP])               # Rests
        |(?P<octave_set>O(?=\d))      # Octave set: O5
        |(?P<octave_up>>+)            # Octave up
        |(?P<octave_down><+)          # Octave down
        |(?P<length_set>L(?=\d))      # Default length: L4
        |(?P<tempo>T(?=\d))           # Tempo: T120
        |(?P<volume>V(?=\d))          # Volume: V100
        |(?P<instrument>I(?=\d))      # Instrument: I0
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def parse(
        self, texto: str, settings: PlaybackSettings, mode: ParsingMode
    ) -> list[EventoMusical]:
        if mode == 'standard':
            return self._parse_standard(texto, settings)
        return self._parse_mml(texto, settings)

    def _parse_mml(self, texto: str, settings: PlaybackSettings) -> list[EventoMusical]:
        context = ParsingContext(settings)
        eventos: list[EventoMusical] = [
            EventoTempo(
                tempo=0.0,
                bpm=context.bpm,
                source_index=0,
                source_length=0,
            ),
            EventoInstrumento(
                tempo=0.0,
                instrument_id=context.instrument_id,
                source_index=0,
                source_length=0,
            ),
        ]

        pos = 0
        text_len = len(texto)

        while pos < text_len:
            match = self.TOKEN_REGEX_MML.match(texto, pos)
            if not match:
                pos += 1
                continue

            token_type = match.lastgroup
            token_str = match.group()
            start_idx = match.start()
            curr_pos = match.end()

            if token_type == 'note':
                duration, new_pos = self._calculate_duration(texto, curr_pos, context)
                length = new_pos - start_idx

                base_char = token_str[0].upper()
                accidental = token_str[1] if len(token_str) > 1 else None

                pitch = NOTAS_MIDI_BASE.get(base_char, 60)
                if accidental in ('#', '+'):
                    pitch += 1
                elif accidental in ('b', '-'):
                    pitch -= 1

                pitch += (context.octave - 5) * 12
                pitch = max(0, min(127, pitch))

                eventos.append(
                    EventoNota(
                        tempo=context.tempo_evento,
                        pitch=pitch,
                        volume=context.volume,
                        duracao=duration,
                        source_index=start_idx,
                        source_length=length,
                    )
                )
                context.tempo_evento += duration
                pos = new_pos

            elif token_type == 'rest':
                duration, new_pos = self._calculate_duration(texto, curr_pos, context)
                length = new_pos - start_idx

                eventos.append(
                    EventoPausa(
                        tempo=context.tempo_evento,
                        duracao=duration,
                        source_index=start_idx,
                        source_length=length,
                    )
                )
                context.tempo_evento += duration
                pos = new_pos

            elif token_type in (
                'octave_set',
                'length_set',
                'tempo',
                'volume',
                'instrument',
            ):
                val, new_pos = self._read_number(texto, curr_pos)
                length = new_pos - start_idx

                if token_type == 'octave_set':
                    context.octave = max(0, min(val, 10))
                elif token_type == 'length_set':
                    context.default_length = max(1, val)
                elif token_type == 'tempo':
                    context.bpm = max(1, val)
                    eventos.append(
                        EventoTempo(
                            tempo=context.tempo_evento,
                            bpm=context.bpm,
                            source_index=start_idx,
                            source_length=length,
                        )
                    )
                elif token_type == 'volume':
                    context.volume = max(0, min(val, 127))
                elif token_type == 'instrument':
                    context.instrument_id = max(0, min(val, 127))
                    eventos.append(
                        EventoInstrumento(
                            tempo=context.tempo_evento,
                            instrument_id=context.instrument_id,
                            source_index=start_idx,
                            source_length=length,
                        )
                    )
                pos = new_pos

            elif token_type == 'octave_up':
                context.octave = min(context.octave + len(token_str), 10)
                pos = curr_pos

            elif token_type == 'octave_down':
                context.octave = max(context.octave - len(token_str), 0)
                pos = curr_pos

            else:
                pos = curr_pos

        return eventos

    def _parse_standard(
        self, texto: str, settings: PlaybackSettings
    ) -> list[EventoMusical]:
        """Implements the 'Padrão' logic."""
        context = ParsingContext(settings)
        # Fixed duration for standard mode notes (e.g. 1 beat)
        NOTE_DURATION = 1.0

        eventos: list[EventoMusical] = [
            EventoTempo(tempo=0.0, bpm=context.bpm, source_index=0, source_length=0),
            EventoInstrumento(
                tempo=0.0,
                instrument_id=context.instrument_id,
                source_index=0,
                source_length=0,
            ),
        ]

        pos = 0
        text_len = len(texto)
        last_note_pitch: int | None = None

        while pos < text_len:
            char = texto[pos]
            start_idx = pos

            # 1. BPM+ Check (Lookahead for sequence)
            if texto.startswith('BPM+', pos):
                context.bpm += 80
                eventos.append(
                    EventoTempo(
                        tempo=context.tempo_evento,
                        bpm=context.bpm,
                        source_index=start_idx,
                        source_length=4,
                    )
                )
                pos += 4
                continue

            # 2. Newline: Random Instrument
            if char == '\n':
                context.instrument_id = random.randint(0, 127)
                eventos.append(
                    EventoInstrumento(
                        tempo=context.tempo_evento,
                        instrument_id=context.instrument_id,
                        source_index=start_idx,
                        source_length=1,
                    )
                )
                pos += 1
                continue

            # 3. Notes (A-G)
            upper_char = char.upper()
            if 'A' <= upper_char <= 'G':
                pitch = NOTAS_MIDI_BASE.get(upper_char, 60)
                pitch += (context.octave - 5) * 12
                pitch = max(0, min(127, pitch))

                eventos.append(
                    EventoNota(
                        tempo=context.tempo_evento,
                        pitch=pitch,
                        volume=context.volume,
                        duracao=NOTE_DURATION,
                        source_index=start_idx,
                        source_length=1,
                    )
                )
                last_note_pitch = pitch
                context.tempo_evento += NOTE_DURATION
                pos += 1
                continue

            # 4. Note H (Bb / A#) -> Base 70
            if upper_char == 'H':
                pitch = 70
                pitch += (context.octave - 5) * 12
                pitch = max(0, min(127, pitch))

                eventos.append(
                    EventoNota(
                        tempo=context.tempo_evento,
                        pitch=pitch,
                        volume=context.volume,
                        duracao=NOTE_DURATION,
                        source_index=start_idx,
                        source_length=1,
                    )
                )
                last_note_pitch = pitch
                context.tempo_evento += NOTE_DURATION
                pos += 1
                continue

            # 5. Octave Increase (+) / Decrease (-)
            if char == '+':
                context.octave = min(context.octave + 1, 10)
                pos += 1
                continue
            if char == '-':
                context.octave = max(context.octave - 1, 0)
                pos += 1
                continue

            # 6. Volume (Space)
            if char == ' ':
                new_vol = context.volume * 2
                context.volume = min(127, new_vol) if new_vol > 0 else 127
                pos += 1
                continue

            # 7. Vowels (O, I, U) - Repeat or Telephone
            if upper_char in ('O', 'I', 'U'):
                if last_note_pitch is not None:
                    # Repeat last note
                    eventos.append(
                        EventoNota(
                            tempo=context.tempo_evento,
                            pitch=last_note_pitch,
                            volume=context.volume,
                            duracao=NOTE_DURATION,
                            source_index=start_idx,
                            source_length=1,
                        )
                    )
                else:
                    # Telephone Ring (GM 124 in 0-based indexing)
                    context.instrument_id = 124
                    eventos.append(
                        EventoInstrumento(
                            tempo=context.tempo_evento,
                            instrument_id=context.instrument_id,
                            source_index=start_idx,
                            source_length=0,
                        )
                    )
                    # Play a default note to make sound audible
                    note_pitch = 60
                    eventos.append(
                        EventoNota(
                            tempo=context.tempo_evento,
                            pitch=note_pitch,
                            volume=context.volume,
                            duracao=NOTE_DURATION,
                            source_index=start_idx,
                            source_length=1,
                        )
                    )
                    last_note_pitch = note_pitch

                context.tempo_evento += NOTE_DURATION
                pos += 1
                continue

            # 8. Random Note (?)
            if char == '?':
                random_note = random.choice(list(NOTAS_MIDI_BASE.values()))
                pitch = random_note + ((context.octave - 5) * 12)
                pitch = max(0, min(127, pitch))

                eventos.append(
                    EventoNota(
                        tempo=context.tempo_evento,
                        pitch=pitch,
                        volume=context.volume,
                        duracao=NOTE_DURATION,
                        source_index=start_idx,
                        source_length=1,
                    )
                )
                last_note_pitch = pitch
                context.tempo_evento += NOTE_DURATION
                pos += 1
                continue

            # 9. Rest (;)
            if char == ';':
                eventos.append(
                    EventoPausa(
                        tempo=context.tempo_evento,
                        duracao=NOTE_DURATION,
                        source_index=start_idx,
                        source_length=1,
                    )
                )
                context.tempo_evento += NOTE_DURATION
                pos += 1
                continue

            # 10. Default / Other characters: Continue current sound
            found_note = False
            for i in range(len(eventos) - 1, -1, -1):
                ev = eventos[i]
                if isinstance(ev, EventoNota):
                    ev.duracao += NOTE_DURATION
                    # Extend the source length to cover this character as well
                    ev.source_length += 1
                    context.tempo_evento += NOTE_DURATION
                    found_note = True
                    break

            if not found_note:
                # If no note is playing, act as pause
                pass

            pos += 1

        return eventos

    def _read_number(self, text: str, pos: int) -> tuple[int, int]:
        """Reads a number starting at pos. Returns (value, new_pos)."""
        match = re.match(r'\d+', text[pos:])
        if match:
            return int(match.group()), pos + match.end()
        return 0, pos

    def _calculate_duration(
        self,
        text: str,
        pos: int,
        context: ParsingContext,
    ) -> tuple[float, int]:
        """Determines duration based on optional number and dots."""
        value_num, new_pos = self._read_number(text, pos)
        length_val = value_num if value_num > 0 else context.default_length

        duration = 4.0 / length_val
        dots = 0
        while new_pos < len(text) and text[new_pos] == '.':
            dots += 1
            new_pos += 1

        if dots > 0:
            original_dur = duration
            add = original_dur * 0.5
            for _ in range(dots):
                duration += add
                add *= 0.5

        return duration, new_pos
