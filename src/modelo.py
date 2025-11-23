class EstadoMusical:
    """Armazena o estado musical atual (BPM, volume, etc.)."""

    def __init__(self) -> None:
        self.bpm: int = 120
        self.volume: int = 100
        self.oitava: int = 5
        self.instrumento_id: int = 0  # Acoustic Grand Piano
        self.ultima_nota_midi: int = -1
        self.tempo_evento: float = 0.0  # Posição inicial em 'batidas'

    def redefinir_para_playback(self):
        """Resetar o estado para nova reprodução."""
        self.ultima_nota_midi = -1
        self.tempo_evento = 0.0

    def duracao_padrao_seg(self):
        """Calcular duração de uma 'batida' em segundos."""
        return 60.0 / self.bpm
