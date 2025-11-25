from pathlib import Path

import gi

from config import DEFAULT_SOUNDFONT, INSTRUMENTOS
from domain.models import PlaybackSettings

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
    GtkSource,  # pyright: ignore[reportMissingModuleSource]
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

        # SoundFont Selector
        self.soundfont_row: Adw.ActionRow = Adw.ActionRow()
        self.soundfont_row.set_title('SoundFont')
        self.soundfont_row.set_subtitle(str(DEFAULT_SOUNDFONT))

        self.btn_soundfont: Gtk.Button = Gtk.Button(label='Selecionar')
        self.btn_soundfont.set_valign(Gtk.Align.CENTER)
        _ = self.btn_soundfont.connect('clicked', self._on_select_soundfont)

        self.soundfont_row.add_suffix(self.btn_soundfont)
        self.add(self.soundfont_row)

        self.current_soundfont_path: Path = DEFAULT_SOUNDFONT

    def _on_select_soundfont(self, btn: Gtk.Button) -> None:
        root = btn.get_root()
        window = root if isinstance(root, Gtk.Window) else None

        dialog = Gtk.FileChooserDialog(
            title='Selecionar SoundFont',
            transient_for=window,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button('_Cancelar', Gtk.ResponseType.CANCEL)
        _ = dialog.add_button('_Abrir', Gtk.ResponseType.OK)

        filter_sf2 = Gtk.FileFilter()
        filter_sf2.set_name('SoundFont files (*.sf2)')
        filter_sf2.add_pattern('*.sf2')
        dialog.add_filter(filter_sf2)

        _ = dialog.connect('response', self._on_soundfont_response)
        dialog.show()

    def _on_soundfont_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if response == Gtk.ResponseType.OK:
            file = dialog.get_file()
            if file and (path := file.get_path()):
                self.current_soundfont_path = Path(path)
                self.soundfont_row.set_subtitle(str(self.current_soundfont_path))
        dialog.destroy()

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

    def get_soundfont_path(self) -> Path:
        return self.current_soundfont_path


class TextEditor(Adw.PreferencesGroup):
    """Editor de texto para entrada musical."""

    def __init__(self) -> None:
        super().__init__()
        self.set_title('Texto de entrada')
        self.set_description('Insira o texto para geração da música.')

        self.buffer: GtkSource.Buffer = GtkSource.Buffer()
        self._setup_language()

        self.textview: GtkSource.View = GtkSource.View.new_with_buffer(self.buffer)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_monospace(True)
        self.textview.set_vexpand(True)
        self.textview.set_left_margin(6)
        self.textview.set_right_margin(6)
        self.textview.set_top_margin(6)
        self.textview.set_bottom_margin(6)
        self.textview.set_show_line_numbers(True)
        self.textview.set_highlight_current_line(True)

        self.text_buffer: Gtk.TextBuffer = self.buffer
        self.text_buffer.set_text('CDEFGABH+CDEF\n\n-CDEF\n\n')

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(150)
        scrolled_window.set_child(self.textview)

        text_frame = Gtk.Frame()
        text_frame.set_child(scrolled_window)
        self.add(text_frame)

        # Tag for highlighting
        self.highlight_tag: Gtk.TextTag = self.buffer.create_tag(
            'highlight', background='yellow', foreground='black'
        )

    def _setup_language(self) -> None:
        lm = GtkSource.LanguageManager.get_default()
        # Add current directory to search path for tcp.lang
        search_path = lm.get_search_path()
        current_dir = str(Path(__file__).parent)
        if current_dir not in search_path:
            search_path.append(current_dir)
            lm.set_search_path(search_path)

        lang = lm.get_language('tcp')
        if lang:
            self.buffer.set_language(lang)

        # Set scheme
        sm = GtkSource.StyleSchemeManager.get_default()
        scheme = sm.get_scheme('classic')  # Or another available scheme
        if scheme:
            self.buffer.set_style_scheme(scheme)

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

    def highlight_char(self, index: int) -> None:
        """Highlight character at specific index."""
        start_iter = self.buffer.get_iter_at_offset(index)
        end_iter = self.buffer.get_iter_at_offset(index + 1)

        self.buffer.remove_tag(
            self.highlight_tag, self.buffer.get_start_iter(), self.buffer.get_end_iter()
        )
        self.buffer.apply_tag(self.highlight_tag, start_iter, end_iter)

        # Scroll to cursor
        _ = self.textview.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.0)  # noqa: FBT003

    def set_editable(self, editable: bool) -> None:  # noqa: FBT001
        """Definir se o texto pode ser editado."""
        self.textview.set_editable(editable)
