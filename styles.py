"""
Apple macOS Aesthetic Design System for Keystone
Curated Cupertino / macOS Sonoma & Sequoia design system.
Includes Apple Dark Mode and Apple Light Mode, refined typography (-apple-system, SF Pro, Segoe UI),
authentic Apple color palette, frosted glass translucent surfaces, smooth rounded corners (8-12px),
macOS traffic lights, modern segmented pill controls, clean badges, and macOS card hierarchy.
"""

from utils import resource_path

# =============================================================================
# THEME PALETTES & ACCENT METADATA (APPLE DESIGN SYSTEM)
# =============================================================================

THEME_CONFIG = {
    "dark": {
        "primary_accent": "#0A84FF",      # Apple System Blue
        "secondary_accent": "#30D158",    # Apple System Green
        "warning_accent": "#FFD60A",      # Apple System Yellow
        "error_accent": "#FF453A",        # Apple System Red
        "text_primary": "#F5F5F7",        # Apple Primary Text
        "text_secondary": "#A1A1A6",      # Apple Secondary Text
        "text_muted": "#6E6E73",          # Apple Tertiary / Muted
        "meta_color": "#86868B",
        "card_bg": "#252528",
        "card_checked_bg": "#1C2B3A",
        "window_bg": "#1E1E1E",
    },
    "light": {
        "primary_accent": "#0071E3",      # Apple System Blue Light
        "secondary_accent": "#28CD41",    # Apple System Green Light
        "warning_accent": "#FF9F0A",      # Apple System Orange
        "error_accent": "#FF3B30",        # Apple System Red Light
        "text_primary": "#1D1D1F",
        "text_secondary": "#424245",
        "text_muted": "#86868B",
        "meta_color": "#6E6E73",
        "card_bg": "#FFFFFF",
        "card_checked_bg": "#EEF6FF",
        "window_bg": "#F5F5F7",
    }
}


# =============================================================================
# APPLE DARK MODE (MACOS DARK STYLING)
# =============================================================================

