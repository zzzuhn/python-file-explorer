import curses

class CursesUI():
    def init_curses(self):
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)     # dir
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)    # status
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # size
        curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # date


