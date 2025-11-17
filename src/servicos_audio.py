import threading
import time

import fluidsynth
from gi.repository import GLib  # type: ignore
from midiutil import MIDIFile


class GeradorMIDI:
    """Gera e salva um arquivo MIDI a partir da lista de eventos."""

    def gerar_e_salvar(self, eventos, _estado_inicial, caminho_arquivo):
        """Criar o objeto `MIDIFile` e o salva no disco."""

        # 1 track, 1 channel, 120BPM (BPM inicial)
        midi = MIDIFile(1, deinterleave=False)

        track = 0
        channel = 0
        tempo_inicial_definido = False
        instrumento_inicial_definido = False

        for evento in eventos:
            tipo = evento[0]
            tempo = evento[1]  # Tempo em batidas

            if tipo == 'tempo' and not tempo_inicial_definido:
                midi.addTempo(track, tempo, evento[2])  # evento[2] é o BPM
                tempo_inicial_definido = True

            elif tipo == 'instrumento' and not instrumento_inicial_definido:
                midi.addProgramChange(
                    track, channel, tempo, evento[2]
                )  # evento[2] é o ID do instrumento
                instrumento_inicial_definido = True

            elif tipo == 'nota':
                pitch = evento[2]
                volume = evento[3]
                duracao = evento[4]
                midi.addNote(track, channel, pitch, tempo, duracao, volume)

            elif tipo == 'nota_instrumento_especifico':
                pitch = evento[3]
                volume = evento[4]
                duracao = evento[5]
                midi.addNote(track, channel, pitch, tempo, duracao, volume)

            # Mudanças de tempo/instrumento no meio da música
            if tipo == 'tempo' and tempo_inicial_definido:
                midi.addTempo(track, tempo, evento[2])

            if tipo == 'instrumento' and instrumento_inicial_definido:
                midi.addProgramChange(track, channel, tempo, evento[2])

        # Salvar o arquivo
        try:
            with open(caminho_arquivo, 'wb') as output_file:
                midi.writeFile(output_file)
            return True
        except Exception as e:
            print(f'Erro ao salvar MIDI: {e}')
            return False


class PlayerAudio(threading.Thread):
    """
    Executa a música em tempo real usando fluidsynth em uma thread separada.
    (RNF-04, RNF-05)
    """

    def __init__(self, soundfont_path, eventos, estado_inicial):
        super().__init__()
        self.fs = None
        self.soundfont_path = soundfont_path
        self.eventos = eventos
        self.estado = estado_inicial
        self._parar_requisicao = threading.Event()
        self.callback_parada = None

    def run(self):
        """Método principal da thread"""
        try:
            self.fs = fluidsynth.Synth()
            self.fs.start()  # Driver de áudio padrão
            _sfid = self.fs.sfload(self.soundfont_path)
        except Exception as e:
            print(f'Erro ao inicializar o FluidSynth: {e}')
            print(f'Verifique se o SoundFont está em: {self.soundfont_path}')
            if self.fs:
                self.fs.delete()
            GLib.idle_add(self.notificar_parada_main_thread)
            return

        # Configurações iniciais
        channel = 0
        bpm_atual = self.estado.bpm

        # Configuração inicial de instrumento
        instrumento_id_atual = -1
        for evento in self.eventos:
            if evento[0] == 'instrumento':
                instrumento_id_atual = evento[2]
                self.fs.program_change(channel, instrumento_id_atual)
                break
        if instrumento_id_atual == -1:  # Se não houver, usa o padrão
            instrumento_id_atual = self.estado.instrumento_id
            self.fs.program_change(channel, instrumento_id_atual)

        tempo_evento_anterior = 0.0

        for evento in self.eventos:
            if self._parar_requisicao.is_set():
                break  # Interrompe a reprodução

            tipo = evento[0]
            tempo = evento[1]  # Tempo em batidas

            # Calcula o tempo de espera desde o último evento
            delta_batidas = tempo - tempo_evento_anterior
            if delta_batidas > 0:
                segundos_espera = (60.0 / bpm_atual) * delta_batidas
                time.sleep(segundos_espera)

            if self._parar_requisicao.is_set():
                break

            # Processa o evento atual
            if tipo == 'tempo':
                bpm_atual = evento[2]

            elif tipo == 'instrumento':
                instrumento_id_atual = evento[2]
                self.fs.program_change(channel, instrumento_id_atual)

            elif tipo == 'nota':
                # evento: ('nota', tempo, pitch, volume, duracao_batidas)
                pitch = evento[2]
                volume = evento[3]
                duracao_seg = (60.0 / bpm_atual) * evento[4]

                self.fs.noteon(channel, pitch, volume)
                time.sleep(duracao_seg * 0.9)  # Toca por 90% da duração
                self.fs.noteoff(channel, pitch)
                time.sleep(duracao_seg * 0.1)  # Pequena pausa

            elif tipo == 'nota_instrumento_especifico':
                # evento: ('nota_instrumento_especifico', tempo, instrumento_id, pitch, volume, duracao)
                # Toca com o instrumento específico e depois restaura o anterior
                id_especifico = evento[2]
                pitch = evento[3]
                volume = evento[4]
                duracao_seg = (60.0 / bpm_atual) * evento[5]

                self.fs.program_change(channel, id_especifico)
                self.fs.noteon(channel, pitch, volume)
                time.sleep(duracao_seg * 0.9)
                self.fs.noteoff(channel, pitch)
                time.sleep(duracao_seg * 0.1)
                self.fs.program_change(channel, instrumento_id_atual)  # Restaura

            # 'pausa' é tratada pelo delta_batidas > 0 no início do loop

            tempo_evento_anterior = tempo

        # Limpeza
        self.fs.delete()

        # Notifica a thread principal (GTK) que a música terminou
        GLib.idle_add(self.notificar_parada_main_thread)

    def parar(self):
        """Sinaliza para a thread parar"""
        self._parar_requisicao.set()

    def notificar_parada_main_thread(self):
        """Função de callback (executada na thread principal)"""
        if self.callback_parada:
            self.callback_parada()
