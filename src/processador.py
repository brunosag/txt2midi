import random

from constantes import INSTRUMENTOS, NOTAS_MIDI_BASE


class MapeadorRegras:
    """Implementa o mapeamento de texto para eventos musicais."""

    def _get_nota_midi(self, nota_char, oitava):
        """Calcular valor MIDI de uma nota (A-H) na oitava especificada."""
        base_nota = NOTAS_MIDI_BASE.get(nota_char.lower(), -1)
        if base_nota == -1:
            return -1

        # Ajustar oitava (base é 5)
        mod_oitava = (oitava - 5) * 12
        return base_nota + mod_oitava

    def processar_texto(self, texto, estado_processamento):
        """Processar texto e retornar lista de eventos musicais."""

        estado_processamento.redefinir_para_playback()
        eventos = []

        # Eventos iniciais para configurar o MIDI/Player
        eventos.append(
            ('tempo', estado_processamento.tempo_evento, estado_processamento.bpm)
        )
        eventos.append(
            (
                'instrumento',
                estado_processamento.tempo_evento,
                estado_processamento.instrumento_id,
            )
        )

        # Processar caractere a caractere
        i = 0
        while i < len(texto):
            char = texto[i]
            duracao_batidas = 1.0  # Duração padrão de 1 batida por evento

            # Checagem especial 'BPM+'
            if i + 3 < len(texto) and texto[i : i + 4].upper() == 'BPM+':
                estado_processamento.bpm += 80
                eventos.append(
                    (
                        'tempo',
                        estado_processamento.tempo_evento,
                        estado_processamento.bpm,
                    )
                )
                i += 4
                continue

            # Mapeamento de notas
            if char.lower() in 'abcdefgh':
                nota_midi = self._get_nota_midi(char, estado_processamento.oitava)
                if 0 <= nota_midi <= 127:
                    eventos.append(
                        (
                            'nota',
                            estado_processamento.tempo_evento,
                            nota_midi,
                            estado_processamento.volume,
                            duracao_batidas,
                        )
                    )
                    estado_processamento.ultima_nota_midi = nota_midi
                else:
                    # Oitava fora do limite, tratar como NOP ou pausa?
                    eventos.append(
                        ('pausa', estado_processamento.tempo_evento, duracao_batidas)
                    )
                    estado_processamento.ultima_nota_midi = -1

            # Espaço (volume)
            elif char == ' ':
                estado_processamento.volume = min(estado_processamento.volume * 2, 127)
                # O volume é aplicado na *próxima* nota, não é um evento MIDI em si
                estado_processamento.ultima_nota_midi = -1

            # Oitava +
            elif char == '+':
                estado_processamento.oitava = min(estado_processamento.oitava + 1, 10)
                estado_processamento.ultima_nota_midi = -1

            # Oitava -
            elif char == '-':
                estado_processamento.oitava = max(estado_processamento.oitava - 1, 1)
                estado_processamento.ultima_nota_midi = -1

            # Vogais (O, I, U)
            elif char.lower() in 'oiu':
                if estado_processamento.ultima_nota_midi != -1:
                    # Repete última nota
                    eventos.append(
                        (
                            'nota',
                            estado_processamento.tempo_evento,
                            estado_processamento.ultima_nota_midi,
                            estado_processamento.volume,
                            duracao_batidas,
                        )
                    )
                else:
                    # Tocar telefone (GM #125)
                    # Toca na oitava 5, independente da oitava atual
                    nota_telefone = self._get_nota_midi('c', 5)
                    eventos.append(
                        (
                            'nota_instrumento_especifico',
                            estado_processamento.tempo_evento,
                            125,
                            nota_telefone,
                            100,
                            duracao_batidas,
                        )
                    )
                    estado_processamento.ultima_nota_midi = (
                        -1
                    )  # Telefone não conta como "última nota"

            # '?' (nota aleatória)
            elif char == '?':
                nota_rand_char = random.choice('abcdefgh')
                nota_midi = self._get_nota_midi(
                    nota_rand_char, estado_processamento.oitava
                )
                if 0 <= nota_midi <= 127:
                    eventos.append(
                        (
                            'nota',
                            estado_processamento.tempo_evento,
                            nota_midi,
                            estado_processamento.volume,
                            duracao_batidas,
                        )
                    )
                    estado_processamento.ultima_nota_midi = nota_midi
                else:
                    eventos.append(
                        ('pausa', estado_processamento.tempo_evento, duracao_batidas)
                    )
                    estado_processamento.ultima_nota_midi = -1

            # Nova linha (mudar instrumento)
            elif char == '\n':
                # Lógica de troca: ciclar pela lista de instrumentos
                ids_instrumentos = [id for id, _nome in INSTRUMENTOS]
                try:
                    idx_atual = ids_instrumentos.index(
                        estado_processamento.instrumento_id
                    )
                    idx_novo = (idx_atual + 1) % len(ids_instrumentos)
                except ValueError:
                    idx_novo = (
                        0  # Voltar para o primeiro se o atual não estiver na lista
                    )

                estado_processamento.instrumento_id = ids_instrumentos[idx_novo]
                eventos.append(
                    (
                        'instrumento',
                        estado_processamento.tempo_evento,
                        estado_processamento.instrumento_id,
                    )
                )
                estado_processamento.ultima_nota_midi = -1

            # Pausa
            elif char == ';':
                eventos.append(
                    ('pausa', estado_processamento.tempo_evento, duracao_batidas)
                )
                estado_processamento.ultima_nota_midi = -1

            # ELSE (NOP)
            else:
                # Não faz nada (não avança o tempo)
                i += 1
                continue

            # Avançar o tempo da música (em batidas)
            estado_processamento.tempo_evento += duracao_batidas
            i += 1

        return eventos
