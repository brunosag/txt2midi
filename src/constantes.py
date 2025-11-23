from pathlib import Path

# Caminho padrão para o SoundFont
DEFAULT_SOUNDFONT = Path('FluidR3_GM.sf2')

# Mapeamento de notas base (Oitava 5) para números MIDI
NOTAS_MIDI_BASE = {
    'C': 60,
    'D': 62,
    'E': 64,
    'F': 65,
    'G': 67,
    'A': 69,
    'B': 71,
    'H': 70,  # Bb
}

# Mapeamento de IDs do General MIDI para nomes
INSTRUMENTOS = [
    (0, 'Acoustic Grand Piano'),
    (24, 'Acoustic Guitar (nylon)'),
    (33, 'Electric Bass (finger)'),
    (40, 'Violin'),
    (56, 'Trumpet'),
    (65, 'Alto Sax'),
    (73, 'Flute'),
    (15, 'Tubular Bells'),
    (110, 'Bag pipe'),
    (114, 'Agogo'),
    (123, 'Seashore'),
    (125, 'Telephone Ring'),
    (127, 'Gunshot'),
]

# Valor máximo para dados MIDI (notas, volume, etc.)
MAX_MIDI_VALUE = 127
