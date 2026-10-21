"""
RetroFormat Styling System
High-density compact pixel-art styling with clear Segoe UI typography.
Supports both Dark Mode (Gece Modu) and Light Mode (Gündüz Modu) with 
meticulously tuned contrast and readability across all screens, cards, and dialogs.
"""

from utils import resource_path

# =============================================================================
# THEME PALETTES & ACCENT METADATA
# =============================================================================

THEME_CONFIG = {
    "dark": {
        "primary_accent": "#00F0FF",
        "secondary_accent": "#00FF66",
        "warning_accent": "#FFAA00",
        "error_accent": "#FF4757",
        "text_primary": "#FFFFFF",
        "text_secondary": "#BAC7D5",
        "text_muted": "#8C99AA",
        "meta_color": "#79869C",
        "card_bg": "#111220",
        "card_checked_bg": "#0B1C17",
    },
    "light": {
        "primary_accent": "#0284C7",
        "secondary_accent": "#15803D",
        "warning_accent": "#B45309",
        "error_accent": "#B91C1C",
        "text_primary": "#0F172A",
        "text_secondary": "#334155",
        "text_muted": "#475569",
        "meta_color": "#64748B",
        "card_bg": "#FFFFFF",
        "card_checked_bg": "#F0FDF4",
    }
}


# =============================================================================
# DARK MODE (GECE MODU)
# =============================================================================

