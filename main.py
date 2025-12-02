import sys

from ui.main_window import Application

if __name__ == '__main__':
    app = Application()
    sys.exit(app.run(sys.argv))
