from pathlib import Path
from typing import override

import gi

from application.controller import MusicController
from domain.models import PlaybackSettings
from ui.components import ConfigPanel, TextEditor

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

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
        self.set_title('txt2midi')
        self.set_default_size(600, 700)

        # Controlador da aplicação
        self.controller: MusicController = MusicController()
        self.caminho_txt_atual: Path | None = None

        # Caixa GTK principal
        self.box_principal: Gtk.Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.box_principal)

        # Barra de cabeçalho
        self._construir_header()

        # Sobreposição para notificações
        self.toast_overlay: Adw.ToastOverlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.box_principal.append(self.toast_overlay)

        # PreferencesPage como container principal
        self.prefs_page: Adw.PreferencesPage = Adw.PreferencesPage()
        self.toast_overlay.set_child(self.prefs_page)

        # Adicionar grupos de configuração e texto
        self.config_panel: ConfigPanel = ConfigPanel()
        self.prefs_page.add(self.config_panel)

        self.text_editor: TextEditor = TextEditor()
        self.prefs_page.add(self.text_editor)

    def _construir_header(self) -> None:
        header = Adw.HeaderBar()
        self.box_principal.append(header)

        # Container para botões da esquerda
        box_esquerda = Gtk.Box(spacing=6)
        header.pack_start(box_esquerda)

        # Botão 'Abrir'
        self.btn_abrir: Gtk.Button = Gtk.Button()
        self.btn_abrir.set_label('Abrir')
        self.btn_abrir.set_icon_name('document-open-symbolic')
        self.btn_abrir.set_tooltip_text('Abrir texto')

        # Ação 'Abrir'
        action_abrir_txt: Gio.SimpleAction = Gio.SimpleAction.new('abrir_txt', None)
        _ = action_abrir_txt.connect('activate', self._on_abrir_txt_clicked)
        self.add_action(action_abrir_txt)
        self.btn_abrir.set_action_name('win.abrir_txt')  # Linkar o botão à ação

        box_esquerda.append(self.btn_abrir)

        # --- Novo: Botão 'Importar MIDI' ---
        self.btn_importar: Gtk.Button = Gtk.Button()
        self.btn_importar.set_icon_name('folder-music-symbolic')
        self.btn_importar.set_tooltip_text('Importar MIDI')

        action_importar_midi: Gio.SimpleAction = Gio.SimpleAction.new(
            'importar_midi', None
        )
        _ = action_importar_midi.connect('activate', self._on_importar_midi_clicked)
        self.add_action(action_importar_midi)
        self.btn_importar.set_action_name('win.importar_midi')

        box_esquerda.append(self.btn_importar)
        # -----------------------------------

        # Menu 'Salvar'
        menu_salvar_model = Gio.Menu()
        menu_salvar_model.append('Salvar texto (.txt)', 'win.salvar_txt')
        menu_salvar_model.append('Salvar música (.mid)', 'win.salvar_midi')

        self.btn_menu_salvar: Gtk.MenuButton = Gtk.MenuButton.new()
        self.btn_menu_salvar.set_icon_name('document-save-symbolic')
        self.btn_menu_salvar.set_tooltip_text('Salvar')
        self.btn_menu_salvar.set_menu_model(menu_salvar_model)

        # Ação 'Salvar TXT'
        action_salvar_txt = Gio.SimpleAction.new('salvar_txt', None)
        _ = action_salvar_txt.connect('activate', self._on_salvar_txt_clicked)
        self.add_action(action_salvar_txt)

        # Ação 'Salvar MIDI'
        action_salvar_midi = Gio.SimpleAction.new('salvar_midi', None)
        _ = action_salvar_midi.connect('activate', self._on_salvar_midi_clicked)
        self.add_action(action_salvar_midi)

        box_esquerda.append(self.btn_menu_salvar)

        # Controles
        box_controles = Gtk.Box(spacing=6)
        header.pack_end(box_controles)

        # Botão 'Tocar'
        self.btn_tocar: Gtk.Button = Gtk.Button.new_from_icon_name(
            'media-playback-start-symbolic',
        )
        self.btn_tocar.set_tooltip_text('Tocar música')
        _ = self.btn_tocar.connect('clicked', self._on_tocar_clicked)
        self.btn_tocar.set_sensitive(True)
        box_controles.append(self.btn_tocar)

        # Botão 'Parar'
        self.btn_parar: Gtk.Button = Gtk.Button.new_from_icon_name(
            'media-playback-stop-symbolic',
        )
        self.btn_parar.set_tooltip_text('Parar reprodução')
        _ = self.btn_parar.connect('clicked', self._on_parar_clicked)
        self.btn_parar.set_sensitive(False)  # Desabilitado por padrão
        box_controles.append(self.btn_parar)

    def _get_ui_settings(self) -> PlaybackSettings:
        """Ler os valores da interface e retornar PlaybackSettings."""
        return self.config_panel.get_playback_settings()

    def _get_texto_atual(self) -> str:
        return self.text_editor.get_text()

    def _on_tocar_clicked(self, _widget: Gtk.Button) -> None:
        """Iniciar a reprodução e atualizar interface."""
        settings = self._get_ui_settings()
        texto = self._get_texto_atual()
        soundfont_path = self.config_panel.get_soundfont_path()

        self.controller.play_music(
            text=texto,
            settings=settings,
            soundfont_path=soundfont_path,
            on_finished_callback=self._on_playback_terminado,
            on_progress_callback=self.text_editor.highlight_char,
        )
        # Atualizar interface
        self.btn_tocar.set_sensitive(False)
        self.btn_parar.set_sensitive(True)
        self.text_editor.set_editable(False)

    def _on_parar_clicked(self, _widget: Gtk.Button) -> None:
        """Solicitar parada da reprodução."""
        self.controller.stop_music()

    def _on_playback_terminado(self) -> None:
        """Atualizar botões de reprodução após término."""
        self.btn_tocar.set_sensitive(True)
        self.btn_parar.set_sensitive(False)
        self.text_editor.set_editable(True)

    def _on_abrir_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor de arquivo para carregar texto."""
        dialog = Gtk.FileChooserDialog(
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

        filter_txt = Gtk.FileFilter()
        filter_txt.set_name('Text files (*.txt)')
        filter_txt.add_pattern('*.txt')
        dialog.add_filter(filter_txt)

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
                conteudo = f.read()
            self.text_editor.set_text(conteudo)
            self._show_toast(f"Texto '{self.caminho_txt_atual.name}' carregado.")
        dialog.destroy()

    def _on_importar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor de arquivo para importar MIDI."""
        dialog = Gtk.FileChooserDialog(
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

        filter_midi = Gtk.FileFilter()
        filter_midi.set_name('MIDI files (*.mid, *.midi)')
        filter_midi.add_pattern('*.mid')
        filter_midi.add_pattern('*.midi')
        dialog.add_filter(filter_midi)

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
            try:
                texto_convertido = self.controller.import_midi(Path(path))
                self.text_editor.set_text(texto_convertido)
                self.caminho_txt_atual = None
                self._show_toast('Arquivo MIDI importado com sucesso.')
            except Exception as e:
                self._show_toast(f'Erro ao importar MIDI: {e}')
        dialog.destroy()

    def _on_salvar_txt_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir seletor para salvar texto."""
        dialog = Gtk.FileChooserDialog(
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
            _ = dialog.set_file(Gio.File.new_for_path(str(self.caminho_txt_atual)))
        else:
            dialog.set_current_name('musica.txt')

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
            caminho_txt = Path(path)
            conteudo = self._get_texto_atual()
            with caminho_txt.open('w') as f:
                _ = f.write(conteudo)
            self.caminho_txt_atual = caminho_txt
            self._show_toast('Arquivo de texto salvo.')
        dialog.destroy()

    def _on_salvar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Abrir diálogo de salvar MIDI."""
        dialog = Gtk.FileChooserDialog(
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
        dialog.set_current_name('musica.mid')

        filter_midi = Gtk.FileFilter()
        filter_midi.set_name('MIDI files (*.mid, *.midi)')
        filter_midi.add_pattern('*.mid')
        filter_midi.add_pattern('*.midi')
        dialog.add_filter(filter_midi)
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
            caminho = Path(path)
            if caminho.suffix not in ['.mid', '.midi']:
                caminho = caminho.with_suffix('.mid')

            settings = self._get_ui_settings()
            texto = self._get_texto_atual()

            self.controller.export_midi(
                text=texto,
                settings=settings,
                filepath=caminho,
            )
            self._show_toast('Arquivo MIDI salvo.')
        dialog.destroy()

    def _show_toast(self, mensagem: str) -> None:
        """Mostrar uma notificação (toast) no overlay."""
        toast = Adw.Toast(title=mensagem, timeout=3)
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
            self.window = JanelaPrincipal(self)
        self.window.present()

    @override
    def do_shutdown(self) -> None:
        """Garantir que a thread do player seja encerrada ao fechar."""
        if self.window and self.window.controller:
            self.window.controller.stop_music()
        Adw.Application.do_shutdown(self)
