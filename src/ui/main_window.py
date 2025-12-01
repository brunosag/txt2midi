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
    GObject,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
)


class JanelaPrincipal(Adw.ApplicationWindow):
    """Janela principal da aplicação com suporte a abas."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.app: Adw.Application = app
        self.set_title(title='txt2midi')
        self.set_default_size(width=430, height=750)

        # Controlador da aplicação
        self.controller: MusicController = MusicController()

        # Toolbar View
        self.toolbar_view: Adw.ToolbarView = Adw.ToolbarView()
        self.set_content(content=self.toolbar_view)

        # Barra de cabeçalho
        self._construir_header()

        # Sobreposição para notificações
        self.toast_overlay: Adw.ToastOverlay = Adw.ToastOverlay()
        self.toolbar_view.set_content(content=self.toast_overlay)

        # Container de Abas (Stack)
        self.view_stack: Adw.ViewStack = Adw.ViewStack()
        self.toast_overlay.set_child(child=self.view_stack)

        # Aba 1: Modo Padrão
        self.page_standard: EditorPage = EditorPage(
            title='Padrão',
            lang_id='standard',
            icon_name='text-x-generic-symbolic',
            default_text='BPM+ A B C D \n ?',
        )

        page_std = self.view_stack.add_titled(
            child=self.page_standard, name='standard', title='Padrão'
        )
        page_std.set_icon_name('text-x-generic-symbolic')

        # Aba 2: Modo MML
        self.page_mml: EditorPage = EditorPage(
            title='MML',
            lang_id='tcp',
            icon_name='music-note-symbolic',
            default_text='T120 I19 C D E F',
        )

        page_mml = self.view_stack.add_titled(
            child=self.page_mml, name='mml', title='MML'
        )
        page_mml.set_icon_name('music-note-symbolic')

        self.switcher_title.set_stack(stack=self.view_stack)
        self._construir_bottom_bar()

    def _construir_header(self) -> None:
        header: Adw.HeaderBar = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(widget=header)

        # Widget central: Título com switcher de abas
        self.switcher_title: Adw.ViewSwitcherTitle = Adw.ViewSwitcherTitle()
        header.set_title_widget(title_widget=self.switcher_title)

        # Esquerda: Botão de menu
        self.btn_menu: Gtk.MenuButton = Gtk.MenuButton()
        self.btn_menu.set_icon_name(icon_name='open-menu-symbolic')
        self.btn_menu.set_tooltip_text(text='Menu Principal')

        # Modelo do menu
        menu_model: Gio.Menu = Gio.Menu()

        section_file: Gio.Menu = Gio.Menu()
        section_file.append(label='Importar texto...', detailed_action='win.abrir_txt')
        section_file.append(
            label='Importar MIDI...', detailed_action='win.importar_midi'
        )
        menu_model.append_section(label=None, section=section_file)

        section_save: Gio.Menu = Gio.Menu()
        section_save.append(label='Salvar texto...', detailed_action='win.salvar_txt')
        section_save.append(label='Salvar MIDI...', detailed_action='win.salvar_midi')
        menu_model.append_section(label=None, section=section_save)

        self.btn_menu.set_menu_model(menu_model=menu_model)
        header.pack_start(child=self.btn_menu)

        # Ações do menu
        self._add_action(name='abrir_txt', callback=self._on_abrir_txt_clicked)
        self._add_action(name='importar_midi', callback=self._on_importar_midi_clicked)
        self._add_action(name='salvar_txt', callback=self._on_salvar_txt_clicked)
        self._add_action(name='salvar_midi', callback=self._on_salvar_midi_clicked)

        # Direita: Controles de reprodução
        box_controles: Gtk.Box = Gtk.Box(spacing=6)
        header.pack_end(child=box_controles)

        self.btn_tocar: Gtk.Button = Gtk.Button.new_from_icon_name(
            icon_name='media-playback-start-symbolic',
        )
        self.btn_tocar.set_tooltip_text(text='Tocar música')
        _ = self.btn_tocar.connect('clicked', self._on_tocar_clicked)
        box_controles.append(child=self.btn_tocar)

        self.btn_parar: Gtk.Button = Gtk.Button.new_from_icon_name(
            icon_name='media-playback-stop-symbolic',
        )
        self.btn_parar.set_tooltip_text(text='Parar reprodução')
        self.btn_parar.set_sensitive(sensitive=False)
        _ = self.btn_parar.connect('clicked', self._on_parar_clicked)
        box_controles.append(child=self.btn_parar)

    def _construir_bottom_bar(self) -> None:
        """Adiciona a barra inferior que aparece em telas estreitas."""
        switcher_bar: Adw.ViewSwitcherBar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(stack=self.view_stack)
        self.toolbar_view.add_bottom_bar(widget=switcher_bar)

        # Revelar a barra inferior apenas quando o título estiver visível (modo mobile)
        _ = self.switcher_title.bind_property(
            'title-visible',
            switcher_bar,
            'reveal',
            GObject.BindingFlags.SYNC_CREATE,
        )

    def _add_action(self, name: str, callback) -> None:
        action: Gio.SimpleAction = Gio.SimpleAction.new(name=name, parameter_type=None)
        _ = action.connect('activate', callback)
        self.add_action(action=action)

    def _get_active_page(self) -> EditorPage:
        """Retorna a página (aba) atualmente visível."""
        visible_name = self.view_stack.get_visible_child_name()
        if visible_name == 'mml':
            return self.page_mml
        return self.page_standard

    def _get_active_mode(self) -> ParsingMode:
        """Retorna o modo de parsing baseado na aba ativa."""
        return cast('ParsingMode', self.view_stack.get_visible_child_name())

    def _on_tocar_clicked(self, _widget: Gtk.Button) -> None:
        """Iniciar a reprodução usando o contexto da aba ativa."""
        page: EditorPage = self._get_active_page()
        mode: ParsingMode = self._get_active_mode()

        self.controller.play_music(
            text=page.get_text(),
            settings=page.get_settings(),
            mode=mode,
            soundfont_path=page.get_soundfont_path(),
            on_finished_callback=self._on_playback_terminado,
            on_progress_callback=page.text_editor.highlight_char,
        )
        self.btn_tocar.set_sensitive(sensitive=False)
        self.btn_parar.set_sensitive(sensitive=True)
        page.text_editor.set_editable(editable=False)

    def _on_parar_clicked(self, _widget: Gtk.Button) -> None:
        self.controller.stop_music()

    def _on_playback_terminado(self) -> None:
        self.btn_tocar.set_sensitive(sensitive=True)
        self.btn_parar.set_sensitive(sensitive=False)
        self._get_active_page().text_editor.set_editable(editable=True)

    def _on_abrir_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Abrir arquivo',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        _ = dialog.add_button(button_text='_Abrir', response_id=Gtk.ResponseType.OK)

        filter_txt: Gtk.FileFilter = Gtk.FileFilter()
        filter_txt.set_name(name='Arquivos de texto (*.txt)')
        filter_txt.add_pattern(pattern='*.txt')
        dialog.add_filter(filter=filter_txt)

        _ = dialog.connect('response', self._on_abrir_txt_response)
        dialog.show()

    def _on_abrir_txt_response(
        self,
        dialog: Gtk.FileChooserDialog,
        response: Gtk.ResponseType,
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            caminho: Path = Path(path)
            with caminho.open() as f:
                conteudo: str = f.read()
            self._get_active_page().text_editor.set_text(text=conteudo)
            self._show_toast(mensagem=f'Carregado: {caminho.name}')
        dialog.destroy()

    def _on_importar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Importar MIDI',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        _ = dialog.add_button(button_text='_Importar', response_id=Gtk.ResponseType.OK)

        filter_midi: Gtk.FileFilter = Gtk.FileFilter()
        filter_midi.set_name(name='Arquivos MIDI (*.mid, *.midi)')
        filter_midi.add_pattern(pattern='*.mid')
        filter_midi.add_pattern(pattern='*.midi')
        dialog.add_filter(filter=filter_midi)

        _ = dialog.connect('response', self._on_importar_midi_response)
        dialog.show()

    def _on_importar_midi_response(
        self,
        dialog: Gtk.FileChooserDialog,
        response: Gtk.ResponseType,
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            texto, inst, vol, bpm = self.controller.import_midi(filepath=Path(path))

            self.view_stack.set_visible_child_name(name='mml')
            page: EditorPage = self.page_mml

            page.text_editor.set_text(text=texto)
            page.config_panel.set_instrument(instrument_id=inst)
            page.config_panel.set_volume(volume=vol)
            page.config_panel.set_bpm(bpm=bpm)

            self._show_toast(mensagem='MIDI importado.')
        dialog.destroy()

    def _on_salvar_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Salvar texto',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        _ = dialog.add_button(button_text='_Salvar', response_id=Gtk.ResponseType.OK)
        dialog.set_current_name(name='musica.txt')

        _ = dialog.connect('response', self._on_salvar_txt_response)
        dialog.show()

    def _on_salvar_txt_response(
        self,
        dialog: Gtk.FileChooserDialog,
        response: Gtk.ResponseType,
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            caminho: Path = Path(path)
            with caminho.open('w') as f:
                _ = f.write(self._get_active_page().get_text())
            self._show_toast(mensagem='Arquivo salvo.')
        dialog.destroy()

    def _on_salvar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Salvar MIDI',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        _ = dialog.add_button(
            button_text='_Cancelar', response_id=Gtk.ResponseType.CANCEL
        )
        _ = dialog.add_button(button_text='_Salvar', response_id=Gtk.ResponseType.OK)
        dialog.set_current_name(name='musica.mid')

        filter_midi: Gtk.FileFilter = Gtk.FileFilter()
        filter_midi.set_name(name='MIDI files (*.mid, *.midi)')
        filter_midi.add_pattern(pattern='*.mid')
        filter_midi.add_pattern(pattern='*.midi')
        dialog.add_filter(filter=filter_midi)

        _ = dialog.connect('response', self._on_salvar_midi_response)
        dialog.show()

    def _on_salvar_midi_response(
        self,
        dialog: Gtk.FileChooserDialog,
        response: Gtk.ResponseType,
    ) -> None:
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            caminho: Path = Path(path)
            if caminho.suffix not in ['.mid', '.midi']:
                caminho = caminho.with_suffix(suffix='.mid')

            page: EditorPage = self._get_active_page()

            self.controller.export_midi(
                text=page.get_text(),
                settings=page.get_settings(),
                mode=self._get_active_mode(),
                filepath=caminho,
            )
            self._show_toast(mensagem='MIDI exportado.')
        dialog.destroy()

    def _show_toast(self, mensagem: str) -> None:
        toast: Adw.Toast = Adw.Toast(title=mensagem, timeout=3)
        self.toast_overlay.add_toast(toast)


class Aplicacao(Adw.Application):
    """Classe principal da aplicação Adwaita."""

    def __init__(self) -> None:
        super().__init__(application_id='br.ufrgs.inf01120.tcp')
        self.window: JanelaPrincipal | None = None

    @override
    def do_activate(self) -> None:
        """Chamado quando a aplicação é ativada."""
        if not self.window:
            self.window = JanelaPrincipal(app=self)
        self.window.present()

    @override
    def do_shutdown(self) -> None:
        """Garantir que a thread do player seja encerrada ao fechar."""
        if self.window and self.window.controller:
            self.window.controller.stop_music()
        Adw.Application.do_shutdown(self)
