import sys

from ui import Aplicacao

if __name__ == '__main__':
    app = Aplicacao()
    sys.exit(app.run(sys.argv))
