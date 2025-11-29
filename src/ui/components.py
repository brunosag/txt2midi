from pathlib import Path

import gi

from config import DEFAULT_SOUNDFONT, INSTRUMENTOS
from domain.models import PlaybackSettings

gi.require_version(namespace='Gtk', version='4.0')
gi.require_version(namespace='Adw', version='1')
gi.require_version(namespace='GtkSource', version='5')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gio,  # pyright: ignore[reportMissingModuleSource]
    GObject,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
    GtkSource,  # pyright: ignore[reportMissingModuleSource]
)


class ConfigPanel(Adw.PreferencesGroup):
    """Painel de configuração (BPM, Volume, Oitava, Instrumento)."""

    def __init__(self) -> None:
        super().__init__()
        self.set_title(title='Parâmetros iniciais')

        adj_bpm: Gtk.Adjustment = Gtk.Adjustment(
            value=120,
            lower=20,
            upper=400,
            step_increment=5,
            page_increment=0,
            page_size=0,
        )
        self.spin_bpm: Adw.SpinRow = Adw.SpinRow()
        self.spin_bpm.set_title(title='BPM (batidas por minuto)')
        self.spin_bpm.set_adjustment(adjustment=adj_bpm)
        self.spin_bpm.set_digits(digits=0)
        self.add(child=self.spin_bpm)

        adj_vol: Gtk.Adjustment = Gtk.Adjustment(
            value=100,
            lower=0,
            upper=127,
            step_increment=1,
            page_increment=0,
            page_size=0,
        )
        self.spin_vol: Adw.SpinRow = Adw.SpinRow()
        self.spin_vol.set_title(title='Volume inicial')
        self.spin_vol.set_adjustment(adjustment=adj_vol)
        self.spin_vol.set_digits(digits=0)
        self.add(child=self.spin_vol)

        adj_oitava: Gtk.Adjustment = Gtk.Adjustment(
            value=5,
            lower=1,
            upper=10,
            step_increment=1,
            page_increment=0,
            page_size=0,
        )
        self.spin_oitava: Adw.SpinRow = Adw.SpinRow()
        self.spin_oitava.set_title(title='Oitava inicial')
        self.spin_oitava.set_adjustment(adjustment=adj_oitava)
        self.spin_oitava.set_digits(digits=0)
        self.add(child=self.spin_oitava)

        self.row_inst: Adw.ActionRow = Adw.ActionRow()
        self.row_inst.set_title(title='Instrumento inicial')
        self.row_inst.set_activatable(activatable=True)
        _ = self.row_inst.connect('activated', self._on_open_inst_popover)
        self.box_inst_wrapper: Gtk.Box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        self.box_inst_wrapper.set_valign(align=Gtk.Align.CENTER)

        self.lbl_inst_selected: Gtk.Label = Gtk.Label()
        self.box_inst_wrapper.append(child=self.lbl_inst_selected)

        icon_arrow: Gtk.Image = Gtk.Image.new_from_icon_name(
            icon_name='pan-down-symbolic'
        )
        self.box_inst_wrapper.append(child=icon_arrow)

        self.row_inst.add_suffix(widget=self.box_inst_wrapper)
        self.add(child=self.row_inst)

        self._build_instrument_popover()

        self.current_instrument_id: int = 0
        self._select_instrument_by_name(name=INSTRUMENTOS[0][1])

        self.soundfont_row: Adw.ActionRow = Adw.ActionRow()
        self.soundfont_row.set_title(title='SoundFont')
        self.soundfont_row.set_subtitle(subtitle=str(DEFAULT_SOUNDFONT))

        self.btn_soundfont: Gtk.Button = Gtk.Button(label='Selecionar')
        self.btn_soundfont.set_valign(align=Gtk.Align.CENTER)
        _ = self.btn_soundfont.connect('clicked', self._on_select_soundfont)

        self.soundfont_row.add_suffix(widget=self.btn_soundfont)
        self.add(child=self.soundfont_row)

        self.current_soundfont_path: Path = DEFAULT_SOUNDFONT

    def _build_instrument_popover(self) -> None:
        self.popover_inst: Gtk.Popover = Gtk.Popover()
        self.popover_inst.set_parent(parent=self.box_inst_wrapper)
        self.popover_inst.add_css_class(css_class='menu')
        self.popover_inst.set_autohide(autohide=True)

        box: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.popover_inst.set_child(child=box)

        self.entry_search: Gtk.SearchEntry = Gtk.SearchEntry()
        self.entry_search.set_placeholder_text(text='Buscar...')
        self.entry_search.set_search_delay(delay=0)
        self.entry_search.set_margin_top(margin=6)
        self.entry_search.set_margin_bottom(margin=6)
        self.entry_search.set_margin_start(margin=6)
        self.entry_search.set_margin_end(margin=6)
        box.append(child=self.entry_search)

        self.stack_inst: Gtk.Stack = Gtk.Stack()
        self.stack_inst.set_transition_type(transition=Gtk.StackTransitionType.NONE)
        box.append(child=self.stack_inst)

        items: list[str] = [nome for _id, nome in INSTRUMENTOS]
        self.model_strings: Gtk.StringList = Gtk.StringList.new(strings=items)

        self.filter_inst: Gtk.StringFilter = Gtk.StringFilter()
        expression: Gtk.PropertyExpression = Gtk.PropertyExpression.new(
            this_type=Gtk.StringObject, expression=None, property_name='string'
        )
        self.filter_inst.set_expression(expression)
        self.filter_inst.set_ignore_case(ignore_case=True)
        self.filter_inst.set_match_mode(mode=Gtk.StringFilterMatchMode.SUBSTRING)

        self.model_filter: Gtk.FilterListModel = Gtk.FilterListModel(
            model=self.model_strings, filter=self.filter_inst
        )
        _ = self.model_filter.connect('items-changed', self._on_inst_filter_changed)

        self.model_selection: Gtk.SingleSelection = Gtk.SingleSelection(
            model=self.model_filter
        )
        self.model_selection.set_autoselect(autoselect=False)

        factory: Gtk.SignalListItemFactory = Gtk.SignalListItemFactory()
        _ = factory.connect('setup', self._on_inst_list_setup)
        _ = factory.connect('bind', self._on_inst_list_bind)

        self.list_inst: Gtk.ListView = Gtk.ListView(
            model=self.model_selection, factory=factory
        )
        self.list_inst.set_single_click_activate(single_click_activate=True)
        _ = self.list_inst.connect('activate', self._on_inst_list_activate)

        scrolled: Gtk.ScrolledWindow = Gtk.ScrolledWindow()
        scrolled.set_min_content_width(width=200)
        scrolled.set_max_content_height(height=300)
        scrolled.set_propagate_natural_height(propagate=True)
        scrolled.set_propagate_natural_width(propagate=True)
        scrolled.set_child(child=self.list_inst)

        _ = self.stack_inst.add_named(child=scrolled, name='list')

        lbl_empty: Gtk.Label = Gtk.Label(label='Nenhum resultado.')
        lbl_empty.add_css_class(css_class='dim-label')

        _ = self.stack_inst.add_named(child=lbl_empty, name='empty')
        _ = self.entry_search.connect('search-changed', self._on_inst_search_changed)

    def _on_inst_filter_changed(
        self, model: Gtk.FilterListModel, _pos: int, _rm: int, _add: int
    ) -> None:
        """Alterna a stack dependendo se há itens visíveis no filtro."""
        if model.get_n_items() == 0:
            self.stack_inst.set_visible_child_name(name='empty')
        else:
            self.stack_inst.set_visible_child_name(name='list')

    def _on_open_inst_popover(self, _row: Adw.ActionRow) -> None:
        self.entry_search.set_text(text='')
        self.popover_inst.popup()
        _ = self.entry_search.grab_focus()

    def _on_inst_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.filter_inst.set_search(search=entry.get_text())

    def _on_inst_list_setup(
        self, _factory: Gtk.SignalListItemFactory, item: Gtk.ListItem
    ) -> None:
        label: Gtk.Label = Gtk.Label()
        label.set_halign(align=Gtk.Align.START)
        item.set_child(child=label)

    def _on_inst_list_bind(
        self, _factory: Gtk.SignalListItemFactory, item: Gtk.ListItem
    ) -> None:
        label: Gtk.Widget | None = item.get_child()
        if isinstance(label, Gtk.Label):
            obj: GObject.Object | None = item.get_item()
            if isinstance(obj, Gtk.StringObject):
                label.set_label(str=obj.get_string())

    def _on_inst_list_activate(self, _listview: Gtk.ListView, position: int) -> None:
        obj: GObject.Object | None = self.model_filter.get_item(position)
        if isinstance(obj, Gtk.StringObject):
            name: str = obj.get_string()
            self._select_instrument_by_name(name)
            self.popover_inst.popdown()

    def _select_instrument_by_name(self, name: str) -> None:
        self.lbl_inst_selected.set_label(str=name)
        for inst_id, inst_name in INSTRUMENTOS:
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
            volume=int(self.spin_vol.get_value()),
            octave=int(self.spin_oitava.get_value()),
            instrument_id=self.current_instrument_id,
        )

    def get_soundfont_path(self) -> Path:
        return self.current_soundfont_path


