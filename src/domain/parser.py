import re

from config import NOTAS_MIDI_BASE
from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoPausa,
    EventoTempo,
)
from domain.models import ParsingContext, PlaybackSettings


class TextParser:
    """Parses MML-like text into musical events."""

    # Regex patterns for tokenizing
    TOKEN_REGEX = re.compile(
        r"""
        (?P<note>[A-G][#\+\-b]?)      # Notes: C, C#, Db, etc.
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

    def parse(self, texto: str, settings: PlaybackSettings) -> list[EventoMusical]:
        context = ParsingContext(settings)
        # Use keyword arguments to avoid inheritance ordering issues
        eventos: list[EventoMusical] = [
            EventoTempo(
                tempo=0.0,
                bpm=context.bpm,
                source_index=0,
            ),
            EventoInstrumento(
                tempo=0.0,
                instrument_id=context.instrument_id,
                source_index=0,
            ),
        ]

        pos = 0
        text_len = len(texto)

        while pos < text_len:
            # Try to match a token
            match = self.TOKEN_REGEX.match(texto, pos)
            if not match:
                pos += 1
                continue

            token_type = match.lastgroup
            token_str = match.group()
            start_idx = match.start()
            curr_pos = match.end()

            if token_type == 'note':
                duration, new_pos = self._calculate_duration(texto, curr_pos, context)

                # Parse Pitch
                base_char = token_str[0].upper()
                accidental = token_str[1] if len(token_str) > 1 else None

                pitch = NOTAS_MIDI_BASE.get(base_char, 60)
                if accidental in ('#', '+'):
                    pitch += 1
                elif accidental in ('b', '-'):
                    pitch -= 1

                # Adjust Octave
                pitch += (context.octave - 5) * 12

                # Validate range
                pitch = max(0, min(127, pitch))

                eventos.append(
                    EventoNota(
                        tempo=context.tempo_evento,
                        pitch=pitch,
                        volume=context.volume,
                        duracao=duration,
                        source_index=start_idx,
                    )
                )
                context.tempo_evento += duration
                pos = new_pos

            elif token_type == 'rest':
                duration, new_pos = self._calculate_duration(texto, curr_pos, context)
                eventos.append(
                    EventoPausa(
                        tempo=context.tempo_evento,
                        duracao=duration,
                        source_index=start_idx,
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
        """Determines duration based on optional number and dots.
        Returns (duration_in_beats, new_pos).
        """
        # Read number (e.g., '4' in 'C4')
        value_num, new_pos = self._read_number(text, pos)

        # If no number provided, use default
        length_val = value_num if value_num > 0 else context.default_length

        duration = 4.0 / length_val

        # Check for dots ('.')
        dots = 0
        while new_pos < len(text) and text[new_pos] == '.':
            dots += 1
            new_pos += 1

        # Apply dot modifier (adds half of previous value)
        if dots > 0:
            original_dur = duration
            add = original_dur * 0.5
            for _ in range(dots):
                duration += add
                add *= 0.5

        return duration, new_pos
