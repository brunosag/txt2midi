import random
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
from typing import Final, override

from config import NOTAS_MIDI_BASE
from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoPausa,
    EventoTempo,
)
from domain.models import ParsingContext, PlaybackSettings


class ParsingMode(StrEnum):
    """Enumeração para os modos de parsing suportados."""

    MML = 'mml'
    STANDARD = 'standard'


class MusicParser(ABC):
    """Estratégia abstrata para converter texto em eventos musicais."""

    @abstractmethod
    def parse(self, texto: str, settings: PlaybackSettings) -> list[EventoMusical]:
        """Converte o texto de entrada em uma lista de eventos musicais."""


class MMLParser(MusicParser):
    """Estratégia concreta para o formato MML (Music Macro Language)."""

    TOKEN_REGEX_MML: Final[re.Pattern[str]] = re.compile(
        r"""
        (?P<note>[A-H][#\+\-b]?)      # Notas: A-H, mais acidentes
        |(?P<rest>[RP])               # Pausas
        |(?P<octave_set>O(?=\d))      # Definir oitava: O5
        |(?P<octave_up>>+)            # Subir oitava
        |(?P<octave_down><+)          # Descer oitava
        |(?P<length_set>L(?=\d))      # Comprimento padrão: L4
        |(?P<tempo>T(?=\d))           # Tempo: T120
        |(?P<volume>V(?=\d))          # Volume: V100
        |(?P<instrument>I(?=\d))      # Instrumento: I0
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    @override
    def parse(self, texto: str, settings: PlaybackSettings) -> list[EventoMusical]:
        context = ParsingContext(settings)
        eventos = self._initialize_events(context)

        pos = 0
        text_len = len(texto)

        while pos < text_len:
            match = self.TOKEN_REGEX_MML.match(texto, pos)
            if not match:
                pos += 1
                continue

            pos = self._process_token(match, texto, pos, context, eventos)

        return eventos

    def _initialize_events(self, context: ParsingContext) -> list[EventoMusical]:
        """Cria a lista inicial de eventos com configurações padrão."""
        return [
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

    def _process_token(
        self,
        match: re.Match[str],
        text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> int:
        """Despacha o token encontrado para o manipulador correto."""
        token_type = match.lastgroup
        if not token_type:
            return pos + 1

        match token_type:
            case 'note':
                return self._handle_note(match, text, pos, context, eventos)
            case 'rest':
                return self._handle_rest(match, text, pos, context, eventos)
            case 'octave_set' | 'length_set' | 'tempo' | 'volume' | 'instrument':
                return self._handle_setting(match, text, pos, context, eventos)
            case 'octave_up' | 'octave_down':
                return self._handle_octave_shift(match, context)
            case _:
                return match.end()

    def _handle_note(
        self,
        match: re.Match[str],
        text: str,
        start_idx: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> int:
        curr_pos = match.end()
        duration, new_pos = self._calculate_duration(text, curr_pos, context)
        token_str = match.group()

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
                source_length=new_pos - start_idx,
            )
        )
        context.tempo_evento += duration
        return new_pos

    def _handle_rest(
        self,
        match: re.Match[str],
        text: str,
        start_idx: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> int:
        curr_pos = match.end()
        duration, new_pos = self._calculate_duration(text, curr_pos, context)

        eventos.append(
            EventoPausa(
                tempo=context.tempo_evento,
                duracao=duration,
                source_index=start_idx,
                source_length=new_pos - start_idx,
            )
        )
        context.tempo_evento += duration
        return new_pos

    def _handle_setting(
        self,
        match: re.Match[str],
        text: str,
        start_idx: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> int:
        token_type = match.lastgroup
        curr_pos = match.end()
        val, new_pos = self._read_number(text, curr_pos)
        length = new_pos - start_idx

        match token_type:
            case 'octave_set':
                context.octave = max(0, min(val, 10))
            case 'length_set':
                context.default_length = max(1, val)
            case 'tempo':
                context.bpm = max(1, val)
                eventos.append(
                    EventoTempo(
                        tempo=context.tempo_evento,
                        bpm=context.bpm,
                        source_index=start_idx,
                        source_length=length,
                    )
                )
            case 'volume':
                context.volume = max(0, min(val, 127))
            case 'instrument':
                context.instrument_id = max(0, min(val, 127))
                eventos.append(
                    EventoInstrumento(
                        tempo=context.tempo_evento,
                        instrument_id=context.instrument_id,
                        source_index=start_idx,
                        source_length=length,
                    )
                )

        return new_pos

    def _handle_octave_shift(
        self,
        match: re.Match[str],
        context: ParsingContext,
    ) -> int:
        token_type = match.lastgroup
        token_str = match.group()

        if token_type == 'octave_up':
            context.octave = min(context.octave + len(token_str), 10)
        elif token_type == 'octave_down':
            context.octave = max(context.octave - len(token_str), 0)

        return match.end()

    def _read_number(self, text: str, pos: int) -> tuple[int, int]:
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


class StandardParser(MusicParser):
    """Estratégia concreta para o formato Padrão usando Dispatch Table."""

    NOTE_DURATION: Final[float] = 1.0

    def __init__(self) -> None:
        self.dispatch_table: dict[
            str,
            Callable[
                [str, int, ParsingContext, list[EventoMusical], int | None],
                tuple[int | None, int],
            ],
        ] = self._build_dispatch_table()

    @override
    def parse(self, texto: str, settings: PlaybackSettings) -> list[EventoMusical]:
        context = ParsingContext(settings)
        eventos = self._initialize_events(context)

        last_note_pitch: int | None = None
        pos = 0
        text_len = len(texto)

        while pos < text_len:
            char = texto[pos]
            upper_char = char.upper()

            handler = self.dispatch_table.get(upper_char, self._handle_default)
            last_note_pitch, pos = handler(
                texto, pos, context, eventos, last_note_pitch
            )

        return eventos

    def _initialize_events(self, context: ParsingContext) -> list[EventoMusical]:
        return [
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

    def _build_dispatch_table(self) -> dict[str, Callable]:
        """Construir a tabela de mapeamento Caractere -> Função."""
        table = {
            '+': self._handle_octave_up,
            '-': self._handle_octave_down,
            ' ': self._handle_volume,
            '?': self._handle_random_note,
            '\n': self._handle_newline,
            ';': self._handle_rest,
            'B': self._handle_b_context,
        }

        for char in 'ACDEFGH':
            table[char] = self._handle_note

        for char in 'OIU':
            table[char] = self._handle_vowel

        return table

    def _handle_default(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        """Estende a duração da última nota, se houver."""
        for i in range(len(eventos) - 1, -1, -1):
            ev = eventos[i]
            if isinstance(ev, EventoNota):
                ev.duracao += self.NOTE_DURATION
                ev.source_length += 1
                context.tempo_evento += self.NOTE_DURATION
                return last_pitch, pos + 1

        return last_pitch, pos + 1

    def _handle_note(
        self,
        text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        _last_pitch: int | None,
    ) -> tuple[int, int]:
        char = text[pos].upper()
        pitch = 70 if char == 'H' else NOTAS_MIDI_BASE.get(char, 60)
        pitch += (context.octave - 5) * 12
        pitch = max(0, min(127, pitch))

        eventos.append(
            EventoNota(
                tempo=context.tempo_evento,
                pitch=pitch,
                volume=context.volume,
                duracao=self.NOTE_DURATION,
                source_index=pos,
                source_length=1,
            )
        )
        context.tempo_evento += self.NOTE_DURATION
        return pitch, pos + 1

    def _handle_b_context(
        self,
        text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        """Trata o caso ambíguo do 'B': Nota B ou comando BPM+."""
        if text.startswith('BPM+', pos):
            context.bpm += 80
            eventos.append(
                EventoTempo(
                    tempo=context.tempo_evento,
                    bpm=context.bpm,
                    source_index=pos,
                    source_length=4,
                )
            )
            return last_pitch, pos + 4

        return self._handle_note(text, pos, context, eventos, last_pitch)

    def _handle_vowel(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        current_pitch = last_pitch

        if last_pitch is not None:
            eventos.append(
                EventoNota(
                    tempo=context.tempo_evento,
                    pitch=last_pitch,
                    volume=context.volume,
                    duracao=self.NOTE_DURATION,
                    source_index=pos,
                    source_length=1,
                )
            )
        else:
            context.instrument_id = 124  # Telefone (GM 124)
            eventos.append(
                EventoInstrumento(
                    tempo=context.tempo_evento,
                    instrument_id=124,
                    source_index=pos,
                    source_length=0,
                )
            )
            note_pitch = 60
            eventos.append(
                EventoNota(
                    tempo=context.tempo_evento,
                    pitch=note_pitch,
                    volume=context.volume,
                    duracao=self.NOTE_DURATION,
                    source_index=pos,
                    source_length=1,
                )
            )
            current_pitch = note_pitch

        context.tempo_evento += self.NOTE_DURATION
        return current_pitch if current_pitch is not None else 60, pos + 1

    def _handle_octave_up(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        _eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        context.octave = min(context.octave + 1, 10)
        return last_pitch, pos + 1

    def _handle_octave_down(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        _eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        context.octave = max(context.octave - 1, 0)
        return last_pitch, pos + 1

    def _handle_volume(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        _eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        new_vol = context.volume * 2
        context.volume = min(127, new_vol) if new_vol > 0 else 127
        return last_pitch, pos + 1

    def _handle_random_note(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        _last_pitch: int | None,
    ) -> tuple[int, int]:
        random_note = random.choice(list(NOTAS_MIDI_BASE.values()))
        pitch = random_note + ((context.octave - 5) * 12)
        pitch = max(0, min(127, pitch))

        eventos.append(
            EventoNota(
                tempo=context.tempo_evento,
                pitch=pitch,
                volume=context.volume,
                duracao=self.NOTE_DURATION,
                source_index=pos,
                source_length=1,
            )
        )
        context.tempo_evento += self.NOTE_DURATION
        return pitch, pos + 1

    def _handle_newline(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        context.instrument_id = random.randint(0, 127)
        eventos.append(
            EventoInstrumento(
                tempo=context.tempo_evento,
                instrument_id=context.instrument_id,
                source_index=pos,
                source_length=1,
            )
        )
        return last_pitch, pos + 1

    def _handle_rest(
        self,
        _text: str,
        pos: int,
        context: ParsingContext,
        eventos: list[EventoMusical],
        last_pitch: int | None,
    ) -> tuple[int | None, int]:
        eventos.append(
            EventoPausa(
                tempo=context.tempo_evento,
                duracao=self.NOTE_DURATION,
                source_index=pos,
                source_length=1,
            )
        )
        context.tempo_evento += self.NOTE_DURATION
        return last_pitch, pos + 1


class TextParser:
    """Facade para selecionar a estratégia de parsing apropriada."""

    def parse(
        self, texto: str, settings: PlaybackSettings, mode: ParsingMode
    ) -> list[EventoMusical]:
        match mode:
            case ParsingMode.STANDARD:
                strategy = StandardParser()
            case ParsingMode.MML:
                strategy = MMLParser()

        return strategy.parse(texto, settings)
