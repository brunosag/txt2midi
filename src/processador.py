import random

from constantes import INSTRUMENTOS, MAX_MIDI_VALUE, NOTAS_MIDI_BASE
from eventos import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoNotaEspecifica,
    EventoPausa,
    EventoTempo,
)
from modelo import EstadoMusical


class MapeadorRegras:
    """Implementa o mapeamento de texto para eventos musicais."""

    def _get_nota_midi(self, nota_char: str, oitava: int) -> int:
        """Calcular valor MIDI de uma nota (A-H) na oitava especificada."""
        base_nota = NOTAS_MIDI_BASE.get(nota_char.upper(), -1)
        if base_nota == -1:
            return -1

        # Ajustar oitava (base é 5)
        mod_oitava = (oitava - 5) * 12
        return base_nota + mod_oitava

    def processar_texto(
        self,
        texto: str,
        estado_processamento: EstadoMusical,
    ) -> list[EventoMusical]:
        """Processar texto e retornar lista de eventos musicais."""
        eventos = self._inicializar_eventos(estado_processamento)

        i = 0
        while i < len(texto):
            # Checagem especial 'BPM+'
            if i + 3 < len(texto) and texto[i : i + 4].upper() == 'BPM+':
                self._tratar_bpm_mais(estado_processamento, eventos)
                i += 4
                continue

            char = texto[i]
            self._processar_caractere(char, estado_processamento, eventos)

            # Avançar o tempo da música (em batidas)
            estado_processamento.tempo_evento += 1.0
            i += 1

        return eventos

    def _inicializar_eventos(
        self,
        estado: EstadoMusical,
    ) -> list[EventoMusical]:
        """Inicializar a lista de eventos e configurar o estado."""
        estado.redefinir_para_playback()
        return [
            EventoTempo(tempo=estado.tempo_evento, bpm=estado.bpm),
            EventoInstrumento(
                tempo=estado.tempo_evento,
                instrumento_id=estado.instrumento_id,
            ),
        ]

    def _processar_caractere(
        self,
        char: str,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        """Processar um único caractere e atualizar estado/eventos."""
        char_lower = char.lower()

        if char_lower in 'abcdefgh':
            self._tratar_nota(char, estado, eventos)
        elif char == ' ':
            self._tratar_volume(estado)
        elif char in '+-':
            self._tratar_oitava(char, estado)
        elif char_lower in 'oiu':
            self._tratar_vogal(estado, eventos)
        elif char == '?':
            self._tratar_aleatorio(estado, eventos)
        elif char == '\n':
            self._tratar_troca_instrumento(estado, eventos)
        elif char == ';':
            self._tratar_pausa(estado, eventos)

    def _tratar_bpm_mais(
        self,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        estado.bpm += 80
        eventos.append(EventoTempo(tempo=estado.tempo_evento, bpm=estado.bpm))

    def _tratar_nota(
        self,
        char: str,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        nota_midi = self._get_nota_midi(char, estado.oitava)
        if 0 <= nota_midi <= MAX_MIDI_VALUE:
            eventos.append(
                EventoNota(
                    tempo=estado.tempo_evento,
                    pitch=nota_midi,
                    volume=estado.volume,
                    duracao=1.0,
                ),
            )
            estado.ultima_nota_midi = nota_midi
        else:
            self._tratar_pausa(estado, eventos)

    def _tratar_volume(self, estado: EstadoMusical) -> None:
        estado.volume = min(estado.volume * 2, MAX_MIDI_VALUE)
        estado.ultima_nota_midi = -1

    def _tratar_oitava(self, char: str, estado: EstadoMusical) -> None:
        if char == '+':
            estado.oitava = min(estado.oitava + 1, 10)
        else:
            estado.oitava = max(estado.oitava - 1, 1)
        estado.ultima_nota_midi = -1

    def _tratar_vogal(
        self,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        if estado.ultima_nota_midi != -1:
            eventos.append(
                EventoNota(
                    tempo=estado.tempo_evento,
                    pitch=estado.ultima_nota_midi,
                    volume=estado.volume,
                    duracao=1.0,
                ),
            )
        else:
            # Tocar telefone (GM #125)
            nota_telefone = self._get_nota_midi('c', 5)
            eventos.append(
                EventoNotaEspecifica(
                    tempo=estado.tempo_evento,
                    instrumento_id=125,
                    pitch=nota_telefone,
                    volume=100,
                    duracao=1.0,
                ),
            )
            estado.ultima_nota_midi = -1

    def _tratar_aleatorio(
        self,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        nota_rand_char = random.choice('abcdefgh')
        self._tratar_nota(nota_rand_char, estado, eventos)

    def _tratar_troca_instrumento(
        self,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        ids_instrumentos = [id_inst for id_inst, _ in INSTRUMENTOS]
        try:
            idx_atual = ids_instrumentos.index(estado.instrumento_id)
            idx_novo = (idx_atual + 1) % len(ids_instrumentos)
        except ValueError:
            idx_novo = 0

        estado.instrumento_id = ids_instrumentos[idx_novo]
        eventos.append(
            EventoInstrumento(
                tempo=estado.tempo_evento,
                instrumento_id=estado.instrumento_id,
            ),
        )
        estado.ultima_nota_midi = -1

    def _tratar_pausa(
        self,
        estado: EstadoMusical,
        eventos: list[EventoMusical],
    ) -> None:
        eventos.append(EventoPausa(tempo=estado.tempo_evento, duracao=1.0))
        estado.ultima_nota_midi = -1
