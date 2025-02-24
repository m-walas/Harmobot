from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpacerItem, QSizePolicy, QButtonGroup
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QSize, QSettings
)
from PyQt6.QtGui import QIcon

from core.resources import resource_path, get_icon_path


class SidebarButton(QPushButton):
    """
    Sidebar button.
    - May be checkable.
    - The text is displayed next to the icon when expanded.
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
        """Toggle the original text (displayed next to the icon)."""
        self.setText(self._original_text if visible else "")


class CollapsibleSidebar(QFrame):
    """
    Collapsible sidebar (50 -> 200 px).
    The 'initial_mode' parameter determines whether only basic buttons (InitialSetup)
    or the full set (MainWindow) are displayed.
    """

    # Signals for MainWindow / InitialSetup
    sig_select_cabbage = pyqtSignal()
    sig_select_schej = pyqtSignal()
    sig_load_csv = pyqtSignal()
    sig_export_csv = pyqtSignal()
    sig_export_html = pyqtSignal()
    sig_export_png = pyqtSignal()
    sig_settings = pyqtSignal()
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

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Top widget
        top_widget = QFrame()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)

        menu_icon = QIcon(get_icon_path("menu"))
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

        # --- Tabs Cabbage / Schej ---
        engine_group = QButtonGroup(self)
        engine_group.setExclusive(True)

        cabbage_icon = QIcon(get_icon_path("cabbage"))
        self.btn_cabbage = SidebarButton(icon=cabbage_icon, text="cabbagemeet", checkable=True)
        self.btn_cabbage.setChecked(True)
        self.btn_cabbage.clicked.connect(self._on_cabbage_clicked)
        engine_group.addButton(self.btn_cabbage)
        self.main_layout.addWidget(self.btn_cabbage)

        schej_icon = QIcon(get_icon_path("schej"))
        self.btn_schej = SidebarButton(icon=schej_icon, text="schej", checkable=True)
        self.btn_schej.setChecked(False)
        self.btn_schej.clicked.connect(self._on_schej_clicked)
        engine_group.addButton(self.btn_schej)
        self.main_layout.addWidget(self.btn_schej)

        csv_icon = QIcon(get_icon_path("load_csv"))
        self.btn_load_csv = SidebarButton(icon=csv_icon, text="Wczytaj CSV", checkable=False)
        self.btn_load_csv.clicked.connect(lambda: self.sig_load_csv.emit())
        self.main_layout.addWidget(self.btn_load_csv)

        if not initial_mode:
            exp_csv_icon = QIcon(get_icon_path("export_csv"))
            self.btn_export_csv = SidebarButton(icon=exp_csv_icon, text="Eksport CSV", checkable=False)
            self.btn_export_csv.clicked.connect(lambda: self.sig_export_csv.emit())
            self.main_layout.addWidget(self.btn_export_csv)

            exp_html_icon = QIcon(get_icon_path("export_html"))
            self.btn_export_html = SidebarButton(icon=exp_html_icon, text="Eksport HTML", checkable=False)
            self.btn_export_html.clicked.connect(lambda: self.sig_export_html.emit())
            self.main_layout.addWidget(self.btn_export_html)

            exp_png_icon = QIcon(get_icon_path("export_png"))
            self.btn_export_png = SidebarButton(icon=exp_png_icon, text="Eksport PNG", checkable=False)
            self.btn_export_png.clicked.connect(lambda: self.sig_export_png.emit())
            self.main_layout.addWidget(self.btn_export_png)

        # spacer
        self.main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Additional buttons – only for main_window
        if not initial_mode:
            # color chips – checkable
            color_icon = QIcon(get_icon_path("colorize_chips"))
            self.btn_colorize = SidebarButton(icon=color_icon, text="Kolor czipów", checkable=True)
            self.btn_colorize.setChecked(False)
            self.btn_colorize.clicked.connect(lambda: self.sig_colorize.emit())
            self.main_layout.addWidget(self.btn_colorize)

            # Parameters – checkable
            params_icon = QIcon(get_icon_path("parameters"))
            self.btn_params = SidebarButton(icon=params_icon, text="Parametry", checkable=True)
            self.btn_params.setChecked(True)
            self.btn_params.clicked.connect(lambda: self.sig_toggle_params.emit())
            self.main_layout.addWidget(self.btn_params)

        # Separator
        sep_bottom = QFrame()
        sep_bottom.setFrameShape(QFrame.Shape.HLine)
        sep_bottom.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(sep_bottom)

        # settings
        settings_icon = QIcon(get_icon_path("settings"))
        self.btn_settings = SidebarButton(icon=settings_icon, text="Ustawienia", checkable=False)
        self.btn_settings.clicked.connect(lambda: self.sig_settings.emit())
        self.main_layout.addWidget(self.btn_settings)

        # Dokumentacja
        doc_icon = QIcon(get_icon_path("docs"))
        self.btn_doc = SidebarButton(icon=doc_icon, text="Dokumentacja", checkable=False)
        self.btn_doc.clicked.connect(lambda: self.sig_documentation.emit())
        self.main_layout.addWidget(self.btn_doc)

        # back to initial – only for main_window
        if not initial_mode:
            back_icon = QIcon(get_icon_path("back"))
            self.btn_go_initial = SidebarButton(icon=back_icon, text="Powrót", checkable=False)
            self.btn_go_initial.clicked.connect(lambda: self.sig_go_initial.emit())
            self.main_layout.addWidget(self.btn_go_initial)

    def _on_cabbage_clicked(self):
        if not self.btn_cabbage.isChecked():
            self.btn_cabbage.setChecked(True)
        self.btn_schej.setChecked(False)
        self.sig_select_cabbage.emit()

    def _on_schej_clicked(self):
        if not self.btn_schej.isChecked():
            self.btn_schej.setChecked(True)
        self.btn_cabbage.setChecked(False)
        self.sig_select_schej.emit()

    def toggle_sidebar(self):
        """
        Toggles the sidebar between collapsed and expanded states.
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
            "btn_cabbage", "btn_schej", "btn_load_csv",
            "btn_export_csv", "btn_export_html", "btn_export_png",
            "btn_settings", "btn_colorize", "btn_params",
            "btn_doc", "btn_go_initial"
        ]:
            btn = getattr(self, attr_name, None)
            if btn is not None:
                btn.show_text(self._expanded)

    def _on_animation_finished(self):
        final_w = self._expanded_width if self._expanded else self._collapsed_width
        self.setFixedWidth(final_w)

    def disable_api_tabs(self, disabled: bool):
        if hasattr(self, "btn_cabbage"):
            self.btn_cabbage.setEnabled(not disabled)
        if hasattr(self, "btn_schej"):
            self.btn_schej.setEnabled(not disabled)

    def update_icons(self, initial_mode=False):
        """
        Update the icons based on the current theme.
        """
        settings = QSettings("Harmobot", "Harmobot")
        current_theme = settings.value("theme", "Light").lower()
        if current_theme in ["light"]:
            if not initial_mode:
                self.btn_export_csv.setIcon(QIcon(get_icon_path("export_csv", variant="light")))
                self.btn_export_html.setIcon(QIcon(get_icon_path("export_html", variant="light")))
                self.btn_export_png.setIcon(QIcon(get_icon_path("export_png", variant="light")))
                self.btn_colorize.setIcon(QIcon(get_icon_path("colorize_chips", variant="light")))
                self.btn_params.setIcon(QIcon(get_icon_path("parameters", variant="light")))
                self.btn_go_initial.setIcon(QIcon(get_icon_path("back", variant="light")))
            self.toggle_btn.setIcon(QIcon(get_icon_path("menu", variant="light")))
            self.btn_cabbage.setIcon(QIcon(get_icon_path("cabbage", variant="light")))
            self.btn_schej.setIcon(QIcon(get_icon_path("schej", variant="light")))
            self.btn_load_csv.setIcon(QIcon(get_icon_path("load_csv", variant="light")))
            self.btn_settings.setIcon(QIcon(get_icon_path("settings", variant="light")))
            self.btn_doc.setIcon(QIcon(get_icon_path("docs", variant="light")))
        elif current_theme in ["high contrast"]:
            if not initial_mode:
                self.btn_export_csv.setIcon(QIcon(get_icon_path("export_csv", variant="dark")))
                self.btn_export_html.setIcon(QIcon(get_icon_path("export_html", variant="dark")))
                self.btn_export_png.setIcon(QIcon(get_icon_path("export_png", variant="dark")))
                self.btn_colorize.setIcon(QIcon(get_icon_path("colorize_chips", variant="dark")))
                self.btn_params.setIcon(QIcon(get_icon_path("parameters", variant="dark")))
                self.btn_go_initial.setIcon(QIcon(get_icon_path("back", variant="dark")))
            self.toggle_btn.setIcon(QIcon(get_icon_path("menu", variant="dark")))
            self.btn_cabbage.setIcon(QIcon(get_icon_path("cabbage", variant="dark")))
            self.btn_schej.setIcon(QIcon(get_icon_path("schej", variant="dark")))
            self.btn_load_csv.setIcon(QIcon(get_icon_path("load_csv", variant="dark")))
            self.btn_settings.setIcon(QIcon(get_icon_path("settings", variant="dark")))
            self.btn_doc.setIcon(QIcon(get_icon_path("docs", variant="dark")))
        else:
            if not initial_mode:
                self.btn_export_csv.setIcon(QIcon(get_icon_path("export_csv")))
                self.btn_export_html.setIcon(QIcon(get_icon_path("export_html")))
                self.btn_export_png.setIcon(QIcon(get_icon_path("export_png")))
                self.btn_colorize.setIcon(QIcon(get_icon_path("colorize_chips")))
                self.btn_params.setIcon(QIcon(get_icon_path("parameters")))
                self.btn_go_initial.setIcon(QIcon(get_icon_path("back")))
            self.toggle_btn.setIcon(QIcon(get_icon_path("menu")))
            self.btn_cabbage.setIcon(QIcon(get_icon_path("cabbage")))
            self.btn_schej.setIcon(QIcon(get_icon_path("schej")))
            self.btn_load_csv.setIcon(QIcon(get_icon_path("load_csv")))
            self.btn_settings.setIcon(QIcon(get_icon_path("settings")))
            self.btn_doc.setIcon(QIcon(get_icon_path("docs")))
