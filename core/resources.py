import sys
import os

from PyQt6.QtCore import QSettings

def resource_path(relative_path):
    """
    Returns the absolute path to a resource.
    This ensures that the file is correctly located both during development
    and after packaging (with PyInstaller).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_icon_path(icon_name: str, variant: str = None) -> str:
        """
        Return the path to the icon based on the current theme and variant for the specified icon name.
        """
        settings = QSettings("Harmobot", "Harmobot")
        theme = settings.value("theme", "Light").lower()
        if variant:
            folder = variant
        else:
            folder = "light" if theme in ["dark", "dracula", "ocean dark", "firemode", "high contrast"] else "dark"
        return resource_path(f"assets/icons/{folder}/{icon_name}.png")


def get_logo_path() -> str:
    """
    Return the path to the logo based on the current theme.
    """
    settings = QSettings("Harmobot", "Harmobot")
    theme = settings.value("theme", "Light").lower()
    if theme in ["dark", "dracula", "ocean dark", "high contrast"]:
        return resource_path("assets/harmobot_logo_light.png")
    else:
        return resource_path("assets/harmobot_logo_dark.png")