DARK_STYLE = """
/* =========================================================================
   GLOBAL RESET & BASICS - APPLE MACOS DARK
   ========================================================================= */
QMainWindow, QDialog {
    background-color: #1E1E1E;
    color: #F5F5F7;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Inter, sans-serif;
    font-size: 13px;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Inter, sans-serif;
    outline: none;
    color: #F5F5F7;
}

QToolTip {
    background-color: #2C2C2E;
    color: #F5F5F7;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11.5px;
}

/* =========================================================================
   MACOS HEADER / TOOLBAR
   ========================================================================= */
#headerContainer {
    background-color: #242426;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 9px 18px;
}

/* Traffic Light Circle Buttons */
#trafficLightsBox {
    background: transparent;
}

#trafficCloseBtn {
    background-color: #FF5F56;
    border: 1px solid #E0443E;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficCloseBtn:hover {
    background-color: #FF3B30;
}

#trafficMinBtn {
    background-color: #FFBD2E;
    border: 1px solid #DEA123;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficMinBtn:hover {
    background-color: #F5A623;
}

#trafficMaxBtn {
    background-color: #27C93F;
    border: 1px solid #1AAB29;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficMaxBtn:hover {
    background-color: #1F9A30;
}

#menuHeaderBtn {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #F5F5F7;
}
#menuHeaderBtn:hover {
    background-color: rgba(255, 255, 255, 0.14);
}

#appLogo {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9px;
    background-color: rgba(255, 255, 255, 0.04);
}

#titleLabel {
    font-size: 15px;
    font-weight: 700;
    color: #F5F5F7;
    letter-spacing: -0.2px;
}

#subtitleLabel {
    font-size: 11px;
    font-weight: 400;
    color: #86868B;
}

#adminBadge {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 14px;
    border: 1px solid rgba(255, 69, 58, 0.4);
    background-color: rgba(255, 69, 58, 0.12);
    color: #FF453A;
    border-radius: 12px;
}
#adminBadge:hover {
    background-color: rgba(255, 69, 58, 0.22);
}

#adminBadgeElevated {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 14px;
    border: 1px solid rgba(48, 209, 88, 0.35);
    background-color: rgba(48, 209, 88, 0.12);
    color: #30D158;
    border-radius: 12px;
}

#profileSwitcherBtn, #profileBtn, #themeToggleBtn, #headerSettingsBtn {
    background-color: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #F5F5F7;
}
#profileSwitcherBtn:hover, #profileBtn:hover, #themeToggleBtn:hover, #headerSettingsBtn:hover {
    background-color: rgba(255, 255, 255, 0.13);
    border-color: rgba(255, 255, 255, 0.2);
}

/* =========================================================================
   TOP INSPECT PANEL (MACOS SYSTEM HUD / INSPECTOR)
   ========================================================================= */
#inspectPanel {
    background-color: #212124;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px 18px;
}

#inspectBadge {
    background-color: rgba(10, 132, 255, 0.15);
    color: #0A84FF;
    border: 1px solid rgba(10, 132, 255, 0.35);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#inspectBadgeSuccess {
    background-color: rgba(48, 209, 88, 0.15);
    color: #30D158;
    border: 1px solid rgba(48, 209, 88, 0.35);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#inspectTitle {
    font-size: 14px;
    font-weight: 700;
    color: #F5F5F7;
}

#inspectCatLbl {
    font-size: 11px;
    font-weight: 600;
    color: #0A84FF;
}

#inspectCatSuccess {
    font-size: 11px;
    font-weight: 600;
    color: #30D158;
}

#inspectMeta {
    font-size: 11px;
    color: #86868B;
}

#inspectDesc {
    font-size: 12px;
    color: #D1D1D6;
    line-height: 1.4;
}

#inspectHintLbl {
    font-size: 11px;
    color: #86868B;
}

#inspectHintSuccess {
    font-size: 11px;
    color: #30D158;
}

/* =========================================================================
   SIDEBAR (MACOS FINDER / SYSTEM SETTINGS STYLE)
   ========================================================================= */
#sidebarContainer, #sidebarPanel {
    background-color: #1E1E21;
    border-right: 1px solid rgba(255, 255, 255, 0.07);
}

.sidebarTabBtn {
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    color: #A1A1A6;
    background-color: transparent;
}
.sidebarTabBtn:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #F5F5F7;
}
.sidebarTabBtn[selected="true"] {
    background-color: #0A84FF;
    color: #FFFFFF;
    font-weight: 600;
}

.sidebarRailBtn {
    border: none;
    border-radius: 8px;
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    font-size: 16px;
    background-color: transparent;
    color: #A1A1A6;
}
.sidebarRailBtn:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: #F5F5F7;
}
.sidebarRailBtn[selected="true"] {
    background-color: #0A84FF;
    color: #FFFFFF;
}

#sidebarToggleBtn {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    background-color: rgba(255, 255, 255, 0.05);
    color: #A1A1A6;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 500;
}
#sidebarToggleBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #F5F5F7;
}

#navTree {
    border: none;
    background-color: transparent;
    color: #A1A1A6;
    font-size: 12.5px;
    padding: 4px;
}
#navTree::item {
    height: 28px;
    border-radius: 6px;
    padding: 2px 6px;
}
#navTree::item:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #F5F5F7;
}
#navTree::item:selected {
    background-color: rgba(10, 132, 255, 0.22);
    color: #0A84FF;
    font-weight: 600;
}

/* =========================================================================
   TOOLBARS & CONTROL BARS (MACOS SEGMENTED PILLS)
   ========================================================================= */
#categoryBar, #presetBar {
    background-color: #1E1E21;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    padding: 8px 14px;
}

.barSectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #86868B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.categoryTab {
    border: none;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #A1A1A6;
    background-color: transparent;
}
.categoryTab:hover {
    background-color: rgba(255, 255, 255, 0.07);
    color: #F5F5F7;
}
.categoryTab[selected="true"] {
    background-color: rgba(255, 255, 255, 0.15);
    color: #FFFFFF;
    font-weight: 600;
}

.presetBtn {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #D1D1D6;
    background-color: rgba(255, 255, 255, 0.05);
}
.presetBtn:hover {
    background-color: rgba(255, 255, 255, 0.11);
    border-color: rgba(255, 255, 255, 0.2);
    color: #FFFFFF;
}
.presetBtn[selected="true"] {
    background-color: rgba(255, 255, 255, 0.16);
    border-color: rgba(255, 255, 255, 0.35);
    color: #FFFFFF;
    font-weight: 600;
}

#btnToggleSelectAll {
    border: 1.5px solid #0A84FF;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #5AC8FA;
    background-color: rgba(10, 132, 255, 0.16);
}
#btnToggleSelectAll:hover {
    background-color: rgba(10, 132, 255, 0.30);
    border-color: #5AC8FA;
    color: #FFFFFF;
}
#btnToggleSelectAll[mode="clear"] {
    border: 1.5px solid #FF453A;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #FF6961;
    background-color: rgba(255, 69, 58, 0.16);
}
#btnToggleSelectAll[mode="clear"]:hover {
    background-color: rgba(255, 69, 58, 0.30);
    border-color: #FF6961;
    color: #FFFFFF;
}

#presetCombo {
    background-color: #212124;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    padding: 5px 12px;
    color: #F5F5F7;
    font-size: 12px;
    font-weight: 500;
    min-width: 250px;
}
#presetCombo:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.28);
}
#presetCombo::drop-down {
    border: none;
    width: 20px;
    padding-right: 6px;
}
#presetCombo QAbstractItemView {
    background-color: #1C1C1E;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    selection-background-color: #0A84FF;
    selection-color: #FFFFFF;
    color: #F5F5F7;
    padding: 6px;
}

#presetApplyBtn {
    background-color: rgba(10, 132, 255, 0.16);
    border: 1px solid rgba(10, 132, 255, 0.4);
    color: #5AC8FA;
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}
#presetApplyBtn:hover {
    background-color: #0A84FF;
    color: #FFFFFF;
}

#searchBox {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12.5px;
    color: #F5F5F7;
    background-color: rgba(255, 255, 255, 0.06);
}
#searchBox:focus {
    border: 1.5px solid #0A84FF;
    background-color: rgba(255, 255, 255, 0.09);
}

/* =========================================================================
   MAIN SCROLL AREA & WORKSPACE
   ========================================================================= */
#rightPane {
    background-color: #18181A;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

#scrollContent {
    background-color: #18181A;
}

/* =========================================================================
   CARDS (MACOS CARD DESIGN SYSTEM)
   ========================================================================= */
.pkgCard {
    background-color: #252528;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 0px;
}
.pkgCard:hover {
    background-color: #2D2D31;
    border: 1px solid rgba(10, 132, 255, 0.45);
}
.pkgCard[checked="true"] {
    background-color: #1C2B3A;
    border: 1.5px solid #0A84FF;
}

/* Apple Toggle Switch */
QCheckBox {
    min-height: 24px;
    spacing: 10px;
    font-size: 13px;
    font-weight: 600;
    color: #F5F5F7;
}
QCheckBox::indicator {
    width: 38px;
    height: 22px;
    border: none;
    background-color: transparent;
    subcontrol-origin: padding;
    subcontrol-position: left center;
}
QCheckBox::indicator:unchecked {
    image: url("assets/apple_switch_off_dark.png");
}
QCheckBox::indicator:checked {
    image: url("assets/apple_switch_on_dark.png");
}


.pkgDesc {
    font-size: 11px;
    color: #A1A1A6;
    line-height: 1.35;
}

/* =========================================================================
   PILL BADGES (MACOS TINTED PILLS)
   ========================================================================= */
.pkgPortableBadge {
    background-color: rgba(191, 90, 242, 0.16);
    color: #BF5AF2;
    border: 1px solid rgba(191, 90, 242, 0.38);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgSetupBadge {
    background-color: rgba(10, 132, 255, 0.15);
    color: #0A84FF;
    border: 1px solid rgba(10, 132, 255, 0.35);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgInstalledBadge {
    background-color: rgba(50, 215, 75, 0.14);
    color: #32D74B;
    border: 1px solid rgba(50, 215, 75, 0.3);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
}

.pkgTag {
    background-color: rgba(255, 255, 255, 0.08);
    color: #8E8E93;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 500;
    padding: 1px 7px;
}

.pkgStatusInstalling {
    background-color: rgba(255, 214, 10, 0.15);
    color: #FFD60A;
    border: 1px solid rgba(255, 214, 10, 0.35);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
}

.pkgStatusSuccess {
    background-color: rgba(48, 209, 88, 0.2);
    color: #30D158;
    border: 1px solid rgba(48, 209, 88, 0.4);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgStatusError {
    background-color: rgba(255, 69, 58, 0.18);
    color: #FF453A;
    border: 1px solid rgba(255, 69, 58, 0.4);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgStatusWarning {
    background-color: rgba(255, 159, 10, 0.18);
    color: #FF9F0A;
    border: 1px solid rgba(255, 159, 10, 0.4);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

/* =========================================================================
   BOTTOM ACTION BAR & CONTROLS
   ========================================================================= */
#actionBar {
    background-color: #242426;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding: 11px 18px;
}

.selectedCountLabel {
    font-size: 12.5px;
    font-weight: 600;
    color: #F5F5F7;
}

.installBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A84FF, stop:1 #0071E3);
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
}
.installBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A8CFF, stop:1 #0A7AFF);
}

.revertTweaksBtn {
    background-color: rgba(255, 69, 58, 0.12);
    border: 1px solid rgba(255, 69, 58, 0.35);
    border-radius: 8px;
    color: #FF453A;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
}
.revertTweaksBtn:hover {
    background-color: rgba(255, 69, 58, 0.22);
}

.downloadSetupsBtn {
    background-color: rgba(255, 255, 255, 0.09);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    color: #F5F5F7;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
}
.downloadSetupsBtn:hover {
    background-color: rgba(255, 255, 255, 0.15);
}

.clearBtn {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #A1A1A6;
    background-color: transparent;
    padding: 8px 14px;
    font-size: 12px;
}
.clearBtn:hover {
    background-color: rgba(255, 255, 255, 0.06);
    color: #F5F5F7;
}

.cancelBtn {
    background-color: rgba(255, 69, 58, 0.15);
    border: 1px solid rgba(255, 69, 58, 0.35);
    border-radius: 8px;
    color: #FF453A;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 14px;
}

.terminalToggleBtn {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #A1A1A6;
    background-color: rgba(255, 255, 255, 0.05);
    padding: 8px 14px;
    font-size: 12px;
}
.terminalToggleBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #F5F5F7;
}

/* macOS Progress Bar */
QProgressBar {
    border: none;
    border-radius: 5px;
    height: 8px;
    background-color: rgba(255, 255, 255, 0.1);
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0A84FF, stop:1 #30D158);
}

/* =========================================================================
   TERMINAL CONSOLE (MACOS TERMINAL / MONTEREY STYLE)
   ========================================================================= */
#terminalContainer {
    background-color: #121214;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}
#terminalHeader {
    background-color: #18181B;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
#terminalConsole {
    background-color: #121214;
    border: none;
    color: #30D158;
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
}

/* =========================================================================
   SLIM MACOS SCROLLBARS
   ========================================================================= */
QScrollBar:vertical {
    width: 7px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.32);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar:horizontal {
    height: 7px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.18);
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.32);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* Splitter Handle */
#mainSplitter::handle {
    background-color: rgba(255, 255, 255, 0.07);
    width: 1px;
}

/* Profile Dialog */
.dialogTitle {
    font-size: 15px;
    font-weight: 700;
    color: #F5F5F7;
}
.dialogFieldLabel {
    font-size: 12px;
    font-weight: 500;
    color: #A1A1A6;
}
.dialogInput {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    background-color: rgba(255, 255, 255, 0.06);
    color: #F5F5F7;
}
.dialogInput:focus {
    border: 1.5px solid #0A84FF;
}
.dialogPrimaryBtn {
    background-color: #0A84FF;
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
}
.dialogPrimaryBtn:hover {
    background-color: #1A8CFF;
}
.dialogSecondaryBtn {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #F5F5F7;
    font-size: 13px;
    font-weight: 500;
    padding: 7px 16px;
}

/* Settings View Styles (Dark) */
.settingsCard {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 18px 22px;
}
.settingsHeaderTitle {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: -0.3px;
}
.settingsHeaderDesc {
    font-size: 13px;
    color: #A1A1A6;
}
.settingsSectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
}
.settingsSectionDesc {
    font-size: 12px;
    color: #8E8E93;
}
.themeSegmentContainer {
    background-color: rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    padding: 4px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.themeSegmentBtn {
    background-color: transparent;
    color: #A1A1A6;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12.5px;
    font-weight: 500;
}
.themeSegmentBtn:hover {
    color: #FFFFFF;
}
.themeSegmentBtn[selected="true"] {
    background-color: #0A84FF;
    color: #FFFFFF;
    font-weight: 600;
}
.settingsActionBtn {
    background-color: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #F5F5F7;
}
.settingsActionBtn:hover {
    background-color: rgba(255, 255, 255, 0.13);
    border-color: rgba(255, 255, 255, 0.22);
}
.settingsDangerBtn {
    background-color: rgba(255, 69, 58, 0.15);
    border: 1px solid rgba(255, 69, 58, 0.3);
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #FF453A;
}
.settingsDangerBtn:hover {
    background-color: rgba(255, 69, 58, 0.25);
    border-color: rgba(255, 69, 58, 0.5);
}
.settingsComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    color: #FFFFFF;
    min-width: 220px;
}
.settingsComboBox QAbstractItemView {
    background-color: #252528;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 7px;
    color: #FFFFFF;
    selection-background-color: #0A84FF;
}
"""



# =============================================================================
# APPLE LIGHT MODE (MACOS LIGHT STYLING)
# =============================================================================

LIGHT_STYLE = """
/* =========================================================================
   GLOBAL RESET & BASICS - APPLE MACOS LIGHT
   ========================================================================= */
QMainWindow, QDialog {
    background-color: #F5F5F7;
    color: #1D1D1F;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Inter, sans-serif;
    font-size: 13px;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Inter, sans-serif;
    outline: none;
    color: #1D1D1F;
}

QToolTip {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11.5px;
}

/* =========================================================================
   MACOS HEADER / TOOLBAR (LIGHT)
   ========================================================================= */
#headerContainer {
    background-color: #FFFFFF;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    padding: 9px 18px;
}

#trafficLightsBox {
    background: transparent;
}

#trafficCloseBtn {
    background-color: #FF5F56;
    border: 1px solid #E0443E;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficCloseBtn:hover {
    background-color: #FF3B30;
}

#trafficMinBtn {
    background-color: #FFBD2E;
    border: 1px solid #DEA123;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficMinBtn:hover {
    background-color: #F5A623;
}

#trafficMaxBtn {
    background-color: #27C93F;
    border: 1px solid #1AAB29;
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}
#trafficMaxBtn:hover {
    background-color: #1F9A30;
}

#menuHeaderBtn {
    background-color: rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #1D1D1F;
}
#menuHeaderBtn:hover {
    background-color: rgba(0, 0, 0, 0.09);
}

#appLogo {
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 9px;
    background-color: rgba(0, 0, 0, 0.03);
}

#titleLabel {
    font-size: 15px;
    font-weight: 700;
    color: #1D1D1F;
    letter-spacing: -0.2px;
}

#subtitleLabel {
    font-size: 11px;
    font-weight: 400;
    color: #86868B;
}

#adminBadge {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 14px;
    border: 1px solid rgba(255, 59, 48, 0.35);
    background-color: rgba(255, 59, 48, 0.08);
    color: #FF3B30;
    border-radius: 12px;
}
#adminBadge:hover {
    background-color: rgba(255, 59, 48, 0.16);
}

#adminBadgeElevated {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 14px;
    border: 1px solid rgba(40, 205, 65, 0.35);
    background-color: rgba(40, 205, 65, 0.1);
    color: #28CD41;
    border-radius: 12px;
}

#profileSwitcherBtn, #profileBtn, #themeToggleBtn, #headerSettingsBtn {
    background-color: rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #1D1D1F;
}
#profileSwitcherBtn:hover, #profileBtn:hover, #themeToggleBtn:hover, #headerSettingsBtn:hover {
    background-color: rgba(0, 0, 0, 0.09);
    border-color: rgba(0, 0, 0, 0.18);
}

/* =========================================================================
   TOP INSPECT PANEL (LIGHT)
   ========================================================================= */
#inspectPanel {
    background-color: #FBFBFD;
    border-bottom: 1px solid rgba(0, 0, 0, 0.07);
    padding: 10px 18px;
}

#inspectBadge {
    background-color: rgba(0, 113, 227, 0.1);
    color: #0071E3;
    border: 1px solid rgba(0, 113, 227, 0.28);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#inspectBadgeSuccess {
    background-color: rgba(40, 205, 65, 0.12);
    color: #28CD41;
    border: 1px solid rgba(40, 205, 65, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#inspectTitle {
    font-size: 14px;
    font-weight: 700;
    color: #1D1D1F;
}

#inspectCatLbl {
    font-size: 11px;
    font-weight: 600;
    color: #0071E3;
}

#inspectCatSuccess {
    font-size: 11px;
    font-weight: 600;
    color: #28CD41;
}

#inspectMeta {
    font-size: 11px;
    color: #86868B;
}

#inspectDesc {
    font-size: 12px;
    color: #424245;
    line-height: 1.4;
}

#inspectHintLbl {
    font-size: 11px;
    color: #86868B;
}

#inspectHintSuccess {
    font-size: 11px;
    color: #28CD41;
}

/* =========================================================================
   SIDEBAR (LIGHT)
   ========================================================================= */
#sidebarContainer, #sidebarPanel {
    background-color: #F2F2F5;
    border-right: 1px solid rgba(0, 0, 0, 0.07);
}

.sidebarTabBtn {
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    color: #515154;
    background-color: transparent;
}
.sidebarTabBtn:hover {
    background-color: rgba(0, 0, 0, 0.05);
    color: #1D1D1F;
}
.sidebarTabBtn[selected="true"] {
    background-color: #0071E3;
    color: #FFFFFF;
    font-weight: 600;
}

.sidebarRailBtn {
    border: none;
    border-radius: 8px;
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    font-size: 16px;
    background-color: transparent;
    color: #515154;
}
.sidebarRailBtn:hover {
    background-color: rgba(0, 0, 0, 0.06);
    color: #1D1D1F;
}
.sidebarRailBtn[selected="true"] {
    background-color: #0071E3;
    color: #FFFFFF;
}

#sidebarToggleBtn {
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 6px;
    background-color: rgba(0, 0, 0, 0.04);
    color: #6E6E73;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 500;
}
#sidebarToggleBtn:hover {
    background-color: rgba(0, 0, 0, 0.08);
    color: #1D1D1F;
}

#navTree {
    border: none;
    background-color: transparent;
    color: #515154;
    font-size: 12.5px;
    padding: 4px;
}
#navTree::item {
    height: 28px;
    border-radius: 6px;
    padding: 2px 6px;
}
#navTree::item:hover {
    background-color: rgba(0, 0, 0, 0.05);
    color: #1D1D1F;
}
#navTree::item:selected {
    background-color: rgba(0, 113, 227, 0.15);
    color: #0071E3;
    font-weight: 600;
}

/* =========================================================================
   TOOLBARS & CONTROL BARS (LIGHT)
   ========================================================================= */
#categoryBar, #presetBar {
    background-color: #FBFBFD;
    border-bottom: 1px solid rgba(0, 0, 0, 0.07);
    padding: 8px 14px;
}

.barSectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #86868B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.categoryTab {
    border: none;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #6E6E73;
    background-color: transparent;
}
.categoryTab:hover {
    background-color: rgba(0, 0, 0, 0.05);
    color: #1D1D1F;
}
.categoryTab[selected="true"] {
    background-color: #FFFFFF;
    color: #1D1D1F;
    font-weight: 600;
    border: 1px solid rgba(0, 0, 0, 0.08);
}

.presetBtn {
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #424245;
    background-color: #FFFFFF;
}
.presetBtn:hover {
    background-color: #F5F5F7;
    border-color: rgba(0, 0, 0, 0.18);
    color: #1D1D1F;
}
.presetBtn[selected="true"] {
    background-color: rgba(0, 113, 227, 0.12);
    border-color: #0071E3;
    color: #0071E3;
    font-weight: 600;
}

#btnToggleSelectAll {
    border: 1.5px solid #0071E3;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #0071E3;
    background-color: rgba(0, 113, 227, 0.10);
}
#btnToggleSelectAll:hover {
    background-color: rgba(0, 113, 227, 0.22);
    border-color: #0077ED;
    color: #0077ED;
}
#btnToggleSelectAll[mode="clear"] {
    border: 1.5px solid #FF3B30;
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #FF3B30;
    background-color: rgba(255, 59, 48, 0.10);
}
#btnToggleSelectAll[mode="clear"]:hover {
    background-color: rgba(255, 59, 48, 0.22);
    border-color: #E02B20;
    color: #E02B20;
}

#presetCombo {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 8px;
    padding: 5px 12px;
    color: #1D1D1F;
    font-size: 12px;
    font-weight: 500;
    min-width: 250px;
}
#presetCombo:hover {
    background-color: #F5F5F7;
    border-color: rgba(0, 0, 0, 0.3);
}
#presetCombo::drop-down {
    border: none;
    width: 20px;
    padding-right: 6px;
}
#presetCombo QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 8px;
    selection-background-color: #0071E3;
    selection-color: #FFFFFF;
    color: #1D1D1F;
    padding: 6px;
}

#presetApplyBtn {
    background-color: rgba(0, 113, 227, 0.12);
    border: 1px solid rgba(0, 113, 227, 0.35);
    color: #0071E3;
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}
#presetApplyBtn:hover {
    background-color: #0071E3;
    color: #FFFFFF;
}

#searchBox {
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12.5px;
    color: #1D1D1F;
    background-color: #FFFFFF;
}
#searchBox:focus {
    border: 1.5px solid #0071E3;
}

/* =========================================================================
   MAIN SCROLL AREA & WORKSPACE (LIGHT)
   ========================================================================= */
#rightPane {
    background-color: #F5F5F7;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

#scrollContent {
    background-color: #F5F5F7;
}

/* =========================================================================
   CARDS (LIGHT)
   ========================================================================= */
.pkgCard {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    padding: 0px;
}
.pkgCard:hover {
    background-color: #FBFBFD;
    border: 1px solid rgba(0, 113, 227, 0.45);
}
.pkgCard[checked="true"] {
    background-color: #EEF6FF;
    border: 1.5px solid #0071E3;
}

/* Apple Toggle Switch (Light) */
QCheckBox {
    min-height: 24px;
    spacing: 10px;
    font-size: 13px;
    font-weight: 600;
    color: #1D1D1F;
}
QCheckBox::indicator {
    width: 38px;
    height: 22px;
    border: none;
    background-color: transparent;
    subcontrol-origin: padding;
    subcontrol-position: left center;
}
QCheckBox::indicator:unchecked {
    image: url("assets/apple_switch_off_light.png");
}
QCheckBox::indicator:checked {
    image: url("assets/apple_switch_on_light.png");
}


.pkgDesc {
    font-size: 11px;
    color: #515154;
    line-height: 1.35;
}

/* =========================================================================
   PILL BADGES (LIGHT)
   ========================================================================= */
.pkgPortableBadge {
    background-color: rgba(175, 82, 222, 0.12);
    color: #AF52DE;
    border: 1px solid rgba(175, 82, 222, 0.32);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgSetupBadge {
    background-color: rgba(0, 113, 227, 0.12);
    color: #0071E3;
    border: 1px solid rgba(0, 113, 227, 0.3);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgInstalledBadge {
    background-color: rgba(40, 205, 65, 0.14);
    color: #28CD41;
    border: 1px solid rgba(40, 205, 65, 0.3);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
}

.pkgTag {
    background-color: rgba(0, 0, 0, 0.05);
    color: #6E6E73;
    border: 1px solid rgba(0, 0, 0, 0.09);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 500;
    padding: 1px 7px;
}

.pkgStatusInstalling {
    background-color: rgba(255, 159, 10, 0.12);
    color: #FF9F0A;
    border: 1px solid rgba(255, 159, 10, 0.3);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
}

.pkgStatusSuccess {
    background-color: rgba(40, 205, 65, 0.15);
    color: #28CD41;
    border: 1px solid rgba(40, 205, 65, 0.35);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgStatusError {
    background-color: rgba(255, 59, 48, 0.12);
    color: #FF3B30;
    border: 1px solid rgba(255, 59, 48, 0.3);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

.pkgStatusWarning {
    background-color: rgba(255, 159, 10, 0.14);
    color: #FF9F0A;
    border: 1px solid rgba(255, 159, 10, 0.35);
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
}

/* =========================================================================
   BOTTOM ACTION BAR (LIGHT)
   ========================================================================= */
#actionBar {
    background-color: #FFFFFF;
    border-top: 1px solid rgba(0, 0, 0, 0.08);
    padding: 11px 18px;
}

.selectedCountLabel {
    font-size: 12.5px;
    font-weight: 600;
    color: #1D1D1F;
}

.installBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0071E3, stop:1 #005BB5);
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
}
.installBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A84EB, stop:1 #0066CC);
}

.revertTweaksBtn {
    background-color: rgba(255, 59, 48, 0.08);
    border: 1px solid rgba(255, 59, 48, 0.3);
    border-radius: 8px;
    color: #FF3B30;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
}
.revertTweaksBtn:hover {
    background-color: rgba(255, 59, 48, 0.16);
}

.downloadSetupsBtn {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 8px;
    color: #1D1D1F;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
}
.downloadSetupsBtn:hover {
    background-color: #F5F5F7;
}

.clearBtn {
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 8px;
    color: #6E6E73;
    background-color: transparent;
    padding: 8px 14px;
    font-size: 12px;
}
.clearBtn:hover {
    background-color: rgba(0, 0, 0, 0.05);
    color: #1D1D1F;
}

.cancelBtn {
    background-color: rgba(255, 59, 48, 0.1);
    border: 1px solid rgba(255, 59, 48, 0.3);
    border-radius: 8px;
    color: #FF3B30;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 14px;
}

.terminalToggleBtn {
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 8px;
    color: #6E6E73;
    background-color: rgba(0, 0, 0, 0.04);
    padding: 8px 14px;
    font-size: 12px;
}
.terminalToggleBtn:hover {
    background-color: rgba(0, 0, 0, 0.08);
    color: #1D1D1F;
}

/* macOS Progress Bar (Light) */
QProgressBar {
    border: none;
    border-radius: 5px;
    height: 8px;
    background-color: rgba(0, 0, 0, 0.08);
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0071E3, stop:1 #28CD41);
}

/* Terminal Console (Light) */
#terminalContainer {
    background-color: #1E1E24;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
}
#terminalHeader {
    background-color: #26262D;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
#terminalConsole {
    background-color: #1E1E24;
    border: none;
    color: #28CD41;
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 12px;
    padding: 10px;
}

/* macOS Scrollbars (Light) */
QScrollBar:vertical {
    width: 7px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0, 0, 0, 0.35);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

QScrollBar:horizontal {
    height: 7px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(0, 0, 0, 0.35);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

#mainSplitter::handle {
    background-color: rgba(0, 0, 0, 0.07);
    width: 1px;
}

/* Profile Dialog (Light) */
.dialogTitle {
    font-size: 15px;
    font-weight: 700;
    color: #1D1D1F;
}
.dialogFieldLabel {
    font-size: 12px;
    font-weight: 500;
    color: #6E6E73;
}
.dialogInput {
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    background-color: #FFFFFF;
    color: #1D1D1F;
}
.dialogInput:focus {
    border: 1.5px solid #0071E3;
}
.dialogPrimaryBtn {
    background-color: #0071E3;
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
}
.dialogPrimaryBtn:hover {
    background-color: #1A84EB;
}
.dialogSecondaryBtn {
    background-color: rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    color: #1D1D1F;
    font-size: 13px;
    font-weight: 500;
    padding: 7px 16px;
}

/* Settings View Styles (Light) */
.settingsCard {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 12px;
    padding: 18px 22px;
}
.settingsHeaderTitle {
    font-size: 20px;
    font-weight: 700;
    color: #1D1D1F;
    letter-spacing: -0.3px;
}
.settingsHeaderDesc {
    font-size: 13px;
    color: #6E6E73;
}
.settingsSectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #1D1D1F;
}
.settingsSectionDesc {
    font-size: 12px;
    color: #6E6E73;
}
.themeSegmentContainer {
    background-color: rgba(0, 0, 0, 0.05);
    border-radius: 8px;
    padding: 4px;
    border: 1px solid rgba(0, 0, 0, 0.08);
}
.themeSegmentBtn {
    background-color: transparent;
    color: #6E6E73;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12.5px;
    font-weight: 500;
}
.themeSegmentBtn:hover {
    color: #1D1D1F;
}
.themeSegmentBtn[selected="true"] {
    background-color: #0071E3;
    color: #FFFFFF;
    font-weight: 600;
}
.settingsActionBtn {
    background-color: rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #1D1D1F;
}
.settingsActionBtn:hover {
    background-color: rgba(0, 0, 0, 0.08);
    border-color: rgba(0, 0, 0, 0.22);
}
.settingsDangerBtn {
    background-color: rgba(255, 59, 48, 0.1);
    border: 1px solid rgba(255, 59, 48, 0.3);
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #FF3B30;
}
.settingsDangerBtn:hover {
    background-color: rgba(255, 59, 48, 0.18);
    border-color: rgba(255, 59, 48, 0.5);
}
.settingsComboBox {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    color: #1D1D1F;
    min-width: 220px;
}
.settingsComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 7px;
    color: #1D1D1F;
    selection-background-color: #0071E3;
}
"""


