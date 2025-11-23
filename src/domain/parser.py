import random

from config import INSTRUMENTOS, MAX_MIDI_VALUE, NOTAS_MIDI_BASE
from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoNotaEspecifica,
    EventoPausa,
    EventoTempo,
)
from domain.models import ParsingContext, PlaybackSettings


class TextParser:
    """Implementa o mapeamento de texto para eventos musicais."""

    def _get_nota_midi(self, nota_char: str, oitava: int) -> int:
        """Calcular valor MIDI de uma nota (A-H) na oitava especificada."""
        base_nota = NOTAS_MIDI_BASE.get(nota_char.upper(), -1)
        if base_nota == -1:
            return -1

        # Ajustar oitava (base é 5)
        mod_oitava = (oitava - 5) * 12
        return base_nota + mod_oitava

    def parse(
        self,
        texto: str,
        settings: PlaybackSettings,
    ) -> list[EventoMusical]:
        """Processar texto e retornar lista de eventos musicais."""
        context = ParsingContext(settings)
        eventos = self._inicializar_eventos(context)

        i = 0
        while i < len(texto):
            # Checagem especial 'BPM+'
            if i + 3 < len(texto) and texto[i : i + 4].upper() == 'BPM+':
                self._tratar_bpm_mais(context, eventos)
                i += 4
                continue

            char = texto[i]
            self._processar_caractere(char, context, eventos)
            context.tempo_evento += 1.0
            i += 1

        return eventos

    def _inicializar_eventos(
        self,
        context: ParsingContext,
    ) -> list[EventoMusical]:
        """Inicializar a lista de eventos e configurar o estado."""
        if not hasattr(context, 'tempo_evento'):
            context.tempo_evento = 0.0
        if not hasattr(context, 'instrument_id'):
            pass

        return [
            EventoTempo(tempo=context.tempo_evento, bpm=context.bpm),
            EventoInstrumento(
                tempo=context.tempo_evento, instrument_id=context.instrument_id
            ),
        ]

    def _processar_caractere(
        self,
        char: str,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        """Processar um único caractere e atualizar estado/eventos."""
        char_lower = char.lower()

        if char_lower in 'abcdefgh':
            self._tratar_nota(char, context, eventos)
        elif char == ' ':
            self._tratar_volume(context)
        elif char in '+-':
            self._tratar_oitava(char, context)
        elif char_lower in 'oiu':
            self._tratar_vogal(context, eventos)
        elif char == '?':
            self._tratar_aleatorio(context, eventos)
        elif char == '\n':
            self._tratar_troca_instrumento(context, eventos)
        elif char == ';':
            self._tratar_pausa(context, eventos)

    def _tratar_bpm_mais(
        self,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        context.bpm += 80
        eventos.append(EventoTempo(tempo=context.tempo_evento, bpm=context.bpm))

    def _tratar_nota(
        self,
        char: str,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        nota_midi = self._get_nota_midi(char, context.octave)
        if 0 <= nota_midi <= MAX_MIDI_VALUE:
            eventos.append(
                EventoNota(
                    tempo=context.tempo_evento,
                    pitch=nota_midi,
                    volume=context.volume,
                    duracao=1.0,
                ),
            )
            context.last_note_midi = nota_midi
        else:
            self._tratar_pausa(context, eventos)

    def _tratar_volume(self, context: ParsingContext) -> None:
        context.volume = min(context.volume * 2, MAX_MIDI_VALUE)
        context.last_note_midi = -1

    def _tratar_oitava(self, char: str, context: ParsingContext) -> None:
        if char == '+':
            context.octave = min(context.octave + 1, 10)
        else:
            context.octave = max(context.octave - 1, 1)
        context.last_note_midi = -1

    def _tratar_vogal(
        self,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        if context.last_note_midi != -1:
            eventos.append(
                EventoNota(
                    tempo=context.tempo_evento,
                    pitch=context.last_note_midi,
                    volume=context.volume,
                    duracao=1.0,
                ),
            )
        else:
            nota_telefone = self._get_nota_midi('c', 5)
            eventos.append(
                EventoNotaEspecifica(
                    tempo=context.tempo_evento,
                    instrument_id=125,
                    pitch=nota_telefone,
                    volume=100,
                    duracao=1.0,
                ),
            )
            context.last_note_midi = -1

    def _tratar_aleatorio(
        self,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        nota_rand_char = random.choice('abcdefgh')
        self._tratar_nota(nota_rand_char, context, eventos)

    def _tratar_troca_instrumento(
        self,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        ids_instrumentos = [id_inst for id_inst, _ in INSTRUMENTOS]
        try:
            idx_atual = ids_instrumentos.index(context.instrument_id)
            idx_novo = (idx_atual + 1) % len(ids_instrumentos)
        except ValueError:
            idx_novo = 0

        context.instrument_id = ids_instrumentos[idx_novo]
        eventos.append(
            EventoInstrumento(
                tempo=context.tempo_evento,
                instrument_id=context.instrument_id,
            ),
        )
        context.last_note_midi = -1

    def _tratar_pausa(
        self,
        context: ParsingContext,
        eventos: list[EventoMusical],
    ) -> None:
        eventos.append(EventoPausa(tempo=context.tempo_evento, duracao=1.0))
        context.last_note_midi = -1
