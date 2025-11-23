import gi

from config import INSTRUMENTOS
from domain.models import PlaybackSettings

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
)


class ConfigPanel(Adw.PreferencesGroup):
    """Painel de configuração (BPM, Volume, Oitava, Instrumento)."""

    def __init__(self) -> None:
        super().__init__()
        self.set_title('Parâmetros iniciais')

        # BPM
        adj_bpm = Gtk.Adjustment(
            value=120,
            lower=20,
            upper=400,
            step_increment=5,
            page_increment=0,
            page_size=0,
        )
        self.spin_bpm: Adw.SpinRow = Adw.SpinRow()
        self.spin_bpm.set_title('BPM (batidas por minuto)')
        self.spin_bpm.set_adjustment(adj_bpm)
        self.spin_bpm.set_digits(0)
        self.add(self.spin_bpm)

        # Volume
        adj_vol = Gtk.Adjustment(
            value=100,
            lower=0,
            upper=127,
            step_increment=1,
            page_increment=0,
            page_size=0,
        )
        self.spin_vol: Adw.SpinRow = Adw.SpinRow()
        self.spin_vol.set_title('Volume inicial')
        self.spin_vol.set_adjustment(adj_vol)
        self.spin_vol.set_digits(0)
        self.add(self.spin_vol)

        # Oitava
        adj_oitava = Gtk.Adjustment(
            value=5,
            lower=1,
            upper=10,
            step_increment=1,
            page_increment=0,
            page_size=0,
        )
        self.spin_oitava: Adw.SpinRow = Adw.SpinRow()
        self.spin_oitava.set_title('Oitava inicial')
        self.spin_oitava.set_adjustment(adj_oitava)
        self.spin_oitava.set_digits(0)
        self.add(self.spin_oitava)

        # Instrumento
        self.lista_instrumentos_store: Gtk.StringList = Gtk.StringList.new(
            [nome for _id, nome in INSTRUMENTOS],
        )
        self.combo_row_inst: Adw.ComboRow = Adw.ComboRow()
        self.combo_row_inst.set_title('Instrumento inicial')
        self.combo_row_inst.set_model(self.lista_instrumentos_store)
        self.combo_row_inst.set_selected(0)  # Acoustic Grand Piano
        self.add(self.combo_row_inst)

    def get_playback_settings(self) -> PlaybackSettings:
        """Retornar as configurações atuais da UI."""
        idx_inst = self.combo_row_inst.get_selected()
        instrument_id = INSTRUMENTOS[idx_inst][0]

        return PlaybackSettings(
            bpm=int(self.spin_bpm.get_value()),
            volume=int(self.spin_vol.get_value()),
            octave=int(self.spin_oitava.get_value()),
            instrument_id=instrument_id,
        )


class TextEditor(Adw.PreferencesGroup):
    """Editor de texto para entrada musical."""

    def __init__(self) -> None:
        super().__init__()
        self.set_title('Texto de entrada')
        self.set_description('Insira o texto para geração da música.')

        self.textview: Gtk.TextView = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_monospace(True)
        self.textview.set_vexpand(True)
        self.textview.set_left_margin(6)
        self.textview.set_right_margin(6)
        self.textview.set_top_margin(6)
        self.textview.set_bottom_margin(6)

        self.text_buffer: Gtk.TextBuffer = self.textview.get_buffer()
        self.text_buffer.set_text('CDEFGABH+CDEF\n\n-CDEF\n\n')

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(150)
        scrolled_window.set_child(self.textview)

        text_frame = Gtk.Frame()
        text_frame.set_child(scrolled_window)
        self.add(text_frame)

    def get_text(self) -> str:
        """Retornar o texto atual do editor."""
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(
            start=start_iter, end=end_iter, include_hidden_chars=False
        )

    def set_text(self, text: str) -> None:
        """Definir o texto do editor."""
        self.text_buffer.set_text(text)
