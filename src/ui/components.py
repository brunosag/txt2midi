from pathlib import Path

import gi

from config import DEFAULT_SOUNDFONT, INSTRUMENTS
from domain.models import PlaybackSettings

gi.require_version(namespace='Gtk', version='4.0')
gi.require_version(namespace='Adw', version='1')
gi.require_version(namespace='GtkSource', version='5')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gdk,  # pyright: ignore[reportMissingModuleSource]
    Gio,  # pyright: ignore[reportMissingModuleSource]
    GObject,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
    GtkSource,  # pyright: ignore[reportMissingModuleSource]
)

GObject.type_ensure(GtkSource.View)


@Gtk.Template(filename='src/ui/blueprints/config_panel.ui')
class ConfigPanel(Adw.PreferencesGroup):
    __gtype_name__ = 'ConfigPanel'

    spin_bpm = Gtk.Template.Child()
    spin_volume = Gtk.Template.Child()
    spin_octave = Gtk.Template.Child()
    row_instrument = Gtk.Template.Child()
    box_instrument_wrapper = Gtk.Template.Child()
    lbl_instrument_selected = Gtk.Template.Child()
    popover_instrument = Gtk.Template.Child()
    entry_search = Gtk.Template.Child()
    stack_instrument = Gtk.Template.Child()
    list_instrument = Gtk.Template.Child()
    soundfont_row = Gtk.Template.Child()
    btn_soundfont = Gtk.Template.Child()

    def __init__(self) -> None:
        super().__init__()

        self.current_instrument_id: int = 0
        self.current_soundfont_path: Path = DEFAULT_SOUNDFONT

        self.soundfont_row.set_subtitle(subtitle=str(DEFAULT_SOUNDFONT))
        self._setup_instrument_list()
        self._select_instrument_by_name(name=INSTRUMENTS[0][1])

        self.row_instrument.connect('activated', self._on_open_instrument_popover)
        self.btn_soundfont.connect('clicked', self._on_select_soundfont)
        self.entry_search.connect('search-changed', self._on_instrument_search_changed)

    def _setup_instrument_list(self) -> None:
        items: list[str] = [nome for _id, nome in INSTRUMENTS]
        self.model_strings: Gtk.StringList = Gtk.StringList.new(strings=items)

        self.filter_instrument: Gtk.StringFilter = Gtk.StringFilter()
        expression: Gtk.PropertyExpression = Gtk.PropertyExpression.new(
            this_type=Gtk.StringObject, expression=None, property_name='string'
        )
        self.filter_instrument.set_expression(expression)
        self.filter_instrument.set_ignore_case(ignore_case=True)
        self.filter_instrument.set_match_mode(mode=Gtk.StringFilterMatchMode.SUBSTRING)

        self.model_filter: Gtk.FilterListModel = Gtk.FilterListModel(
            model=self.model_strings, filter=self.filter_instrument
        )
        _ = self.model_filter.connect(
            'items-changed', self._on_instrument_filter_changed
        )

        self.model_selection: Gtk.SingleSelection = Gtk.SingleSelection(
            model=self.model_filter
        )
        self.model_selection.set_autoselect(autoselect=False)

        factory: Gtk.SignalListItemFactory = Gtk.SignalListItemFactory()
        _ = factory.connect('setup', self._on_instrument_list_setup)
        _ = factory.connect('bind', self._on_instrument_list_bind)

        self.list_instrument.set_model(model=self.model_selection)
        self.list_instrument.set_factory(factory=factory)
        self.list_instrument.connect('activate', self._on_instrument_list_activate)

    def _on_instrument_filter_changed(
        self, model: Gtk.FilterListModel, _pos: int, _rm: int, _add: int
    ) -> None:
        if model.get_n_items() == 0:
            self.stack_instrument.set_visible_child_name(name='empty')
        else:
            self.stack_instrument.set_visible_child_name(name='list')

    def _on_open_instrument_popover(self, _row: Adw.ActionRow) -> None:
        self.entry_search.set_text(text='')
        self.popover_instrument.popup()
        _ = self.entry_search.grab_focus()

    def _on_instrument_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.filter_instrument.set_search(search=entry.get_text())

    def _on_instrument_list_setup(
        self, _factory: Gtk.SignalListItemFactory, item: Gtk.ListItem
    ) -> None:
        label: Gtk.Label = Gtk.Label()
        label.set_halign(align=Gtk.Align.START)
        item.set_child(child=label)

    def _on_instrument_list_bind(
        self, _factory: Gtk.SignalListItemFactory, item: Gtk.ListItem
    ) -> None:
        label: Gtk.Widget | None = item.get_child()
        if isinstance(label, Gtk.Label):
            obj: GObject.Object | None = item.get_item()
            if isinstance(obj, Gtk.StringObject):
                label.set_label(str=obj.get_string())

    def _on_instrument_list_activate(
        self, _listview: Gtk.ListView, position: int
    ) -> None:
        obj: GObject.Object | None = self.model_filter.get_item(position)
        if isinstance(obj, Gtk.StringObject):
            name: str = obj.get_string()
            self._select_instrument_by_name(name)
            self.popover_instrument.popdown()

    def _select_instrument_by_name(self, name: str) -> None:
        self.lbl_instrument_selected.set_label(str=name)
        for inst_id, inst_name in INSTRUMENTS:
            if inst_name == name:
                self.current_instrument_id = inst_id
                break

    def _on_select_soundfont(self, btn: Gtk.Button) -> None:
        root: Gtk.Root | None = btn.get_root()
        window: Gtk.Window | None = root if isinstance(root, Gtk.Window) else None

        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Selecionar SoundFont',
            transient_for=window,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        _ = dialog.add_button(button_text='_Abrir', response_id=Gtk.ResponseType.OK)

        filter_sf2: Gtk.FileFilter = Gtk.FileFilter()
        filter_sf2.set_name(name='SoundFont files (*.sf2)')
        filter_sf2.add_pattern(pattern='*.sf2')
        dialog.add_filter(filter=filter_sf2)

        _ = dialog.connect('response', self._on_soundfont_response)
        dialog.show()

    def _on_soundfont_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if response == Gtk.ResponseType.OK:
            file: Gio.File | None = dialog.get_file()
            if file and (path := file.get_path()):
                self.current_soundfont_path = Path(path)
                self.soundfont_row.set_subtitle(
                    subtitle=str(self.current_soundfont_path)
                )
        dialog.destroy()

    def get_playback_settings(self) -> PlaybackSettings:
        return PlaybackSettings(
            bpm=int(self.spin_bpm.get_value()),
            volume=int(self.spin_volume.get_value()),
            octave=int(self.spin_octave.get_value()),
            instrument_id=self.current_instrument_id,
        )

    def set_volume(self, volume: int) -> None:
        adj: Gtk.Adjustment = self.spin_volume.get_adjustment()
        safe_vol: float = max(adj.get_lower(), min(volume, adj.get_upper()))
        self.spin_volume.set_value(value=safe_vol)

    def set_bpm(self, bpm: int) -> None:
        adj: Gtk.Adjustment = self.spin_bpm.get_adjustment()
        safe_bpm: float = max(adj.get_lower(), min(bpm, adj.get_upper()))
        self.spin_bpm.set_value(value=safe_bpm)

    def set_instrument(self, instrument_id: int) -> None:
        instrument_name: str | None = next(
            (nome for _id, nome in INSTRUMENTS if _id == instrument_id), None
        )
        if instrument_name:
            self._select_instrument_by_name(name=instrument_name)

    def get_soundfont_path(self) -> Path:
        return self.current_soundfont_path


