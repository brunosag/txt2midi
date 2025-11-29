from pathlib import Path
from typing import override

import gi

from application.controller import MusicController
from domain.models import PlaybackSettings
from ui.components import ConfigPanel, TextEditor

gi.require_version(namespace='Gtk', version='4.0')
gi.require_version(namespace='Adw', version='1')

from gi.repository import (  # noqa: E402
    Adw,  # pyright: ignore[reportMissingModuleSource]
    Gio,  # pyright: ignore[reportMissingModuleSource]
    GLib,  # pyright: ignore[reportMissingModuleSource]
    Gtk,  # pyright: ignore[reportMissingModuleSource]
)


class JanelaPrincipal(Adw.ApplicationWindow):
    """Janela principal da aplicação."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.app: Adw.Application = app
        self.set_title(title='txt2midi')
        self.set_default_size(width=600, height=700)

        # Controlador da aplicação
        self.controller: MusicController = MusicController()
        self.caminho_txt_atual: Path | None = None

        # Caixa GTK principal
        self.box_principal: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content=self.box_principal)

        # Barra de cabeçalho
        self._construir_header()

        # Sobreposição para notificações
        self.toast_overlay: Adw.ToastOverlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(expand=True)
        self.box_principal.append(child=self.toast_overlay)

        # PreferencesPage como container principal
        self.prefs_page: Adw.PreferencesPage = Adw.PreferencesPage()
        self.toast_overlay.set_child(child=self.prefs_page)

        # Adicionar grupos de configuração e texto
        self.config_panel: ConfigPanel = ConfigPanel()
        self.prefs_page.add(group=self.config_panel)

        self.text_editor: TextEditor = TextEditor()
        self.prefs_page.add(group=self.text_editor)

    def _construir_header(self) -> None:
        header: Adw.HeaderBar = Adw.HeaderBar()
        self.box_principal.append(child=header)

        # Container para botões da esquerda
        box_esquerda = Gtk.Box(spacing=6)
        header.pack_start(child=box_esquerda)

        # Botão 'Abrir'
        self.btn_abrir: Gtk.Button = Gtk.Button()
        self.btn_abrir.set_label(label='Abrir')
        self.btn_abrir.set_icon_name(icon_name='document-open-symbolic')
        self.btn_abrir.set_tooltip_text(text='Abrir texto')

        # Ação 'Abrir'
        action_abrir_txt: Gio.SimpleAction = Gio.SimpleAction.new(
            name='abrir_txt', parameter_type=None
        )
        _ = action_abrir_txt.connect('activate', self._on_abrir_txt_clicked)
        self.add_action(action=action_abrir_txt)
        self.btn_abrir.set_action_name(action_name='win.abrir_txt')
        box_esquerda.append(child=self.btn_abrir)

        # Botão 'Importar MIDI'
        self.btn_importar: Gtk.Button = Gtk.Button()
        self.btn_importar.set_icon_name(icon_name='folder-music-symbolic')
        self.btn_importar.set_tooltip_text(text='Importar MIDI')

        # Ação 'Importar MIDI'
        action_importar_midi: Gio.SimpleAction = Gio.SimpleAction.new(
            name='importar_midi', parameter_type=None
        )
        _ = action_importar_midi.connect('activate', self._on_importar_midi_clicked)
        self.add_action(action=action_importar_midi)
        self.btn_importar.set_action_name(action_name='win.importar_midi')
        box_esquerda.append(child=self.btn_importar)

        # Menu 'Salvar'
        menu_salvar_model: Gio.Menu = Gio.Menu()
        menu_salvar_model.append(
            label='Salvar texto (.txt)', detailed_action='win.salvar_txt'
        )
        menu_salvar_model.append(
            label='Salvar música (.mid)', detailed_action='win.salvar_midi'
        )

        self.btn_menu_salvar: Gtk.MenuButton = Gtk.MenuButton.new()
        self.btn_menu_salvar.set_icon_name(icon_name='document-save-symbolic')
        self.btn_menu_salvar.set_tooltip_text(text='Salvar')
        self.btn_menu_salvar.set_menu_model(menu_model=menu_salvar_model)

        # Ação 'Salvar TXT'
        action_salvar_txt: Gio.SimpleAction = Gio.SimpleAction.new(name='salvar_txt')
        _ = action_salvar_txt.connect('activate', self._on_salvar_txt_clicked)
        self.add_action(action=action_salvar_txt)

        # Ação 'Salvar MIDI'
        action_salvar_midi: Gio.SimpleAction = Gio.SimpleAction.new(name='salvar_midi')
        _ = action_salvar_midi.connect('activate', self._on_salvar_midi_clicked)
        self.add_action(action=action_salvar_midi)
        box_esquerda.append(child=self.btn_menu_salvar)

        # Controles
        box_controles: Gtk.Box = Gtk.Box(spacing=6)
        header.pack_end(child=box_controles)

        # Botão 'Tocar'
        self.btn_tocar: Gtk.Button = Gtk.Button.new_from_icon_name(
            icon_name='media-playback-start-symbolic',
        )
        self.btn_tocar.set_tooltip_text(text='Tocar música')
        _ = self.btn_tocar.connect('clicked', self._on_tocar_clicked)
        self.btn_tocar.set_sensitive(sensitive=True)
        box_controles.append(child=self.btn_tocar)

        # Botão 'Parar'
        self.btn_parar: Gtk.Button = Gtk.Button.new_from_icon_name(
            icon_name='media-playback-stop-symbolic',
        )
        self.btn_parar.set_tooltip_text(text='Parar reprodução')
        _ = self.btn_parar.connect('clicked', self._on_parar_clicked)
        self.btn_parar.set_sensitive(sensitive=False)
        box_controles.append(child=self.btn_parar)

    def _get_ui_settings(self) -> PlaybackSettings:
        """Ler os valores da interface e retornar PlaybackSettings."""
        return self.config_panel.get_playback_settings()

    def _get_texto_atual(self) -> str:
        return self.text_editor.get_text()

    def _on_tocar_clicked(self, _widget: Gtk.Button) -> None:
        """Iniciar a reprodução e atualizar interface."""
        settings: PlaybackSettings = self._get_ui_settings()
        texto: str = self._get_texto_atual()
        soundfont_path: Path = self.config_panel.get_soundfont_path()

        self.controller.play_music(
            text=texto,
            settings=settings,
            soundfont_path=soundfont_path,
            on_finished_callback=self._on_playback_terminado,
            on_progress_callback=self.text_editor.highlight_char,
        )
        self.btn_tocar.set_sensitive(sensitive=False)
        self.btn_parar.set_sensitive(sensitive=True)
        self.text_editor.set_editable(editable=False)

    def _on_parar_clicked(self, _widget: Gtk.Button) -> None:
        """Solicitar parada da reprodução."""
        self.controller.stop_music()

    def _on_playback_terminado(self) -> None:
        """Atualizar botões de reprodução após término."""
        self.btn_tocar.set_sensitive(sensitive=True)
        self.btn_parar.set_sensitive(sensitive=False)
        self.text_editor.set_editable(editable=True)

    def _on_abrir_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor de arquivo para carregar texto."""
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Abrir arquivo',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button(
            button_text='_Cancelar',
            response_id=Gtk.ResponseType.CANCEL,
        )
        _ = dialog.add_button(
            button_text='_Abrir',
            response_id=Gtk.ResponseType.OK,
        )

        filter_txt: Gtk.FileFilter = Gtk.FileFilter()
        filter_txt.set_name(name='Text files (*.txt)')
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
            self.caminho_txt_atual = Path(path)
            with self.caminho_txt_atual.open() as f:
                conteudo: str = f.read()
            self.text_editor.set_text(text=conteudo)
            self._show_toast(
                mensagem=f"Texto '{self.caminho_txt_atual.name}' carregado."
            )
        dialog.destroy()

    def _on_importar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor de arquivo para importar MIDI."""
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Importar MIDI',
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        _ = dialog.add_button(
            button_text='_Cancelar',
            response_id=Gtk.ResponseType.CANCEL,
        )
        _ = dialog.add_button(
            button_text='_Importar',
            response_id=Gtk.ResponseType.OK,
        )

        filter_midi: Gtk.FileFilter = Gtk.FileFilter()
        filter_midi.set_name(name='MIDI files (*.mid, *.midi)')
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
            texto_convertido, inst_id, vol, bpm = self.controller.import_midi(
                filepath=Path(path)
            )
            self.text_editor.set_text(text=texto_convertido)
            self.config_panel.set_instrument(instrument_id=inst_id)
            self.config_panel.set_volume(volume=vol)
            self.config_panel.set_bpm(bpm=bpm)

            self.caminho_txt_atual = None
            self._show_toast(mensagem='Arquivo MIDI importado com sucesso.')
        dialog.destroy()

    def _on_salvar_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor para salvar texto."""
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Salvar texto',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        _ = dialog.add_button(
            button_text='_Cancelar',
            response_id=Gtk.ResponseType.CANCEL,
        )
        _ = dialog.add_button(
            button_text='_Salvar',
            response_id=Gtk.ResponseType.OK,
        )

        if self.caminho_txt_atual:
            _ = dialog.set_file(
                file=Gio.File.new_for_path(path=str(self.caminho_txt_atual))
            )
        else:
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
            caminho_txt: Path = Path(path)
            conteudo: str = self._get_texto_atual()
            with caminho_txt.open('w') as f:
                _ = f.write(conteudo)
            self.caminho_txt_atual = caminho_txt
            self._show_toast(mensagem='Arquivo de texto salvo.')
        dialog.destroy()

    def _on_salvar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir diálogo de salvar MIDI."""
        dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
            title='Salvar MIDI',
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        _ = dialog.add_button(
            button_text='_Cancelar',
            response_id=Gtk.ResponseType.CANCEL,
        )
        _ = dialog.add_button(
            button_text='_Salvar',
            response_id=Gtk.ResponseType.OK,
        )
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
        """Salvar MIDI."""
        if (
            response == Gtk.ResponseType.OK
            and (file := dialog.get_file())
            and (path := file.get_path())
        ):
            caminho: Path = Path(path)
            if caminho.suffix not in ['.mid', '.midi']:
                caminho = caminho.with_suffix(suffix='.mid')

            settings: PlaybackSettings = self._get_ui_settings()
            texto: str = self._get_texto_atual()

            self.controller.export_midi(
                text=texto,
                settings=settings,
                filepath=caminho,
            )
            self._show_toast(mensagem='Arquivo MIDI salvo.')
        dialog.destroy()

    def _show_toast(self, mensagem: str) -> None:
        """Mostrar uma notificação (toast) no overlay."""
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
