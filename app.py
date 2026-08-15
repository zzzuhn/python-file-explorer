import os
import shutil
import curses
import subprocess
import pyperclip
from ui import CursesUI

from utils import (
    get_mtime,
    get_size,
    read_file,
    get_open_with,
    launch_default
)


class FileBrowserApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.ui = CursesUI()
        self.ui.init_curses()

        self.stdscr.keypad(True)

        self.current_dir: str = "."
        self.selected: int = 0
        self.offset: int = 0
        self.right_selected: int = 0
        self.right_offset: int = 0
        self.active_panel: str = "left"

        self.open_menu: bool = False
        self.open_items: list = []
        self.open_index: int = 0
        self.open_path: str = None
        self.copied_path: str = None

        self.delete_confirm: bool = False
        self.delete_path: str = None
        self.delete_index: int = 0
        self.help_menu: bool = False

        self.help_items = [
            ("q", "Quit"),
            ("ENTER", "Open file/folder"),
            ("UP/DOWN", "Navigate"),
            ("LEFT", "Focus left panel"),
            ("RIGHT", "Focus right panel"),
            ("c", "Copy file"),
            ("v", "Paste file"),
            ("d", "Delete file/folder"),
            ("x", "Go to clipboard path"),
            ("h", "Toggle help"),
            ("ESC", "Close dialogs")
        ]
        


    def render(self) -> tuple[list, str, int]:
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        panel_h = h - 2
        panel_w = w // 2

        left = curses.newwin(panel_h, panel_w, 1, 0)
        right = curses.newwin(panel_h, panel_w, 1, panel_w)

        items = sorted(os.listdir(self.current_dir))
        items.insert(0, "..")

        selected_item = items[self.selected]
        selected_path = os.path.join(self.current_dir, selected_item)

        left.box()

        full_path = os.path.abspath(self.current_dir) + '\\'
        left.addstr(0, 2, full_path[:panel_w - 4])

        visible = items[self.offset:self.offset + panel_h - 4]

        for i, item in enumerate(visible):
            path = os.path.join(self.current_dir, item)
            is_dir = os.path.isdir(path)

            name = item + ("/" if is_dir else "")
            size = get_size(path)
            mtime = get_mtime(path)

            attr = curses.A_REVERSE if (self.offset + i) == self.selected else 0

            left.addstr(i + 2, 2, f"{size:>8}", curses.color_pair(3) | attr)
            left.addstr(i + 2, 12, " ")
            left.addstr(i + 2, 13, mtime[:16], curses.color_pair(4) | attr)
            left.addstr(i + 2, 30, " ")

            if is_dir:
                left.addstr(i + 2, 31, name[:panel_w - 31 - 2], curses.color_pair(1) | attr)
            else:
                left.addstr(i + 2, 31, name[:panel_w - 31 - 2], attr)

        right.box()

        if self.open_menu:
            right.addstr(1, 2, "OPEN WITH:", curses.A_BOLD)

            for i, (name, _) in enumerate(self.open_items):
                attr = curses.A_REVERSE if i == self.open_index else 0
                right.addstr(3 + i, 2, name[:panel_w - 4], attr)
        else:
            if self.help_menu:

                right.addstr(2, 2, "HELP", curses.A_BOLD | curses.color_pair(1))


                for i, (key_name, desc) in enumerate(self.help_items):
                    y = i + 4

                    if y >= panel_h - 1:
                        break

                    right.addstr(y, 4, key_name.ljust(10), curses.color_pair(3) | curses.A_BOLD)

                    right.addstr(y, 16, desc, curses.color_pair(4))

            elif self.delete_confirm:

                filename = os.path.basename(self.delete_path)

                right.addstr(2, 2, f"Are you sure to delete:")
                right.addstr(3, 2, filename[:panel_w - 4], curses.A_BOLD)

                yes_attr = curses.A_REVERSE if self.delete_index == 0 else 0
                no_attr = curses.A_REVERSE if self.delete_index == 1 else 0

                right.addstr(6, 2, "YES", yes_attr)
                right.addstr(7, 2, "NO", no_attr)

            elif os.path.isfile(selected_path):
                ok, lines = read_file(selected_path)

                if ok:
                    visible_h = panel_h - 4

                    max_scroll = max(0, len(lines) - visible_h)
                    self.right_offset = max(0, min(self.right_offset, max_scroll))

                    view = lines[self.right_offset:self.right_offset + visible_h]

                    for i, line in enumerate(view):
                        absolute_index = self.right_offset + i

                        attr = curses.A_REVERSE if absolute_index == self.right_selected else 0

                        right.addstr(2 + i, 2, line[:panel_w - 4], attr)

                        if i == len(view) - 1 and self.right_offset + visible_h < len(lines):
                            right.addstr(2 + i, panel_w - 5, "▼")
                else:
                    right.addstr(2, 2, lines[0])
            else:
                right.addstr(2, 2, "Directory")

        status = f"{self.active_panel.upper()} | {os.path.abspath(selected_path)} | {len(items)-1} items"
        self.stdscr.addstr(h - 1, 0, status[:w - 1], curses.color_pair(2))

        self.stdscr.refresh()
        left.refresh()
        right.refresh()

        return items, selected_path, panel_h


    def handle_open_menu(self, key) -> None:
        if key == curses.KEY_UP:
            self.open_index = max(0, self.open_index - 1)

        elif key == curses.KEY_DOWN:
            self.open_index = min(len(self.open_items) - 1, self.open_index + 1)

        elif key == 27:
            self.open_menu = False

        elif key == 10:
            _, cmd = self.open_items[self.open_index]
            cmd = cmd.replace("%1", self.open_path).replace("%L", self.open_path)

            subprocess.Popen(cmd, shell=True)
            self.open_menu = False

    def handle_navigation(self, key, items, selected_path, panel_h) -> tuple[bool, str]:
        if self.help_menu:

            if key in [ord("h"), 27]:
                self.help_menu = False

            return True, selected_path


        if self.delete_confirm:

            if key == curses.KEY_UP:
                self.delete_index = max(0, self.delete_index - 1)

            elif key == curses.KEY_DOWN:
                self.delete_index = min(1, self.delete_index + 1)

            elif key == 27:
                self.delete_confirm = False

            elif key == 10:

                if self.delete_index == 0:

                    if os.path.isdir(self.delete_path):
                        shutil.rmtree(self.delete_path)
                    else:
                        os.remove(self.delete_path)

                self.delete_confirm = False

            return True, selected_path
        if key == ord("q"):
            return False, selected_path
        
        elif key == ord("c"):
            self.copied_path = selected_path

        elif key == ord("v"):
            if self.copied_path and os.path.isfile(self.copied_path):

                filename = os.path.basename(self.copied_path)
                destination = os.path.join(self.current_dir, filename)

                base, ext = os.path.splitext(filename)
                counter = 1

                while os.path.exists(destination):
                    destination = os.path.join(
                        self.current_dir,
                        f"{base} - Copy{counter}{ext}"
                    )
                    counter += 1

                shutil.copy2(self.copied_path, destination)

        elif key == ord("x"):
            try:
                clipboard_path = pyperclip.paste()
                if clipboard_path:
                    clipboard_path = clipboard_path.strip().strip('"').strip("'")
                    if os.path.isdir(clipboard_path):
                        self.current_dir = os.path.abspath(clipboard_path)
                        self.selected = 0
                        self.offset = 0
                        self.right_offset = 0
                        self.right_selected = 0
            except Exception:
                pass

        elif key == ord("d"):
            if os.path.basename(selected_path) == ".." or selected_path == self.current_dir:
                return True, selected_path
            self.delete_confirm = True
            self.delete_path = selected_path
            self.delete_index = 0

        elif key == ord("h"):
            self.help_menu = True

        elif key == curses.KEY_LEFT:
            self.active_panel = "left"

        elif key == curses.KEY_RIGHT:
            self.active_panel = "right"

        elif key == curses.KEY_UP:
            if self.active_panel == "left":
                self.selected = max(0, self.selected - 1)
                if self.selected < self.offset:
                    self.offset -= 1
                self.right_offset = 0
                self.right_selected = 0
            else:
                self.right_selected = max(0, self.right_selected - 1)

                if self.right_selected < self.right_offset:
                    self.right_offset -= 1

        elif key == curses.KEY_DOWN:
            if self.active_panel == "left":
                self.selected = min(len(items) - 1, self.selected + 1)
                if self.selected >= self.offset + (panel_h - 4):
                    self.offset += 1
                self.right_offset = 0
                self.right_selected = 0
            else:
                if os.path.isfile(selected_path):
                    ok, lines = read_file(selected_path)

                    visible_h = panel_h - 4

                    self.right_selected = min(len(lines) - 1, self.right_selected + 1)

                    if self.right_selected >= self.right_offset + visible_h:
                        self.right_offset += 1

        elif key == 10:
            if os.path.isdir(selected_path):
                self.current_dir = selected_path
                self.selected = 0
                self.offset = 0
                self.right_offset = 0
                self.right_selected = 0
            else:
                self.open_items = get_open_with(selected_path)

                if not self.open_items:
                    launch_default(selected_path)
                else:
                    self.open_menu = True
                    self.open_index = 0
                    self.open_path = selected_path
                    self.right_offset = 0
                    self.right_selected = 0

        return True, selected_path


    def run(self) -> None:
        while True:
            items, selected_path, panel_h = self.render()
            key = self.stdscr.getch()

            if self.open_menu:
                self.handle_open_menu(key)
                continue

            cont, selected_path = self.handle_navigation(key, items, selected_path, panel_h)
            if not cont:
                break
