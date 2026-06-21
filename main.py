import curses
from app import FileBrowserApp

def main(stdscr):
    app = FileBrowserApp(stdscr)
    app.run()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass