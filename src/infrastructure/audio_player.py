import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import override

import fluidsynth
from gi.repository import GLib  # pyright: ignore[reportMissingModuleSource]

from domain.events import (
    EventoInstrumento,
    EventoMusical,
    EventoNota,
    EventoNotaEspecifica,
    EventoTempo,
)
from domain.models import PlaybackSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FluidSynthPlayer(threading.Thread):
    """Executa a música em tempo real usando fluidsynth em uma thread separada."""

    def __init__(
        self,
        soundfont_path: Path,
        eventos: list[EventoMusical],
        settings: PlaybackSettings,
        on_finished_callback: Callable[[], None] | None = None,
        on_progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__()
        self.fs: fluidsynth.Synth = fluidsynth.Synth()
        self.soundfont_path: Path = soundfont_path
        self.eventos: list[EventoMusical] = eventos
        self.settings: PlaybackSettings = settings
        self._parar_requisicao: threading.Event = threading.Event()
        self.callback_parada: Callable[[], None] | None = on_finished_callback
        self.callback_progresso: Callable[[int], None] | None = on_progress_callback
        self.timers: list[threading.Timer] = []

    @override
    def run(self) -> None:
        self._inicializar_fluidsynth()

        channel = 0
        bpm_atual = float(self.settings.bpm)
        instrumento_id_atual = self._configurar_instrumento_inicial(channel)
        tempo_evento_anterior = 0.0

        for evento in self.eventos:
            if self._parar_requisicao.is_set():
                break

            tempo = evento.tempo
            self._aguardar_tempo(tempo, tempo_evento_anterior, bpm_atual)

            if self.callback_progresso:
                GLib.idle_add(self.callback_progresso, evento.source_index)

            if self._parar_requisicao.is_set():
                break

            bpm_atual, instrumento_id_atual = self._processar_evento(
                evento,
                channel,
                bpm_atual,
                instrumento_id_atual,
            )

            tempo_evento_anterior = tempo

        # Aguardar ou cancelar timers pendentes
        if self._parar_requisicao.is_set():
            for timer in self.timers:
                timer.cancel()
        else:
            for timer in self.timers:
                timer.join()

        self.fs.delete()
        _ = GLib.idle_add(self.notificar_parada_main_thread)

    def _inicializar_fluidsynth(self) -> None:
        try:
            self.fs.start()
            self.fs.sfload(str(self.soundfont_path))
        except Exception:
            logger.exception('Erro ao inicializar o FluidSynth')
            if self.fs:
                self.fs.delete()
            self.notificar_parada_main_thread()

    def _configurar_instrumento_inicial(self, channel: int) -> int:
        instrument_id = -1
        for evento in self.eventos:
            if isinstance(evento, EventoInstrumento):
                instrument_id = evento.instrument_id
                break

        if instrument_id == -1:
            instrument_id = self.settings.instrument_id

        self.fs.program_change(chan=channel, prg=instrument_id)
        return instrument_id

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
        instrument_id_atual: int,
    ) -> tuple[float, int]:
        if isinstance(evento, EventoTempo):
            return float(evento.bpm), instrument_id_atual

        if isinstance(evento, EventoInstrumento):
            self.fs.program_change(chan=channel, prg=evento.instrument_id)
            return bpm_atual, evento.instrument_id

        if isinstance(evento, EventoNota):
            self._tocar_nota(channel=channel, evento=evento, bpm_atual=bpm_atual)

        elif isinstance(evento, EventoNotaEspecifica):
            self._tocar_nota_especifica(
                channel=channel,
                evento=evento,
                bpm_atual=bpm_atual,
                instrumento_original=instrument_id_atual,
            )

        return bpm_atual, instrument_id_atual

    def _tocar_nota(
        self,
        channel: int,
        evento: EventoNota,
        bpm_atual: float,
    ) -> None:
        duracao_seg = (60.0 / bpm_atual) * evento.duracao
        self.fs.noteon(chan=channel, key=evento.pitch, vel=evento.volume)

        # Limpar timers finalizados
        self.timers = [t for t in self.timers if t.is_alive()]

        timer = threading.Timer(
            duracao_seg,
            self.fs.noteoff,
            args=[channel, evento.pitch],
        )
        self.timers.append(timer)
        timer.start()

    def _tocar_nota_especifica(
        self,
        channel: int,
        evento: EventoNotaEspecifica,
        bpm_atual: float,
        instrumento_original: int,
    ) -> None:
        duracao_seg = (60.0 / bpm_atual) * evento.duracao

        self.fs.program_change(channel, evento.instrument_id)
        self.fs.noteon(channel, evento.pitch, evento.volume)
        self.fs.program_change(channel, instrumento_original)

        # Limpar timers finalizados
        self.timers = [t for t in self.timers if t.is_alive()]

        timer = threading.Timer(
            duracao_seg,
            self.fs.noteoff,
            args=[channel, evento.pitch],
        )
        self.timers.append(timer)
        timer.start()

    def stop(self) -> None:
        """Sinalizar a thread para parar."""
        self._parar_requisicao.set()

    def notificar_parada_main_thread(self) -> None:
        """Notificar a thread principal que a música terminou."""
        if self.callback_parada:
            self.callback_parada()
