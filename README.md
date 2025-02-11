# HarmoBot Build Instructions

This is a quick how-to for building the HarmoBot project using PyInstaller.

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

## Windows

First build (no .spec):

```bash
pyinstaller --name HarmoBot --onefile --windowed --icon=assets\harmobot_logo.ico --add-data "assets;assets" main.py
```

Subsequent builds (when .spec is unchanged):

```bash
pyinstaller HarmoBot.spec
```

## Linux

First build (no .spec):

```bash
pyinstaller --name HarmoBot --onefile --windowed --icon=assets/harmobot_logo.ico --add-data "assets:assets" main.py
```

Subsequent builds (when .spec is unchanged):

```bash
pyinstaller HarmoBot.spec
```

## macOS

First build (no .spec):

```bash
pyinstaller --name HarmoBot --onefile --windowed --icon=assets/icon.icns --add-data "assets:assets" main.py
```

Subsequent builds (when .spec is unchanged):

```bash
pyinstaller HarmoBot.spec
```

---

<details>
<summary>Additional Info</summary>
If you haven't modified files that affect the GUI (such as icons, images, or other assets), you can simply rebuild using the existing spec file with:

```bash
  pyinstaller HarmoBot.spec
```

Ensure that your assets folder is structured as follows:

```bash
  assets/
    *.png
    *.gif
    harmobot_logo.ico (for Windows/Linux)
    harmobot_logo.icns (for macOS)
```

</details>