class TextEditor(Adw.PreferencesGroup):
    """Editor de texto para entrada musical."""

    def __init__(self) -> None:
        super().__init__()
        self.set_title(title='Texto de entrada')
        self.set_description(description='Insira o texto para geração da música.')

        self.buffer: GtkSource.Buffer = GtkSource.Buffer()
        self._setup_language()

        self.style_manager: Adw.StyleManager = Adw.StyleManager.get_default()
        _ = self.style_manager.connect('notify::dark', self._on_theme_changed)
        self._update_theme()

        self.textview: GtkSource.View = GtkSource.View.new_with_buffer(self.buffer)
        self.textview.set_wrap_mode(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.textview.set_monospace(monospace=True)
        self.textview.set_vexpand(expand=True)
        self.textview.set_left_margin(left_margin=6)
        self.textview.set_right_margin(right_margin=6)
        self.textview.set_top_margin(top_margin=6)
        self.textview.set_bottom_margin(bottom_margin=6)

        self.text_buffer: Gtk.TextBuffer = self.buffer
        self.text_buffer.set_text(text='CDEFGABH+CDEF\n\n-CDEF\n\n')

        scrolled_window: Gtk.ScrolledWindow = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        scrolled_window.set_min_content_height(height=150)
        scrolled_window.set_child(child=self.textview)

        text_frame: Gtk.Frame = Gtk.Frame()
        text_frame.set_child(child=scrolled_window)
        self.add(child=text_frame)

        self.highlight_tag: Gtk.TextTag = self.buffer.create_tag(
            tag_name='highlight', background='yellow', foreground='black'
        )

    def _setup_language(self) -> None:
        lm: GtkSource.LanguageManager = GtkSource.LanguageManager.get_default()
        search_path: list[str] = lm.get_search_path()
        current_dir: str = str(Path(__file__).parent)
        if current_dir not in search_path:
            search_path.append(current_dir)
            lm.set_search_path(dirs=search_path)

        lang: GtkSource.Language | None = lm.get_language(id='tcp')
        if lang:
            self.buffer.set_language(language=lang)

    def _on_theme_changed(
        self, _manager: Adw.StyleManager, _pspec: GObject.ParamSpec
    ) -> None:
        """Chamado quando o tema do sistema muda (claro/escuro)."""
        self._update_theme()

    def _update_theme(self) -> None:
        """Aplica o esquema de cores correto baseado no tema atual."""
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
        """Retornar o texto atual do editor."""
        start_iter: Gtk.TextIter = self.text_buffer.get_start_iter()
        end_iter: Gtk.TextIter = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(
            start=start_iter, end=end_iter, include_hidden_chars=False
        )

    def set_text(self, text: str) -> None:
        """Definir o texto do editor."""
        self.text_buffer.set_text(text)

    def highlight_char(self, index: int) -> None:
        """Highlight character at specific index."""
        start_iter: Gtk.TextIter = self.buffer.get_iter_at_offset(char_offset=index)
        end_iter: Gtk.TextIter = self.buffer.get_iter_at_offset(char_offset=index + 1)

        self.buffer.remove_tag(
            tag=self.highlight_tag,
            start=self.buffer.get_start_iter(),
            end=self.buffer.get_end_iter(),
        )
        self.buffer.apply_tag(tag=self.highlight_tag, start=start_iter, end=end_iter)

        _ = self.textview.scroll_to_iter(
            iter=start_iter, within_margin=0.0, use_align=False, xalign=0.0, yalign=0.0
        )

    def set_editable(self, editable: bool) -> None:  # noqa: FBT001
        """Definir se o texto pode ser editado."""
        self.textview.set_editable(setting=editable)
