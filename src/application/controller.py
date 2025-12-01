from collections.abc import Callable
from pathlib import Path

from domain.events import EventoMusical
from domain.models import PlaybackSettings
from domain.parser import ParsingMode, TextParser
from infrastructure.audio_player import FluidSynthPlayer
from infrastructure.midi_exporter import MIDIExporter
from infrastructure.midi_importer import MIDIImporter


class MusicController:
    def __init__(self) -> None:
        self.parser: TextParser = TextParser()
        self.exporter: MIDIExporter = MIDIExporter()
        self.importer: MIDIImporter = MIDIImporter()
        self.current_player: FluidSynthPlayer | None = None

    def play_music(
        self,
        text: str,
        settings: PlaybackSettings,
        mode: ParsingMode,
        soundfont_path: Path,
        on_finished_callback: Callable[[], None] | None = None,
        on_progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Parse text and start playback."""
        self.stop_music()

        eventos: list[EventoMusical] = self.parser.parse(
            texto=text, settings=settings, mode=mode
        )
        self.current_player = FluidSynthPlayer(
            soundfont_path=soundfont_path,
            eventos=eventos,
            settings=settings,
            on_finished_callback=on_finished_callback,
            on_progress_callback=on_progress_callback,
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
        mode: ParsingMode,
        filepath: Path,
    ) -> None:
        """Parse text and export to MIDI file."""
        eventos: list[EventoMusical] = self.parser.parse(
            texto=text, settings=settings, mode=mode
        )
        self.exporter.save(eventos=eventos, caminho_arquivo=filepath)

    def import_midi(self, filepath: Path) -> tuple[str, int, int, int]:
        """Import a MIDI file and convert it to text syntax + settings."""
        return self.importer.load(filepath)