# Backwards compatibility alias
PIXEL_STYLE = DARK_STYLE


def get_stylesheet(theme: str = "dark") -> str:
    """Returns the compiled Apple macOS stylesheet for the specified theme ('dark' or 'light')."""
    is_light = (theme == "light")
    base_style = LIGHT_STYLE if is_light else DARK_STYLE

    if is_light:
        on_path = resource_path("assets/apple_switch_on_light.png").replace("\\", "/")
        off_path = resource_path("assets/apple_switch_off_light.png").replace("\\", "/")
        check_on_path = resource_path("assets/check_on_light.png").replace("\\", "/")
        style = base_style.replace(
            'url("assets/apple_switch_on_light.png")', f'url("{on_path}")'
        ).replace(
            'url("assets/apple_switch_off_light.png")', f'url("{off_path}")'
        ).replace(
            'url("assets/check_on_light.png")', f'url("{check_on_path}")'
        )
    else:
        on_path = resource_path("assets/apple_switch_on_dark.png").replace("\\", "/")
        off_path = resource_path("assets/apple_switch_off_dark.png").replace("\\", "/")
        check_on_path = resource_path("assets/check_on.png").replace("\\", "/")
        style = base_style.replace(
            'url("assets/apple_switch_on_dark.png")', f'url("{on_path}")'
        ).replace(
            'url("assets/apple_switch_off_dark.png")', f'url("{off_path}")'
        ).replace(
            'url("assets/check_on.png")', f'url("{check_on_path}")'
        )

    return style


def get_theme_accent(theme: str = "dark") -> dict:
    """Returns the color palette metadata for the given theme."""
    return THEME_CONFIG.get(theme, THEME_CONFIG["dark"])
