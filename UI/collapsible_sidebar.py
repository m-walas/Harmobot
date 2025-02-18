from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpacerItem, QSizePolicy, QButtonGroup
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QSize
)
from PyQt6.QtGui import QIcon

from core.resources import resource_path

class SidebarButton(QPushButton):
    """
    Przycisk w sidebar.
    - Może być checkable
    - Tekst pojawia się po rozwinięciu sidebar
    """
    def __init__(self, icon=None, text="", parent=None, checkable=False):
        super().__init__(parent)
        self._original_text = text
        self.setObjectName("SidebarButton")
        self.setCheckable(checkable)
        self.setMinimumHeight(30)

        if icon is not None:
            self.setIcon(icon)
            self.setIconSize(QSize(26, 26))

        self.show_text(False)

    def show_text(self, visible: bool):
        """Włącza/wyłącza oryginalny tekst (obok ikony)."""
        self.setText(self._original_text if visible else "")


class CollapsibleSidebar(QFrame):
    """
    Rozwijany sidebar (50 -> 200 px).

    Parametr 'initial_mode' decyduje, czy mamy tylko
    podstawowe przyciski (InitialSetup) czy pełen zestaw (MainWindow).
    """

    # Sygnały do MainWindow / Initial
    sig_select_lettuce = pyqtSignal()
    sig_select_schej = pyqtSignal()
    sig_load_csv = pyqtSignal()
    sig_export_csv = pyqtSignal()
    sig_export_html = pyqtSignal()
    sig_export_png = pyqtSignal()
    sig_fire_mode = pyqtSignal()
    sig_colorize = pyqtSignal()
    sig_toggle_params = pyqtSignal()
    sig_documentation = pyqtSignal()
    sig_go_initial = pyqtSignal()

    def __init__(self, parent=None, initial_mode=False):
        super().__init__(parent)
        self.setObjectName("CollapsibleSidebar")

        self._collapsed_width = 50
        self._expanded_width = 200
        self._expanded = False

        self.lettuce_icon_light = resource_path("assets/icons/light/lettuce_light.png")
        self.lettuce_icon_dark  = resource_path("assets/icons/dark/lettuce_dark.png")
        self.schej_icon_light   = resource_path("assets/icons/light/schej_light.png")
        self.schej_icon_dark    = resource_path("assets/icons/dark/schej_dark.png")

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Pasek górny (toggle + label) ---
        top_widget = QFrame()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)

        menu_icon = QIcon(resource_path("assets/icons/light/menu_light.png"))
        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("SidebarToggleBtn")
        self.toggle_btn.setIcon(menu_icon)
        self.toggle_btn.setIconSize(QSize(24, 24))
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        top_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.app_label = QLabel("Harmobot")
        self.app_label.setObjectName("SidebarAppLabel")
        self.app_label.setVisible(False)
        top_layout.addWidget(self.app_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(top_widget)

        # Separator
        sep_top = QFrame()
        sep_top.setFrameShape(QFrame.Shape.HLine)
        sep_top.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(sep_top)

        # --- Taby Lettuce / Schej ---
        engine_group = QButtonGroup(self)
        engine_group.setExclusive(True)

        # Lettuce
        self.btn_lettuce = SidebarButton(
            icon=QIcon(self.lettuce_icon_light),
            text="lettucemeet",
            checkable=True
        )
        self.btn_lettuce.setChecked(True)
        self.btn_lettuce.clicked.connect(self._on_lettuce_clicked)
        engine_group.addButton(self.btn_lettuce)
        self.main_layout.addWidget(self.btn_lettuce)

        # Schej
        self.btn_schej = SidebarButton(
            icon=QIcon(self.schej_icon_light),
            text="schej",
            checkable=True
        )
        self.btn_schej.setChecked(False)
        self.btn_schej.clicked.connect(self._on_schej_clicked)
        engine_group.addButton(self.btn_schej)
        self.main_layout.addWidget(self.btn_schej)

        # Wczytaj CSV
        csv_icon = QIcon(resource_path("assets/icons/light/load_csv_light.png"))
        self.btn_load_csv = SidebarButton(icon=csv_icon, text="Wczytaj CSV", checkable=False)
        self.btn_load_csv.clicked.connect(lambda: self.sig_load_csv.emit())
        self.main_layout.addWidget(self.btn_load_csv)

        # Jeśli main_window => eksporty
        if not initial_mode:
            exp_csv_icon = QIcon(resource_path("assets/icons/light/export_csv_light.png"))
            self.btn_export_csv = SidebarButton(icon=exp_csv_icon, text="Eksport CSV", checkable=False)
            self.btn_export_csv.clicked.connect(lambda: self.sig_export_csv.emit())
            self.main_layout.addWidget(self.btn_export_csv)

            exp_html_icon = QIcon(resource_path("assets/icons/light/export_html_light.png"))
            self.btn_export_html = SidebarButton(icon=exp_html_icon, text="Eksport HTML", checkable=False)
            self.btn_export_html.clicked.connect(lambda: self.sig_export_html.emit())
            self.main_layout.addWidget(self.btn_export_html)

            exp_png_icon = QIcon(resource_path("assets/icons/light/export_png_light.png"))
            self.btn_export_png = SidebarButton(icon=exp_png_icon, text="Eksport PNG", checkable=False)
            self.btn_export_png.clicked.connect(lambda: self.sig_export_png.emit())
            self.main_layout.addWidget(self.btn_export_png)

        # spacer
        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # FireMode
        fire_icon = QIcon(resource_path("assets/icons/light/theme_toggle_light.png"))
        self.btn_fire_mode = SidebarButton(icon=fire_icon, text="FireMode", checkable=False)
        self.btn_fire_mode.clicked.connect(lambda: self.sig_fire_mode.emit())
        self.main_layout.addWidget(self.btn_fire_mode)

        # Kolor czipów – checkable
        if not initial_mode:
            color_icon = QIcon(resource_path("assets/icons/light/colorize_chips_light.png"))
            self.btn_colorize = SidebarButton(icon=color_icon, text="Kolor czipów", checkable=True)
            self.btn_colorize.setChecked(False)
            self.btn_colorize.clicked.connect(lambda: self.sig_colorize.emit())
            self.main_layout.addWidget(self.btn_colorize)

        # Parametry – checkable
        if not initial_mode:
            params_icon = QIcon(resource_path("assets/icons/light/parameters_light.png"))
            self.btn_params = SidebarButton(icon=params_icon, text="Parametry", checkable=True)
            self.btn_params.setChecked(True)
            self.btn_params.clicked.connect(lambda: self.sig_toggle_params.emit())
            self.main_layout.addWidget(self.btn_params)

        # Separator
        sep_bottom = QFrame()
        sep_bottom.setFrameShape(QFrame.Shape.HLine)
        sep_bottom.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(sep_bottom)

        # Dokumentacja
        doc_icon = QIcon(resource_path("assets/icons/light/docs_light.png"))
        self.btn_doc = SidebarButton(icon=doc_icon, text="Dokumentacja", checkable=False)
        self.btn_doc.clicked.connect(lambda: self.sig_documentation.emit())
        self.main_layout.addWidget(self.btn_doc)

        # Powrót do initial – only main
        if not initial_mode:
            back_icon = QIcon(resource_path("assets/icons/light/back_light.png"))
            self.btn_go_initial = SidebarButton(icon=back_icon, text="Powrót", checkable=False)
            self.btn_go_initial.clicked.connect(lambda: self.sig_go_initial.emit())
            self.main_layout.addWidget(self.btn_go_initial)

    def _on_lettuce_clicked(self):
        """Zaznacz Lettuce, odznacz Schej, emit sig_select_lettuce."""
        if not self.btn_lettuce.isChecked():
            self.btn_lettuce.setChecked(True)
        self.btn_schej.setChecked(False)
        self.sig_select_lettuce.emit()

    def _on_schej_clicked(self):
        """Zaznacz Schej, odznacz Lettuce, emit sig_select_schej."""
        if not self.btn_schej.isChecked():
            self.btn_schej.setChecked(True)
        self.btn_lettuce.setChecked(False)
        self.sig_select_schej.emit()

    def toggle_sidebar(self):
        """
        Główna metoda rozwijania/zwijania sidebar.
        """
        end_width = self._expanded_width if not self._expanded else self._collapsed_width
        self._expanded = not self._expanded

        self._anim_min = QPropertyAnimation(self, b"minimumWidth")
        self._anim_min.setDuration(250)
        self._anim_min.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim_min.setStartValue(self.width())
        self._anim_min.setEndValue(end_width)

        self._anim_max = QPropertyAnimation(self, b"maximumWidth")
        self._anim_max.setDuration(250)
        self._anim_max.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim_max.setStartValue(self.width())
        self._anim_max.setEndValue(end_width)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self._anim_min)
        self._anim_group.addAnimation(self._anim_max)
        self._anim_group.finished.connect(self._on_animation_finished)
        self._anim_group.start()

        self.app_label.setVisible(self._expanded)
        for attr_name in [
            "btn_lettuce", "btn_schej", "btn_load_csv",
            "btn_export_csv", "btn_export_html", "btn_export_png",
            "btn_fire_mode", "btn_colorize", "btn_params",
            "btn_doc", "btn_go_initial"
        ]:
            btn = getattr(self, attr_name, None)
            if btn is not None:
                btn.show_text(self._expanded)

    def _on_animation_finished(self):
        final_w = self._expanded_width if self._expanded else self._collapsed_width
        self.setFixedWidth(final_w)

    def disable_api_tabs(self, disabled: bool):
        if hasattr(self, "btn_lettuce"):
            self.btn_lettuce.setEnabled(not disabled)
        if hasattr(self, "btn_schej"):
            self.btn_schej.setEnabled(not disabled)

    def set_dark_mode_icon(self, dark: bool):
        if dark:
            self.btn_lettuce.setIcon(QIcon(self.lettuce_icon_dark))
            self.btn_schej.setIcon(QIcon(self.schej_icon_dark))
        else:
            self.btn_lettuce.setIcon(QIcon(self.lettuce_icon_light))
            self.btn_schej.setIcon(QIcon(self.schej_icon_light))