DARK_STYLE = """
/* =========================================================================
   GLOBAL RESET & BASICS - DARK MODE
   ========================================================================= */
QMainWindow, QDialog {
    background-color: #0A0B10;
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, 'Roboto', sans-serif;
    font-size: 13px;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, 'Roboto', sans-serif;
    outline: none;
    color: #E2E8F0;
}

/* =========================================================================
   HEADER
   ========================================================================= */
#headerContainer {
    background-color: #11121E;
    border-bottom: 2px solid #1C1F33;
    padding: 10px 18px;
}

#appLogo {
    border: 2px solid #00F0FF;
    background-color: #06070B;
}

#titleLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: #00F0FF;
    letter-spacing: 0.5px;
}

#subtitleLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #8C99AA;
}

#adminBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
    border: 1px solid rgba(255, 69, 58, 0.45);
    background-color: rgba(255, 69, 58, 0.12);
    color: #FF453A;
    border-radius: 14px;
}
#adminBadge:hover {
    background-color: rgba(255, 69, 58, 0.22);
    color: #FF6961;
}

#adminBadgeElevated {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
    border: 1px solid rgba(52, 199, 89, 0.45);
    background-color: rgba(52, 199, 89, 0.12);
    color: #34C759;
    border-radius: 14px;
}

#profileSwitcherBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: rgba(14, 165, 233, 0.12);
    color: #38BDF8;
    border: 1px solid rgba(14, 165, 233, 0.4);
    border-radius: 14px;
    padding: 6px 16px;
}
#profileSwitcherBtn:hover {
    background-color: rgba(14, 165, 233, 0.22);
    color: #7DD3FC;
    border-color: #7DD3FC;
}

#profileBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: rgba(255, 255, 255, 0.06);
    color: #E2E8F0;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 6px 16px;
}
#profileBtn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
    border-color: rgba(255, 255, 255, 0.25);
}

#themeToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: rgba(245, 158, 11, 0.12);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 14px;
    padding: 6px 16px;
}
#themeToggleBtn:hover {
    background-color: rgba(245, 158, 11, 0.22);
    color: #FDE68A;
    border-color: #FCD34D;
}

/* =========================================================================
   LEFT SIDEBAR NAVIGATION
   ========================================================================= */
#sidebarPanel {
    background-color: #0D0E18;
    border-right: 1px solid #1C2036;
}

#navTree {
    background-color: #0D0E18;
    border: none;
    color: #BAC7D5;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    outline: none;
}
#navTree::item {
    padding: 6px 4px;
    border-radius: 6px;
    color: #8C99AA;
}
#navTree::item:hover {
    background-color: #181A2C;
    color: #D0D8E8;
}
#navTree::item:selected {
    background-color: #102030;
    color: #00F0FF;
    border-left: 2px solid #00F0FF;
}
#navTree::branch {
    background-color: transparent;
}
#navTree::branch:has-siblings:!adjoins-item {
    border-image: none;
}
#navTree::branch:open:has-children {
    border-image: none;
}

#sidebarToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #556270;
    background-color: #0D0E18;
    border: none;
    border-top: 1px solid #1C2036;
    padding: 8px 12px;
    text-align: left;
}
#sidebarToggleBtn:hover {
    color: #8C99AA;
    background-color: #131525;
}

QSplitter#mainSplitter::handle {
    background-color: #1C2036;
    width: 1px;
}

/* =========================================================================
   PORTABLE BADGE
   ========================================================================= */
.pkgPortableBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    background-color: #1A2040;
    color: #6BAED6;
    border: 1px solid #2D4060;
    border-radius: 8px;
    max-height: 18px;
    min-height: 16px;
}

/* =========================================================================
   TOP EXPLANATION PANEL (ITEM INTEL)
   ========================================================================= */
#inspectPanel {
    background-color: #111322;
    border: 1px solid #1E2338;
    border-radius: 12px;
    padding: 10px 18px;
}

#inspectBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: bold;
    color: #00F0FF;
    background-color: #071E28;
    border: 1px solid #00F0FF;
    border-radius: 8px;
    padding: 2px 8px;
}

#inspectTitle {
    font-family: 'Segoe UI', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
}

#inspectCatLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    font-weight: bold;
    color: #00F0FF;
}

#inspectDesc {
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #BAC7D5;
    line-height: 1.4;
}

#inspectMeta, #inspectSourceLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    color: #79869C;
}

#inspectHintLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    font-weight: bold;
    color: #00F0FF;
    background-color: #071E28;
    border: 1px solid #00F0FF55;
    padding: 3px 8px;
}

.inspectCatSuccess {
    color: #00FF66 !important;
}
.inspectBadgeSuccess {
    color: #00FF66 !important;
    background-color: #032410 !important;
    border: 1px solid #00FF66 !important;
}
.inspectHintSuccess {
    color: #00FF66 !important;
    background-color: #032410 !important;
    border: 1px solid #00FF66 !important;
}

/* =========================================================================
   PRESET & CATEGORY BARS
   ========================================================================= */
#presetBar {
    background-color: #0D0E17;
    border-bottom: 2px solid #181A2B;
    padding: 6px 18px;
}

#categoryBar {
    background-color: #0A0B12;
    border-bottom: 2px solid #161828;
    padding: 6px 16px;
}

.barSectionLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #8C99AA;
    margin-right: 2px;
}

.presetBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    font-weight: 600;
    color: #D2DCF0;
    background-color: #16182B;
    border: 1.5px solid #282C48;
    border-radius: 8px;
    padding: 4px 10px;
}
.presetBtn:hover {
    background-color: #222540;
    color: #00F0FF;
    border-color: #00F0FF;
}
.presetBtn[selected="true"] {
    background-color: #0C2838;
    color: #00F0FF;
    border: 1.5px solid #00F0FF;
}
.presetBtn[selected="true"]:hover {
    background-color: #12374E;
    color: #80F7FF;
    border-color: #80F7FF;
}

#clearBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    font-weight: 600;
    color: #FF5E72;
    background-color: #240513;
    border: 1.5px solid #FF2E75;
    border-radius: 8px;
    padding: 4px 10px;
}
#clearBtn:hover {
    background-color: #38081E;
    color: #FF8091;
    border-color: #FF5E95;
}

.categoryTab {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #8C99AA;
    background-color: #121422;
    border: 1.5px solid #20243C;
    border-radius: 8px;
    padding: 4px 8px;
}
.categoryTab:hover {
    color: #FFFFFF;
    border-color: #00F0FF;
}
.categoryTab[selected="true"] {
    background-color: #161B33;
    color: #00F0FF;
    border: 1.5px solid #00F0FF;
}

/* =========================================================================
   SEARCH INPUT
   ========================================================================= */
#searchBox {
    background-color: #10121F;
    color: #00F0FF;
    border: 1.5px solid #232845;
    border-radius: 8px;
    padding: 6px 12px;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
}
#searchBox:focus {
    border: 1.5px solid #00F0FF;
}

/* =========================================================================
   SCROLL AREA & 2-COLUMN CARDS
   ========================================================================= */
QScrollArea {
    background-color: #0A0B10;
    border: none;
}

#scrollContent {
    background-color: #0A0B10;
}

.pkgCard {
    background-color: #131522;
    border: 1.5px solid #23273D;
    border-radius: 12px;
    padding: 8px 12px;
    min-height: 52px;
}
.pkgCard:hover {
    background-color: #191C2E;
    border-color: #383E64;
}
.pkgCard[checked="true"] {
    background-color: #0B2217;
    border: 1.5px solid #34C759;
}

.pkgDesc {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    color: #8C99AA;
    line-height: 1.3;
}

.pkgTag {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #1B1E33;
    color: #A0ABC0;
    border: 1px solid #2D3357;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgInstalledBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #062817;
    color: #34C759;
    border: 1px solid #34C759;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

/* Dynamic Badge Classes */
.pkgStatusSuccess {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #062817;
    color: #34C759;
    border: 1px solid #34C759;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusInstalling {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #0A2540;
    color: #0A84FF;
    border: 1px solid #0A84FF;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusWarning {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #322006;
    color: #FF9F0A;
    border: 1px solid #FF9F0A;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusError {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #380C14;
    color: #FF453A;
    border: 1px solid #FF453A;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

/* =========================================================================
   CHECKBOXES (APPLE TOGGLE SWITCH STYLE)
   ========================================================================= */
QCheckBox {
    spacing: 10px;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #FFFFFF;
}

QCheckBox::indicator {
    width: 38px;
    height: 22px;
    min-width: 38px;
    min-height: 22px;
    max-width: 38px;
    max-height: 22px;
    background-color: transparent;
    border: none;
}

QCheckBox::indicator:hover {
    opacity: 0.9;
}

QCheckBox::indicator:checked {
    image: url("assets/apple_switch_on_dark.png");
    border: none;
    background-color: transparent;
}

QCheckBox::indicator:unchecked {
    image: url("assets/apple_switch_off_dark.png");
    border: none;
    background-color: transparent;
}

/* =========================================================================
   BOTTOM ACTION BAR
   ========================================================================= */
#actionBar {
    background-color: #10121F;
    border-top: 1px solid #1F2238;
    padding: 10px 18px;
}

#selectedCountLabel {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13.5px;
    font-weight: 700;
    color: #34C759;
}

#installBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13.5px;
    font-weight: 700;
    color: #000000;
    background-color: #34C759;
    border-radius: 12px;
    border: none;
    padding: 9px 24px;
}
#installBtn:hover {
    background-color: #30D158;
}
#installBtn:pressed {
    background-color: #28B046;
}
#installBtn:disabled {
    background-color: #222634;
    color: #556270;
    border: none;
}

#downloadSetupsBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #38BDF8;
    background-color: #102438;
    border: 1.5px solid #0284C7;
    border-radius: 12px;
    padding: 8px 18px;
}
#downloadSetupsBtn:hover {
    background-color: #183350;
    color: #FFFFFF;
    border-color: #38BDF8;
}
#downloadSetupsBtn:pressed {
    background-color: #0C1E30;
}
#downloadSetupsBtn:disabled {
    background-color: #151824;
    color: #4C5568;
    border: 1px solid #1E2333;
}

#revertTweaksBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #FF453A;
    background-color: rgba(255, 69, 58, 0.12);
    border: 1.5px solid rgba(255, 69, 58, 0.4);
    border-radius: 12px;
    padding: 8px 18px;
}
#revertTweaksBtn:hover {
    background-color: rgba(255, 69, 58, 0.22);
    color: #FF6961;
}

#cancelBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #FFFFFF;
    background-color: #FF453A;
    border-radius: 12px;
    border: none;
    padding: 8px 18px;
}
#cancelBtn:hover {
    background-color: #FF6961;
}

#terminalToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #BAC7D5;
    background-color: #181B2B;
    border: 1px solid #2B314B;
    border-radius: 12px;
    padding: 7px 16px;
}
#terminalToggleBtn:hover {
    background-color: #232840;
    color: #FFFFFF;
    border-color: #3B4366;
}

/* =========================================================================
   PROGRESS BAR
   ========================================================================= */
QProgressBar {
    border: 2px solid #262B47;
    background-color: #0A0B10;
    text-align: center;
    color: #FFFFFF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #00FF66;
}

/* =========================================================================
   RETRO TERMINAL / CONSOLE
   ========================================================================= */
#terminalConsole {
    background-color: #05060A;
    color: #33FF33;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border-top: 2px solid #00FF66;
    padding: 8px;
}

/* =========================================================================
   SCROLLBAR
   ========================================================================= */
QScrollBar:vertical {
    background-color: #0A0B10;
    width: 12px;
    margin: 0px;
    border-left: 2px solid #181A2B;
}
QScrollBar::handle:vertical {
    background-color: #242742;
    min-height: 20px;
    border: 1px solid #35395E;
}
QScrollBar::handle:vertical:hover {
    background-color: #00F0FF;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* =========================================================================
   TOOLTIPS
   ========================================================================= */
QToolTip {
    background-color: #101221;
    color: #E2E8F0;
    border: 2px solid #00F0FF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    padding: 6px 10px;
}

/* =========================================================================
   MENUS
   ========================================================================= */
QMenu {
    background-color: #0E101B;
    border: 2px solid #00F0FF;
    padding: 6px;
    color: #FFFFFF;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QMenu::item {
    padding: 7px 24px 7px 12px;
    background-color: transparent;
    color: #E2E8F0;
}
QMenu::item:disabled {
    color: #00F0FF;
    font-weight: bold;
}
QMenu::item:selected {
    background-color: #17263C;
    color: #00F0FF;
}
QMenu::separator {
    height: 1px;
    background-color: #232845;
    margin: 5px 8px;
}

/* =========================================================================
   DIALOGS & PROFILE MODALS
   ========================================================================= */
#dialogTitle {
    font-size: 15px;
    font-weight: bold;
    color: #00F0FF;
}
#dialogInfoBox {
    background-color: #0E1325;
    border: 1px solid #1C2444;
    padding: 8px 12px;
}
#dialogInfoTitle {
    color: #00FF66;
    font-weight: bold;
    font-size: 11.5px;
}
#dialogInfoSub {
    color: #8C99AA;
    font-size: 11px;
}
#dialogFieldLabel {
    font-weight: 600;
    color: #FFFFFF;
    font-size: 12px;
}
#dialogInput {
    background-color: #090B14;
    color: #FFFFFF;
    border: 1px solid #00F0FF;
    padding: 7px 10px;
    font-size: 13px;
}
.dialogAvatarBtn {
    background-color: #121526;
    border: 1px solid #232845;
    font-size: 14px;
}
.dialogAvatarBtn:checked {
    background-color: #072230;
    border: 2px solid #00F0FF;
}
.dialogAvatarBtn:hover {
    background-color: #1A1F38;
}
#dialogPrimaryBtn {
    background-color: #00F0FF;
    color: #000000;
    font-weight: bold;
    padding: 8px 18px;
    border: none;
    font-size: 12px;
}
#dialogPrimaryBtn:hover {
    background-color: #38F8FF;
}
#dialogSecondaryBtn {
    background-color: #181A2C;
    color: #BAC7D5;
    padding: 8px 16px;
    border: 1px solid #33385C;
    font-size: 12px;
}
#dialogSecondaryBtn:hover {
    background-color: #23263E;
    color: #FFFFFF;
}

QMessageBox {
    background-color: #0A0B10;
    color: #E2E8F0;
}
QMessageBox QPushButton {
    background-color: #16182B;
    color: #00F0FF;
    border: 1px solid #00F0FF;
    padding: 6px 16px;
    font-weight: bold;
}
QMessageBox QPushButton:hover {
    background-color: #0C2838;
}
"""


