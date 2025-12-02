from collections.abc import Callable
from pathlib import Path

from domain.events import MusicalEvent
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
        on_progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Analisa o texto e inicia a reprodução."""
        self.stop_music()

        events: list[MusicalEvent] = self.parser.parse(
            text=text, settings=settings, mode=mode
        )
        self.current_player = FluidSynthPlayer(
            soundfont_path=soundfont_path,
            events=events,
            settings=settings,
            on_finished_callback=on_finished_callback,
            on_progress_callback=on_progress_callback,
        )
        self.current_player.start()

    def stop_music(self) -> None:
        """Para a reprodução atual se estiver ativa."""
        if self.current_player and self.current_player.is_alive():
            self.current_player.stop()
            self.current_player.join(timeout=1.0)
        self.current_player = None

    def export_midi(
        self,
        text: str,
        settings: PlaybackSettings,
        mode: ParsingMode,
        file_path: Path,
    ) -> None:
        """Analisa o texto e exporta para arquivo MIDI."""
        events: list[MusicalEvent] = self.parser.parse(
            text=text, settings=settings, mode=mode
        )
        self.exporter.save(events=events, file_path=file_path)

    def import_midi(self, file_path: Path) -> tuple[str, int, int, int]:
        """Importa um arquivo MIDI e converte para sintaxe de texto + configurações."""
        return self.importer.load(file_path)
