from pathlib import Path
from typing import cast, override

import gi

from application.controller import MusicController
from domain.parser import ParsingMode
from ui.components import EditorPage

gi.require_version(namespace='Gtk', version='4.0')
gi.require_version(namespace='Adw', version='1')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gio,  # pyright: ignore[reportMissingModuleSource]
    GLib,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
)


@Gtk.Template(filename='src/ui/blueprints/main_window.ui')
class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'MainWindow'

    toast_overlay = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    btn_play = Gtk.Template.Child()
    btn_stop = Gtk.Template.Child()

    page_standard = Gtk.Template.Child()
    page_mml = Gtk.Template.Child()

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)

        self.controller: MusicController = MusicController()

        self.page_standard.text_editor.set_language_id('standard')
        self.page_standard.text_editor.set_text('BPM+ A B C D \n ?')

        self.page_mml.text_editor.set_language_id('mml')
        self.page_mml.text_editor.set_text('T120 I19 C D E F')

        self._add_action(name='open_txt', callback=self._on_open_txt_clicked)
        self._add_action(name='import_midi', callback=self._on_import_midi_clicked)
        self._add_action(name='save_txt', callback=self._on_save_txt_clicked)
        self._add_action(name='save_midi', callback=self._on_save_midi_clicked)

        self.btn_play.connect('clicked', self._on_play_clicked)
        self.btn_stop.connect('clicked', self._on_stop_clicked)

        GLib.idle_add(self.set_focus, None)

    def _add_action(self, name: str, callback) -> None:
        action: Gio.SimpleAction = Gio.SimpleAction.new(name=name, parameter_type=None)
        _ = action.connect('activate', callback)
        self.add_action(action=action)

    def _get_active_page(self) -> EditorPage:
        visible_name = self.view_stack.get_visible_child_name()
        if visible_name == 'mml':
            return self.page_mml
        return self.page_standard

    def _get_active_mode(self) -> ParsingMode:
        return cast('ParsingMode', self.view_stack.get_visible_child_name())

    def _on_play_clicked(self, _widget: Gtk.Button) -> None:
        page: EditorPage = self._get_active_page()
        mode: ParsingMode = self._get_active_mode()

        self.controller.play_music(
            text=page.get_text(),
            settings=page.get_settings(),
            mode=mode,
            soundfont_path=page.get_soundfont_path(),
            on_finished_callback=self._on_playback_finished,
            on_progress_callback=page.text_editor.highlight_range,
        )
        self.btn_play.set_sensitive(sensitive=False)
        self.btn_stop.set_sensitive(sensitive=True)
        page.text_editor.set_editable(editable=False)

    def _on_stop_clicked(self, _widget: Gtk.Button) -> None:
        self.controller.stop_music()

    def _on_playback_finished(self) -> None:
        self.btn_play.set_sensitive(sensitive=True)
        self.btn_stop.set_sensitive(sensitive=False)
        self._get_active_page().text_editor.set_editable(editable=True)

    def _run_file_dialog(
        self, title: str, action, filter_name: str, filter_pattern: str, callback
    ) -> None:
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title=title,
            transient_for=self,
            action=action,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        confirm_label = '_Ok' if action == Gtk.FileChooserAction.OPEN else '_Salvar'
        _ = dialog.add_button(
            button_text=confirm_label, response_id=Gtk.ResponseType.OK
        )

        file_filter: Gtk.FileFilter = Gtk.FileFilter()
        file_filter.set_name(name=filter_name)
        file_filter.add_pattern(pattern=filter_pattern)
        if filter_pattern == '*.mid':
            file_filter.add_pattern(pattern='*.midi')

        dialog.add_filter(filter=file_filter)
        _ = dialog.connect('response', callback)
        dialog.show()

    def _on_open_txt_clicked(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        self._run_file_dialog(
            title='Importar texto',
            action=Gtk.FileChooserAction.OPEN,
            filter_name='Arquivos de texto (*.txt)',
            filter_pattern='*.txt',
            callback=self._on_open_txt_response,
        )

    def _on_open_txt_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            file_path = Path(path)
            content = file_path.read_text(encoding='utf-8')
            self._get_active_page().text_editor.set_text(text=content)
            self._show_toast(message=f'Carregado: {file_path.name}')
        dialog.destroy()

    def _on_import_midi_clicked(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        self._run_file_dialog(
            title='Importar MIDI',
            action=Gtk.FileChooserAction.OPEN,
            filter_name='Arquivos MIDI (*.mid, *.midi)',
            filter_pattern='*.mid',
            callback=self._on_import_midi_response,
        )

    def _on_import_midi_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            text, inst, vol, bpm = self.controller.import_midi(file_path=Path(path))

            self.view_stack.set_visible_child_name(name='mml')
            page: EditorPage = self.page_mml

            page.text_editor.set_text(text=text)
            page.config_panel.set_instrument(instrument_id=inst)
            page.config_panel.set_volume(volume=vol)
            page.config_panel.set_bpm(bpm=bpm)

            self._show_toast(message='MIDI importado.')
        dialog.destroy()

    def _on_save_txt_clicked(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        self._run_file_dialog(
            title='Salvar texto',
            action=Gtk.FileChooserAction.SAVE,
            filter_name='Arquivos de texto (*.txt)',
            filter_pattern='*.txt',
            callback=self._on_save_txt_response,
        )

    def _on_save_txt_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            file_path = Path(path)
            file_path.write_text(self._get_active_page().get_text(), encoding='utf-8')
            self._show_toast(message='Texto salvo.')
        dialog.destroy()

    def _on_save_midi_clicked(
        self, _action: Gio.SimpleAction, _param: GLib.Variant
    ) -> None:
        self._run_file_dialog(
            title='Salvar MIDI',
            action=Gtk.FileChooserAction.SAVE,
            filter_name='Arquivos MIDI (*.mid, *.midi)',
            filter_pattern='*.mid',
            callback=self._on_save_midi_response,
        )

    def _on_save_midi_response(
        self, dialog: Gtk.FileChooserDialog, response: Gtk.ResponseType
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            file_path = Path(path)
            if file_path.suffix not in ['.mid', '.midi']:
                file_path = file_path.with_suffix(suffix='.mid')

            page: EditorPage = self._get_active_page()
            self.controller.export_midi(
                text=page.get_text(),
                settings=page.get_settings(),
                mode=self._get_active_mode(),
                file_path=file_path,
            )
            self._show_toast(message='MIDI exportado.')
        dialog.destroy()

    def _show_toast(self, message: str) -> None:
        toast: Adw.Toast = Adw.Toast(title=message, timeout=3)
        self.toast_overlay.add_toast(toast)


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id='br.ufrgs.inf01120.tcp')
        self.window: MainWindow | None = None

    @override
    def do_activate(self) -> None:
        if not self.window:
            self.window = MainWindow(app=self)
        self.window.present()

    @override
    def do_shutdown(self) -> None:
        if self.window and self.window.controller:
            self.window.controller.stop_music()
        Adw.Application.do_shutdown(self)