@Gtk.Template(filename='src/ui/blueprints/text_editor.ui')
class TextEditor(Adw.PreferencesGroup):
    __gtype_name__ = 'TextEditor'

    textview = Gtk.Template.Child()

    def __init__(self) -> None:
        super().__init__()

        self.buffer: GtkSource.Buffer = self.textview.get_buffer()

        self.highlight_tag: Gtk.TextTag = self.buffer.create_tag(
            tag_name='highlight',
        )
        self.highlight_tag.set_property(
            'background-rgba', Gdk.RGBA(0.2, 0.52, 0.9, 0.4)
        )
        self.highlight_tag.set_property('foreground', None)

        self.style_manager: Adw.StyleManager = Adw.StyleManager.get_default()
        _ = self.style_manager.connect('notify::dark', self._on_theme_changed)
        self._update_theme()

    def set_language_id(self, lang_id: str) -> None:
        lm: GtkSource.LanguageManager = GtkSource.LanguageManager.get_default()
        search_path: list[str] = lm.get_search_path()
        lang_dir: str = str(Path(__file__).parent / 'lang')

        if lang_dir not in search_path:
            search_path.append(lang_dir)
            lm.set_search_path(dirs=search_path)

        lang: GtkSource.Language | None = lm.get_language(id=lang_id)
        if lang:
            self.buffer.set_language(language=lang)

    def _on_theme_changed(
        self, _manager: Adw.StyleManager, _pspec: GObject.ParamSpec
    ) -> None:
        self._update_theme()

    def _update_theme(self) -> None:
        sm: GtkSource.StyleSchemeManager = GtkSource.StyleSchemeManager.get_default()
        is_dark: bool = self.style_manager.get_dark()

        scheme_id = 'Adwaita-dark' if is_dark else 'Adwaita'
        scheme = sm.get_scheme(scheme_id)

        if not scheme:
            scheme_id = 'oblivion' if is_dark else 'classic'
            scheme = sm.get_scheme(scheme_id)

        if scheme:
            self.buffer.set_style_scheme(scheme)

    def get_text(self) -> str:
        start_iter: Gtk.TextIter = self.buffer.get_start_iter()
        end_iter: Gtk.TextIter = self.buffer.get_end_iter()
        return self.buffer.get_text(
            start=start_iter, end=end_iter, include_hidden_chars=False
        )

    def set_text(self, text: str) -> None:
        self.buffer.set_text(text)

    def highlight_range(self, index: int, length: int) -> None:
        if length <= 0:
            return

        start_iter: Gtk.TextIter = self.buffer.get_iter_at_offset(char_offset=index)
        end_iter: Gtk.TextIter = self.buffer.get_iter_at_offset(
            char_offset=index + length
        )

        self.buffer.remove_tag(
            tag=self.highlight_tag,
            start=self.buffer.get_start_iter(),
            end=self.buffer.get_end_iter(),
        )
        self.buffer.apply_tag(tag=self.highlight_tag, start=start_iter, end=end_iter)

        _ = self.textview.scroll_to_iter(
            iter=start_iter, within_margin=0.0, use_align=False, xalign=0.0, yalign=0.0
        )

    def set_editable(self, editable: bool) -> None:
        self.textview.set_editable(setting=editable)


@Gtk.Template(filename='src/ui/blueprints/editor_page.ui')
class EditorPage(Adw.PreferencesPage):
    __gtype_name__ = 'EditorPage'

    config_panel = Gtk.Template.Child()
    text_editor = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def get_text(self) -> str:
        return self.text_editor.get_text()

    def get_settings(self) -> PlaybackSettings:
        return self.config_panel.get_playback_settings()

    def get_soundfont_path(self) -> Path:
        return self.config_panel.get_soundfont_path()