# =============================================================================
# LIGHT MODE (GÜNDÜZ MODU)
# =============================================================================

LIGHT_STYLE = """
/* =========================================================================
   GLOBAL RESET & BASICS - LIGHT MODE
   ========================================================================= */
QMainWindow, QDialog {
    background-color: #F4F6FB;
    color: #0F172A;
    font-family: 'Segoe UI', -apple-system, 'Roboto', sans-serif;
    font-size: 13px;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, 'Roboto', sans-serif;
    outline: none;
    color: #0F172A;
}

/* =========================================================================
   HEADER
   ========================================================================= */
#headerContainer {
    background-color: #FFFFFF;
    border-bottom: 2px solid #CBD5E1;
    padding: 10px 18px;
}

#appLogo {
    border: 2px solid #0284C7;
    background-color: #F0F9FF;
}

#titleLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: #0369A1;
    letter-spacing: 0.5px;
}

#subtitleLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #475569;
}

#adminBadge {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
    border: 2px solid #DC2626;
    background-color: #FEE2E2;
    color: #991B1B;
}
#adminBadge:hover {
    background-color: #FECACA;
    color: #7F1D1D;
}

#adminBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
    border: 1px solid rgba(220, 38, 38, 0.35);
    background-color: #FEF2F2;
    color: #DC2626;
    border-radius: 14px;
}
#adminBadge:hover {
    background-color: #FEE2E2;
}

#adminBadgeElevated {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
    border: 1px solid rgba(22, 163, 74, 0.35);
    background-color: #F0FDF4;
    color: #16A34A;
    border-radius: 14px;
}

#profileSwitcherBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: #F0F9FF;
    color: #0284C7;
    border: 1px solid rgba(2, 132, 199, 0.35);
    border-radius: 14px;
    padding: 6px 16px;
}
#profileSwitcherBtn:hover {
    background-color: #E0F2FE;
    color: #0369A1;
}

#profileBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: #F8FAFC;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 14px;
    padding: 6px 16px;
}
#profileBtn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

#themeToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    background-color: #FFFBEB;
    color: #B45309;
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 14px;
    padding: 6px 16px;
}
#themeToggleBtn:hover {
    background-color: #FEF3C7;
}

/* =========================================================================
   LEFT SIDEBAR NAVIGATION (LIGHT)
   ========================================================================= */
#sidebarPanel {
    background-color: #F8FAFC;
    border-right: 1px solid #E2E8F0;
}

#navTree {
    background-color: #F8FAFC;
    border: none;
    color: #334155;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    outline: none;
}
#navTree::item {
    padding: 6px 4px;
    border-radius: 6px;
    color: #475569;
}
#navTree::item:hover {
    background-color: #E8F0F8;
    color: #0F172A;
}
#navTree::item:selected {
    background-color: #EFF6FF;
    color: #0284C7;
    border-left: 2px solid #0284C7;
}
#navTree::branch {
    background-color: transparent;
}

#sidebarToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    background-color: #F8FAFC;
    border: none;
    border-top: 1px solid #E2E8F0;
    padding: 8px 12px;
    text-align: left;
}
#sidebarToggleBtn:hover {
    color: #64748B;
    background-color: #F1F5F9;
}

QSplitter#mainSplitter::handle {
    background-color: #E2E8F0;
    width: 1px;
}

/* =========================================================================
   PORTABLE BADGE (LIGHT)
   ========================================================================= */
.pkgPortableBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    background-color: #EFF6FF;
    color: #3B82F6;
    border: 1px solid #BFDBFE;
    border-radius: 8px;
    max-height: 18px;
    min-height: 16px;
}

/* =========================================================================
   TOP EXPLANATION PANEL (ITEM INTEL)
   ========================================================================= */
#inspectPanel {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 10px 18px;
}

#inspectBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: bold;
    color: #0369A1;
    background-color: #E0F2FE;
    border: 1px solid #0284C7;
    border-radius: 8px;
    padding: 2px 8px;
}

#inspectTitle {
    font-family: 'Segoe UI', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #0F172A;
}

#inspectCatLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    font-weight: bold;
    color: #0284C7;
}

#inspectDesc {
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    color: #334155;
    line-height: 1.4;
}

#inspectMeta, #inspectSourceLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    color: #64748B;
}

#inspectHintLbl {
    font-family: 'Consolas', monospace;
    font-size: 11px;
    font-weight: bold;
    color: #0369A1;
    background-color: #E0F2FE;
    border: 1px solid #BAE6FD;
    padding: 3px 8px;
}

.inspectCatSuccess {
    color: #15803D !important;
}
.inspectBadgeSuccess {
    color: #15803D !important;
    background-color: #DCFCE7 !important;
    border: 1px solid #16A34A !important;
}
.inspectHintSuccess {
    color: #15803D !important;
    background-color: #DCFCE7 !important;
    border: 1px solid #16A34A !important;
}

/* =========================================================================
   PRESET & CATEGORY BARS
   ========================================================================= */
#presetBar {
    background-color: #F1F5F9;
    border-bottom: 2px solid #E2E8F0;
    padding: 6px 18px;
}

#categoryBar {
    background-color: #EAEFF6;
    border-bottom: 2px solid #CBD5E1;
    padding: 6px 16px;
}

.barSectionLabel {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    margin-right: 2px;
}

.presetBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    font-weight: 600;
    color: #1E293B;
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px 10px;
}
.presetBtn:hover {
    background-color: #F8FAFC;
    color: #0284C7;
    border-color: #0284C7;
}
.presetBtn[selected="true"] {
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1.5px solid #0284C7;
}
.presetBtn[selected="true"]:hover {
    background-color: #BAE6FD;
    color: #0284C7;
}

#clearBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    font-weight: 700;
    color: #991B1B;
    background-color: #FEE2E2;
    border: 1.5px solid #EF4444;
    border-radius: 8px;
    padding: 4px 10px;
}
#clearBtn:hover {
    background-color: #FECACA;
    color: #7F1D1D;
    border-color: #DC2626;
}

.categoryTab {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #475569;
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px 8px;
}
.categoryTab:hover {
    color: #0F172A;
    border-color: #0284C7;
}
.categoryTab[selected="true"] {
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1.5px solid #0284C7;
}

/* =========================================================================
   SEARCH INPUT
   ========================================================================= */
#searchBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
}
#searchBox:focus {
    border: 1.5px solid #0284C7;
}

/* =========================================================================
   SCROLL AREA & 2-COLUMN CARDS
   ========================================================================= */
QScrollArea {
    background-color: #F4F6FB;
    border: none;
}

#scrollContent {
    background-color: #F4F6FB;
}

.pkgCard {
    background-color: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 12px;
    padding: 8px 12px;
    min-height: 52px;
}
.pkgCard:hover {
    background-color: #F8FAFC;
    border-color: #CBD5E1;
}
.pkgCard[checked="true"] {
    background-color: #F0FDF4;
    border: 1.5px solid #34C759;
}

.pkgDesc {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 11.5px;
    color: #475569;
    line-height: 1.3;
}

.pkgTag {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgInstalledBadge {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #34C759;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

/* Dynamic Badge Classes */
.pkgStatusSuccess {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    background-color: #DCFCE7;
    color: #15803D;
    border: 1px solid #34C759;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusInstalling {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    background-color: #E0F2FE;
    color: #0369A1;
    border: 1px solid #0284C7;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusWarning {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    background-color: #FEF3C7;
    color: #B45309;
    border: 1px solid #F59E0B;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

.pkgStatusError {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #EF4444;
    border-radius: 10px;
    max-height: 20px;
    min-height: 18px;
}

/* =========================================================================
   CHECKBOXES (APPLE TOGGLE SWITCH STYLE)
   ========================================================================= */
QCheckBox {
    spacing: 10px;
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: #0F172A;
}

QCheckBox::indicator {
    width: 38px;
    height: 22px;
    min-width: 38px;
    min-height: 22px;
    max-width: 38px;
    max-height: 22px;
    background-color: transparent;
    border: none;
}

QCheckBox::indicator:hover {
    opacity: 0.9;
}

QCheckBox::indicator:checked {
    image: url("assets/apple_switch_on_light.png");
    border: none;
    background-color: transparent;
}

QCheckBox::indicator:unchecked {
    image: url("assets/apple_switch_off_light.png");
    border: none;
    background-color: transparent;
}

/* =========================================================================
   BOTTOM ACTION BAR
   ========================================================================= */
#actionBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    padding: 10px 18px;
}

#selectedCountLabel {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13.5px;
    font-weight: 700;
    color: #16A34A;
}

#installBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 13.5px;
    font-weight: 700;
    color: #FFFFFF;
    background-color: #16A34A;
    border-radius: 12px;
    border: none;
    padding: 9px 24px;
}
#installBtn:hover {
    background-color: #15803D;
}
#installBtn:pressed {
    background-color: #166534;
}
#installBtn:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border: 1px solid #E2E8F0;
}

#downloadSetupsBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #0284C7;
    background-color: #F0F9FF;
    border: 1.5px solid #0284C7;
    border-radius: 12px;
    padding: 8px 18px;
}
#downloadSetupsBtn:hover {
    background-color: #E0F2FE;
    color: #0369A1;
}
#downloadSetupsBtn:pressed {
    background-color: #BAE6FD;
}
#downloadSetupsBtn:disabled {
    background-color: #F8FAFC;
    color: #94A3B8;
    border: 1px solid #E2E8F0;
}

#revertTweaksBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #DC2626;
    background-color: #FEF2F2;
    border: 1.5px solid rgba(220, 38, 38, 0.4);
    border-radius: 12px;
    padding: 8px 18px;
}
#revertTweaksBtn:hover {
    background-color: #FEE2E2;
}

#cancelBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    color: #FFFFFF;
    background-color: #DC2626;
    border-radius: 12px;
    border: none;
    padding: 8px 18px;
}
#cancelBtn:hover {
    background-color: #B91C1C;
}

#terminalToggleBtn {
    font-family: -apple-system, 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 12px;
    padding: 7px 16px;
}
#terminalToggleBtn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

/* =========================================================================
   PROGRESS BAR
   ========================================================================= */
QProgressBar {
    border: 2px solid #CBD5E1;
    background-color: #F1F5F9;
    text-align: center;
    color: #0F172A;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    font-weight: 600;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #16A34A;
}

/* =========================================================================
   RETRO TERMINAL / CONSOLE
   ========================================================================= */
#terminalConsole {
    background-color: #0F172A;
    color: #4ADE80;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border-top: 2px solid #16A34A;
    padding: 8px;
}

/* =========================================================================
   SCROLLBAR
   ========================================================================= */
QScrollBar:vertical {
    background-color: #F1F5F9;
    width: 12px;
    margin: 0px;
    border-left: 1px solid #E2E8F0;
}
QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    min-height: 20px;
    border: 1px solid #94A3B8;
}
QScrollBar::handle:vertical:hover {
    background-color: #0284C7;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* =========================================================================
   TOOLTIPS
   ========================================================================= */
QToolTip {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 2px solid #0284C7;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    padding: 6px 10px;
}

/* =========================================================================
   MENUS
   ========================================================================= */
QMenu {
    background-color: #FFFFFF;
    border: 2px solid #0284C7;
    padding: 6px;
    color: #0F172A;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QMenu::item {
    padding: 7px 24px 7px 12px;
    background-color: transparent;
    color: #1E293B;
}
QMenu::item:disabled {
    color: #0369A1;
    font-weight: bold;
}
QMenu::item:selected {
    background-color: #E0F2FE;
    color: #0369A1;
}
QMenu::separator {
    height: 1px;
    background-color: #CBD5E1;
    margin: 5px 8px;
}

/* =========================================================================
   DIALOGS & PROFILE MODALS
   ========================================================================= */
#dialogTitle {
    font-size: 15px;
    font-weight: bold;
    color: #0369A1;
}
#dialogInfoBox {
    background-color: #F0F9FF;
    border: 1px solid #BAE6FD;
    padding: 8px 12px;
}
#dialogInfoTitle {
    color: #15803D;
    font-weight: bold;
    font-size: 11.5px;
}
#dialogInfoSub {
    color: #475569;
    font-size: 11px;
}
#dialogFieldLabel {
    font-weight: 600;
    color: #0F172A;
    font-size: 12px;
}
#dialogInput {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #0284C7;
    padding: 7px 10px;
    font-size: 13px;
}
.dialogAvatarBtn {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    font-size: 14px;
}
.dialogAvatarBtn:checked {
    background-color: #E0F2FE;
    border: 2px solid #0284C7;
}
.dialogAvatarBtn:hover {
    background-color: #E2E8F0;
}
#dialogPrimaryBtn {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px 18px;
    border: none;
    font-size: 12px;
}
#dialogPrimaryBtn:hover {
    background-color: #0369A1;
}
#dialogSecondaryBtn {
    background-color: #F1F5F9;
    color: #334155;
    padding: 8px 16px;
    border: 1px solid #CBD5E1;
    font-size: 12px;
}
#dialogSecondaryBtn:hover {
    background-color: #E2E8F0;
    color: #0F172A;
}

QMessageBox {
    background-color: #FFFFFF;
    color: #0F172A;
}
QMessageBox QPushButton {
    background-color: #F0F9FF;
    color: #0284C7;
    border: 1px solid #0284C7;
    padding: 6px 16px;
    font-weight: bold;
}
QMessageBox QPushButton:hover {
    background-color: #E0F2FE;
}
"""

