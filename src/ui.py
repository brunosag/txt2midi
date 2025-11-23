from pathlib import Path
from typing import override

import gi

from audio import GeradorMIDI, PlayerAudio
from constantes import DEFAULT_SOUNDFONT, INSTRUMENTOS
from eventos import EventoMusical
from modelo import EstadoMusical
from processador import MapeadorRegras

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

        # Estado da aplicação
        self.estado_musical: EstadoMusical = EstadoMusical()
        self.mapeador: MapeadorRegras = MapeadorRegras()
        self.gerador_midi: GeradorMIDI = GeradorMIDI()
        self.player_thread: PlayerAudio | None = None
        self.soundfont_path: Path = DEFAULT_SOUNDFONT
        self.caminho_txt_atual: Path | None = None

        # Inicializar componentes lógicos
        self.lista_instrumentos_store: Gtk.StringList = Gtk.StringList.new(
            [nome for _id, nome in INSTRUMENTOS],
        )

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
        self._construir_painel_config()
        self._construir_editor_texto()

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

        box_esquerda.append(self.btn_abrir)  # Adicionar ao box da esquerda

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

        box_esquerda.append(self.btn_menu_salvar)  # Adicionar ao box da esquerda

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

    def _construir_painel_config(self) -> None:
        group = Adw.PreferencesGroup()
        group.set_title('Parâmetros iniciais')
        self.prefs_page.add(group)

        # BPM
        adj_bpm = Gtk.Adjustment(
            value=self.estado_musical.bpm,
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
        group.add(self.spin_bpm)

        # Volume
        adj_vol = Gtk.Adjustment(
            value=self.estado_musical.volume,
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
        group.add(self.spin_vol)

        # Oitava
        adj_oitava = Gtk.Adjustment(
            value=self.estado_musical.oitava,
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
        group.add(self.spin_oitava)

        # Instrumento
        self.combo_row_inst: Adw.ComboRow = Adw.ComboRow()
        self.combo_row_inst.set_title('Instrumento inicial')
        self.combo_row_inst.set_model(self.lista_instrumentos_store)
        self.combo_row_inst.set_selected(0)  # Acoustic Grand Piano
        group.add(self.combo_row_inst)

    def _construir_editor_texto(self) -> None:
        """Construir o editor de texto dentro de um grupo."""
        text_group = Adw.PreferencesGroup()
        text_group.set_title('Texto de entrada')
        text_group.set_description('Insira o texto para geração da música.')
        self.prefs_page.add(text_group)

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
        text_group.add(text_frame)

    def _atualizar_estado_dos_controles(self) -> None:
        """Ler os valores da interface e atualizar o `EstadoMusical`."""
        self.estado_musical.bpm = int(self.spin_bpm.get_value())
        self.estado_musical.volume = int(self.spin_vol.get_value())
        self.estado_musical.oitava = int(self.spin_oitava.get_value())

        idx_inst = self.combo_row_inst.get_selected()
        self.estado_musical.instrumento_id = INSTRUMENTOS[idx_inst][0]

    def _on_tocar_clicked(self, _widget: Gtk.Button) -> None:
        """Iniciar a reprodução em uma thread."""
        self._atualizar_estado_dos_controles()
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        texto = self.text_buffer.get_text(
            start=start_iter, end=end_iter, include_hidden_chars=False
        )

        # Processar texto (utilizando cópia)
        estado_para_playback = EstadoMusical()
        estado_para_playback.bpm = self.estado_musical.bpm
        estado_para_playback.volume = self.estado_musical.volume
        estado_para_playback.oitava = self.estado_musical.oitava
        estado_para_playback.instrumento_id = self.estado_musical.instrumento_id

        eventos = self.mapeador.processar_texto(texto, estado_para_playback)

        # Iniciar a thread do player
        self.player_thread = PlayerAudio(
            soundfont_path=self.soundfont_path,
            eventos=eventos,
            estado_inicial=estado_para_playback,
        )
        self.player_thread.callback_parada = self._on_playback_terminado
        self.player_thread.start()

        # Atualizar interface
        self.btn_tocar.set_sensitive(False)
        self.btn_parar.set_sensitive(True)

    def _on_parar_clicked(self, _widget: Gtk.Button) -> None:
        """Solicitar que a thread do player pare."""
        if self.player_thread and self.player_thread.is_alive():
            self.player_thread.parar()

    def _on_playback_terminado(self) -> None:
        """Limpar thread do player e atualizar botões de reprodução."""
        self.player_thread = None
        self.btn_tocar.set_sensitive(True)
        self.btn_parar.set_sensitive(False)

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
        if response == Gtk.ResponseType.OK:
            try:
                if (file := dialog.get_file()) and (path := file.get_path()):
                    self.caminho_txt_atual = Path(path)
                    with self.caminho_txt_atual.open() as f:
                        conteudo = f.read()
                    self.text_buffer.set_text(conteudo)
                    self.set_title(f'txt2midi - {self.caminho_txt_atual}')
            except Exception as e:  # noqa: BLE001
                self._show_toast(f'Erro ao abrir texto: {e}')
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
        if response == Gtk.ResponseType.OK:
            try:
                if (file := dialog.get_file()) and (path := file.get_path()):
                    caminho_txt = Path(path)
                    start_iter = self.text_buffer.get_start_iter()
                    end_iter = self.text_buffer.get_end_iter()
                    conteudo = self.text_buffer.get_text(
                        start=start_iter, end=end_iter, include_hidden_chars=False
                    )
                    with caminho_txt.open('w') as f:
                        _ = f.write(conteudo)
                    self.caminho_txt_atual = caminho_txt
                    self.set_title(f'txt2midi - {self.caminho_txt_atual}')
                    self._show_toast('Arquivo de texto salvo.')
            except Exception as e:  # noqa: BLE001
                self._show_toast(f'Erro ao salvar texto: {e}')
        dialog.destroy()

    def _on_salvar_midi_clicked(
        self,
        _action: Gio.SimpleAction,
        _param: GLib.Variant,
    ) -> None:
        """Gerar os eventos e salvar o MIDI."""
        # Obter texto
        self._atualizar_estado_dos_controles()
        start_iter = self.text_buffer.get_start_iter()
        end_iter = self.text_buffer.get_end_iter()
        texto = self.text_buffer.get_text(
            start=start_iter, end=end_iter, include_hidden_chars=False
        )

        # Processar texto (utilizando cópia)
        estado_para_midi = EstadoMusical()
        estado_para_midi.bpm = self.estado_musical.bpm
        estado_para_midi.volume = self.estado_musical.volume
        estado_para_midi.oitava = self.estado_musical.oitava
        estado_para_midi.instrumento_id = self.estado_musical.instrumento_id

        eventos = self.mapeador.processar_texto(texto, estado_para_midi)

        # Abrir diálogo de salvar
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
        _ = dialog.connect(
            'response',
            self._on_salvar_midi_response,
            eventos,
            estado_para_midi,
        )
        dialog.show()

    def _on_salvar_midi_response(
        self,
        dialog: Gtk.FileChooserDialog,
        response: Gtk.ResponseType,
        eventos: list[EventoMusical],
        estado_para_midi: EstadoMusical,
    ) -> None:
        """Salvar MIDI."""
        if response == Gtk.ResponseType.OK:
            try:
                if (file := dialog.get_file()) and (path := file.get_path()):
                    caminho = Path(path)
                    if caminho.suffix not in ['.mid', '.midi']:
                        caminho = caminho.with_suffix('.mid')

                    self.gerador_midi.gerar_e_salvar(
                        eventos=eventos,
                        _estado_inicial=estado_para_midi,
                        caminho_arquivo=caminho,
                    )
                    self._show_toast('Arquivo MIDI salvo com sucesso.')

            except Exception as e:  # noqa: BLE001
                self._show_toast(f'Erro ao salvar MIDI: {e}')
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
        if (
            self.window
            and self.window.player_thread
            and self.window.player_thread.is_alive()
        ):
            self.window.player_thread.parar()
        Adw.Application.do_shutdown(self)
