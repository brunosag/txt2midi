from collections.abc import Callable
from pathlib import Path

from domain.models import PlaybackSettings
from domain.parser import TextParser
from infrastructure.audio_player import FluidSynthPlayer
from infrastructure.midi_exporter import MIDIExporter


class MusicController:
    def __init__(self) -> None:
        self.parser: TextParser = TextParser()
        self.exporter: MIDIExporter = MIDIExporter()
        self.current_player: FluidSynthPlayer | None = None

    def play_music(
        self,
        text: str,
        settings: PlaybackSettings,
        soundfont_path: Path,
        on_finished_callback: Callable[[], None] | None = None,
    ) -> None:
        """Parse text and start playback."""
        self.stop_music()  # Stop any existing playback

        eventos = self.parser.parse(text, settings)
        self.current_player = FluidSynthPlayer(
            soundfont_path=soundfont_path,
            eventos=eventos,
            settings=settings,
            on_finished_callback=on_finished_callback,
        )
        self.current_player.start()

    def stop_music(self) -> None:
        """Stop current playback if active."""
        if self.current_player and self.current_player.is_alive():
            self.current_player.stop()
            self.current_player.join(timeout=1.0)
        self.current_player = None

    def export_midi(
        self,
        text: str,
        settings: PlaybackSettings,
        filepath: Path,
    ) -> None:
        """Parse text and export to MIDI file."""
        eventos = self.parser.parse(text, settings)
        self.exporter.save(eventos, filepath)
