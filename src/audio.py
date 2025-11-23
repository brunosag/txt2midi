import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import override

import fluidsynth
from gi.repository import GLib  # pyright: ignore[reportMissingModuleSource]
from midiutil import MIDIFile

from eventos import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoNotaEspecifica,
    EventoTempo,
)
from modelo import EstadoMusical

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeradorMIDI:
    """Gera e salva um arquivo MIDI a partir da lista de eventos."""

    def gerar_e_salvar(
        self,
        eventos: list[EventoMusical],
        _estado_inicial: EstadoMusical,
        caminho_arquivo: Path,
    ) -> None:
        """Criar o objeto `MIDIFile` e o salva no disco."""
        # 1 track, 1 channel, 120BPM (BPM inicial)
        midi = MIDIFile(1, deinterleave=False)

        track = 0
        channel = 0
        tempo_inicial_definido = False
        instrumento_inicial_definido = False

        for evento in eventos:
            if isinstance(evento, EventoTempo) and not tempo_inicial_definido:
                midi.addTempo(
                    track=track,
                    time=evento.tempo,
                    tempo=evento.bpm,
                )
                tempo_inicial_definido = True

            elif (
                isinstance(evento, EventoInstrumento)
                and not instrumento_inicial_definido
            ):
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=evento.tempo,
                    program=evento.instrumento_id,
                )
                instrumento_inicial_definido = True

            elif isinstance(evento, (EventoNota, EventoNotaEspecifica)):
                midi.addNote(
                    track=track,
                    channel=channel,
                    pitch=evento.pitch,
                    time=evento.tempo,
                    duration=evento.duracao,
                    volume=evento.volume,
                )

            # Mudanças de tempo/instrumento no meio da música
            if isinstance(evento, EventoTempo) and tempo_inicial_definido:
                midi.addTempo(
                    track=track,
                    time=evento.tempo,
                    tempo=evento.bpm,
                )

            if isinstance(evento, EventoInstrumento) and instrumento_inicial_definido:
                midi.addProgramChange(
                    tracknum=track,
                    channel=channel,
                    time=evento.tempo,
                    program=evento.instrumento_id,
                )

        # Salvar o arquivo
        try:
            with caminho_arquivo.open('wb') as output_file:
                midi.writeFile(output_file)
        except Exception:
            logger.exception('Erro ao salvar MIDI')
            raise


class PlayerAudio(threading.Thread):
    """Executa a música em tempo real usando fluidsynth em uma thread separada."""

    def __init__(
        self,
        soundfont_path: Path,
        eventos: list[EventoMusical],
        estado_inicial: EstadoMusical,
    ) -> None:
        super().__init__()
        self.fs: fluidsynth.Synth = fluidsynth.Synth()
        self.soundfont_path: Path = soundfont_path
        self.eventos: list[EventoMusical] = eventos
        self.estado: EstadoMusical = estado_inicial
        self._parar_requisicao: threading.Event = threading.Event()
        self.callback_parada: Callable[[], None] | None = None

    @override
    def run(self) -> None:
        if not self._inicializar_fluidsynth():
            return

        channel = 0
        bpm_atual = self.estado.bpm
        instrumento_id_atual = self._configurar_instrumento_inicial(channel)
        tempo_evento_anterior = 0.0

        for evento in self.eventos:
            if self._parar_requisicao.is_set():
                break

            tempo = evento.tempo
            self._aguardar_tempo(tempo, tempo_evento_anterior, bpm_atual)

            if self._parar_requisicao.is_set():
                break

            bpm_atual, instrumento_id_atual = self._processar_evento(
                evento,
                channel,
                bpm_atual,
                instrumento_id_atual,
            )

            tempo_evento_anterior = tempo

        self.fs.delete()
        _ = GLib.idle_add(self.notificar_parada_main_thread)

    def _inicializar_fluidsynth(self) -> bool:
        try:
            self.fs.start()
            self.fs.sfload(str(self.soundfont_path))
        except Exception:
            logger.exception('Erro ao inicializar o FluidSynth')
            if self.fs:
                self.fs.delete()
            self.notificar_parada_main_thread()
            return False
        else:
            return True

    def _configurar_instrumento_inicial(self, channel: int) -> int:
        instrumento_id = -1
        for evento in self.eventos:
            if isinstance(evento, EventoInstrumento):
                instrumento_id = evento.instrumento_id
                break

        if instrumento_id == -1:
            instrumento_id = self.estado.instrumento_id

        self.fs.program_change(chan=channel, prg=instrumento_id)
        return instrumento_id

    def _aguardar_tempo(
        self,
        tempo_atual: float,
        tempo_anterior: float,
        bpm: float,
    ) -> None:
        delta_batidas = tempo_atual - tempo_anterior
        if delta_batidas > 0:
            segundos_espera = (60.0 / bpm) * delta_batidas
            time.sleep(segundos_espera)

    def _processar_evento(
        self,
        evento: EventoMusical,
        channel: int,
        bpm_atual: float,
        instrumento_id_atual: int,
    ) -> tuple[float, int]:
        if isinstance(evento, EventoTempo):
            return evento.bpm, instrumento_id_atual

        if isinstance(evento, EventoInstrumento):
            self.fs.program_change(chan=channel, prg=evento.instrumento_id)
            return bpm_atual, evento.instrumento_id

        if isinstance(evento, EventoNota):
            self._tocar_nota(channel=channel, evento=evento, bpm_atual=bpm_atual)

        elif isinstance(evento, EventoNotaEspecifica):
            self._tocar_nota_especifica(
                channel=channel,
                evento=evento,
                bpm_atual=bpm_atual,
                instrumento_original=instrumento_id_atual,
            )

        return bpm_atual, instrumento_id_atual

    def _tocar_nota(
        self,
        channel: int,
        evento: EventoNota,
        bpm_atual: float,
    ) -> None:
        duracao_seg = (60.0 / bpm_atual) * evento.duracao
        self.fs.noteon(chan=channel, key=evento.pitch, vel=evento.volume)
        timer = threading.Timer(
            duracao_seg,
            self.fs.noteoff,
            args=[channel, evento.pitch],
        )
        timer.start()

    def _tocar_nota_especifica(
        self,
        channel: int,
        evento: EventoNotaEspecifica,
        bpm_atual: float,
        instrumento_original: int,
    ) -> None:
        duracao_seg = (60.0 / bpm_atual) * evento.duracao

        self.fs.program_change(channel, evento.instrumento_id)
        self.fs.noteon(channel, evento.pitch, evento.volume)
        self.fs.program_change(channel, instrumento_original)

        timer = threading.Timer(
            duracao_seg,
            self.fs.noteoff,
            args=[channel, evento.pitch],
        )
        timer.start()

    def parar(self) -> None:
        """Sinalizar a thread para parar."""
        self._parar_requisicao.set()

    def notificar_parada_main_thread(self) -> None:
        """Notificar a thread principal que a música terminou."""
        if self.callback_parada:
            self.callback_parada()
