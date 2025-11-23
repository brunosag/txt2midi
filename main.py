import sys

from src.ui.main_window import Aplicacao

if __name__ == '__main__':
    app = Aplicacao()
    sys.exit(app.run(sys.argv))
