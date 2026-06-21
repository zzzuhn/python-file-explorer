import os
import sys
import time
import subprocess
import winreg

def get_mtime(path):
    try:
        ts = os.path.getmtime(path)
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
    except:
        return "?"
    

def launch_default(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)

        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", path])

        else:
            subprocess.run(["xdg-open", path])

    except OSError as e:
        return False, str(e)

    except Exception as e:
        return False, str(e)

    return True, None


def get_open_with(path):
    ext = os.path.splitext(path)[1]

    programs = []

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            ext + r"\OpenWithProgids"
        )

        i = 0
        while True:
            try:
                prog = winreg.EnumValue(key, i)[0]
                programs.append(prog)
                i += 1
            except OSError:
                break
    except:
        pass

    apps = []

    for prog in programs:
        try:
            cmd_key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                prog + r"\shell\open\command"
            )
            cmd = winreg.QueryValue(cmd_key, None)
            apps.append((prog, cmd))
        except:
            continue

    return apps


def read_file(path):
    try:
        with open(path, "rb") as f:
            data = f.read(2048)

        if b"\x00" in data:
            return False, ["Binary file"]

        for enc in ("utf-8", "cp1250"):
            try:
                with open(path, "r", encoding=enc, errors="replace") as f:
                    return True, f.read().splitlines()
            except:
                pass

        return False, ["Unknown encoding"]

    except Exception as e:
        return False, [str(e)]


def get_size(path):
    try:
        if os.path.isdir(path):
            return "<DIR>"

        size = os.path.getsize(path)

        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size // 1024} KB"
        else:
            return f"{size // (1024 * 1024)} MB"
    except:
        return "?"