# Backwards compatibility alias
PIXEL_STYLE = DARK_STYLE


def get_stylesheet(theme: str = "dark") -> str:
    """Returns the compiled stylesheet for the specified theme ('dark' or 'light')."""
    is_light = (theme == "light")
    base_style = LIGHT_STYLE if is_light else DARK_STYLE

    if is_light:
        on_path = resource_path("assets/apple_switch_on_light.png").replace("\\", "/")
        off_path = resource_path("assets/apple_switch_off_light.png").replace("\\", "/")
        style = base_style.replace(
            'url("assets/apple_switch_on_light.png")', f'url("{on_path}")'
        ).replace(
            'url("assets/apple_switch_off_light.png")', f'url("{off_path}")'
        )
    else:
        on_path = resource_path("assets/apple_switch_on_dark.png").replace("\\", "/")
        off_path = resource_path("assets/apple_switch_off_dark.png").replace("\\", "/")
        style = base_style.replace(
            'url("assets/apple_switch_on_dark.png")', f'url("{on_path}")'
        ).replace(
            'url("assets/apple_switch_off_dark.png")', f'url("{off_path}")'
        )

    return style


def get_theme_accent(theme: str = "dark") -> dict:
    """Returns the color palette metadata for the given theme."""
    return THEME_CONFIG.get(theme, THEME_CONFIG["dark"])
