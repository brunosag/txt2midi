import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import override

import fluidsynth
from gi.repository import GLib  # pyright: ignore[reportMissingModuleSource]

from domain.events import (
    InstrumentEvent,
    MusicalEvent,
    NoteEvent,
    SpecificNoteEvent,
    TempoEvent,
)
from domain.models import PlaybackSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FluidSynthPlayer(threading.Thread):
    """Executa a música em tempo real usando fluidsynth em uma thread separada."""

    def __init__(
        self,
        soundfont_path: Path,
        events: list[MusicalEvent],
        settings: PlaybackSettings,
        on_finished_callback: Callable[[], None] | None = None,
        on_progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__()
        self.fs: fluidsynth.Synth = fluidsynth.Synth()
        self.soundfont_path: Path = soundfont_path
        self.events: list[MusicalEvent] = events
        self.settings: PlaybackSettings = settings
        self._stop_request: threading.Event = threading.Event()
        self.stop_callback: Callable[[], None] | None = on_finished_callback
        self.progress_callback: Callable[[int, int], None] | None = on_progress_callback
        self.timers: list[threading.Timer] = []

    @override
    def run(self) -> None:
        self._initialize_fluidsynth()

        channel = 0
        current_bpm = float(self.settings.bpm)
        if current_bpm <= 0:
            current_bpm = 120.0

        current_instrument_id = self._configure_initial_instrument(channel)
        previous_event_time = 0.0

        for event in self.events:
            if self._stop_request.is_set():
                break

            event_time = event.time
            self._wait_time(event_time, previous_event_time, current_bpm)

            if self.progress_callback:
                GLib.idle_add(
                    self.progress_callback, event.source_index, event.source_length
                )

            if self._stop_request.is_set():
                break

            current_bpm, current_instrument_id = self._process_event(
                event,
                channel,
                current_bpm,
                current_instrument_id,
            )

            previous_event_time = event_time

        if self._stop_request.is_set():
            for timer in self.timers:
                timer.cancel()
        else:
            for timer in self.timers:
                timer.join()

        self.fs.delete()
        _ = GLib.idle_add(self.notify_stop_main_thread)

    def _initialize_fluidsynth(self) -> None:
        self.fs.start()
        self.fs.sfload(str(self.soundfont_path))

    def _configure_initial_instrument(self, channel: int) -> int:
        instrument_id = -1
        for event in self.events:
            if isinstance(event, InstrumentEvent):
                instrument_id = event.instrument_id
                break

        if instrument_id == -1:
            instrument_id = self.settings.instrument_id

        self.fs.program_change(chan=channel, prg=instrument_id)
        return instrument_id

    def _wait_time(
        self,
        current_time: float,
        previous_time: float,
        bpm: float,
    ) -> None:
        beat_delta = current_time - previous_time
        safe_bpm = max(1.0, bpm)
        if beat_delta > 0:
            wait_seconds = (60.0 / safe_bpm) * beat_delta
            time.sleep(wait_seconds)

    def _process_event(
        self,
        event: MusicalEvent,
        channel: int,
        current_bpm: float,
        current_instrument_id: int,
    ) -> tuple[float, int]:
        if isinstance(event, TempoEvent):
            new_bpm = float(event.bpm)
            return (new_bpm if new_bpm > 0 else 120.0), current_instrument_id

        if isinstance(event, InstrumentEvent):
            self.fs.program_change(chan=channel, prg=event.instrument_id)
            return current_bpm, event.instrument_id

        if isinstance(event, NoteEvent):
            self._play_note(channel=channel, event=event, current_bpm=current_bpm)

        elif isinstance(event, SpecificNoteEvent):
            self._play_specific_note(
                channel=channel,
                event=event,
                current_bpm=current_bpm,
                original_instrument=current_instrument_id,
            )

        return current_bpm, current_instrument_id

    def _play_note(
        self,
        channel: int,
        event: NoteEvent,
        current_bpm: float,
    ) -> None:
        safe_bpm = max(1.0, current_bpm)
        duration_sec = (60.0 / safe_bpm) * event.duration

        self.fs.noteon(chan=channel, key=event.pitch, vel=event.volume)

        self.timers = [t for t in self.timers if t.is_alive()]

        timer = threading.Timer(
            duration_sec,
            self.fs.noteoff,
            args=[channel, event.pitch],
        )
        self.timers.append(timer)
        timer.start()

    def _play_specific_note(
        self,
        channel: int,
        event: SpecificNoteEvent,
        current_bpm: float,
        original_instrument: int,
    ) -> None:
        safe_bpm = max(1.0, current_bpm)
        duration_sec = (60.0 / safe_bpm) * event.duration

        self.fs.program_change(channel, event.instrument_id)
        self.fs.noteon(channel, event.pitch, event.volume)
        self.fs.program_change(channel, original_instrument)

        self.timers = [t for t in self.timers if t.is_alive()]

        timer = threading.Timer(
            duration_sec,
            self.fs.noteoff,
            args=[channel, event.pitch],
        )
        self.timers.append(timer)
        timer.start()

    def stop(self) -> None:
        """Sinalizar a thread para parar."""
        self._stop_request.set()

    def notify_stop_main_thread(self) -> None:
        """Notificar a thread principal que a música terminou."""
        if self.stop_callback:
            self.stop_callback()
