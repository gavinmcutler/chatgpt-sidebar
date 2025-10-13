# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(SPEC))

# Custom function to filter out unnecessary QML plugins
def filter_qml_plugins(datas):
    """Filter out QML plugins we don't need to reduce size."""
    excluded_qml = [
        'QtCharts', 'Qt3D', 'QtDataVisualization', 'QtGraphs',
        'QtMultimedia', 'QtLocation', 'QtSensors', 'QtTextToSpeech',
        'QtWebView', 'QtRemoteObjects', 'QtScxml', 'QtTest',
        'QtVirtualKeyboard', 'QtQuick3D', 'Scene3D', 'Scene2D'
    ]
    
    filtered = []
    for dest, source, typecode in datas:
        # Check if this is a QML plugin we want to exclude
        should_exclude = False
        for excluded in excluded_qml:
            if f'qml{os.sep}{excluded}' in dest or f'qml\\{excluded}' in dest:
                should_exclude = True
                break
        
        if not should_exclude:
            filtered.append((dest, source, typecode))
    
    return filtered

# Custom function to remove unnecessary files after analysis
def remove_unnecessary_files(binaries, datas):
    """Remove unnecessary Qt translations, locales, and resources."""
    # Files/directories to exclude
    exclude_patterns = [
        # Qt translations (keep only English)
        'translations/qtwebengine_locales/am.pak',
        'translations/qtwebengine_locales/ar.pak',
        'translations/qtwebengine_locales/bg.pak',
        'translations/qtwebengine_locales/bn.pak',
        'translations/qtwebengine_locales/ca.pak',
        'translations/qtwebengine_locales/cs.pak',
        'translations/qtwebengine_locales/da.pak',
        'translations/qtwebengine_locales/de.pak',
        'translations/qtwebengine_locales/el.pak',
        'translations/qtwebengine_locales/es.pak',
        'translations/qtwebengine_locales/et.pak',
        'translations/qtwebengine_locales/fa.pak',
        'translations/qtwebengine_locales/fi.pak',
        'translations/qtwebengine_locales/fil.pak',
        'translations/qtwebengine_locales/fr.pak',
        'translations/qtwebengine_locales/gu.pak',
        'translations/qtwebengine_locales/he.pak',
        'translations/qtwebengine_locales/hi.pak',
        'translations/qtwebengine_locales/hr.pak',
        'translations/qtwebengine_locales/hu.pak',
        'translations/qtwebengine_locales/id.pak',
        'translations/qtwebengine_locales/it.pak',
        'translations/qtwebengine_locales/ja.pak',
        'translations/qtwebengine_locales/kn.pak',
        'translations/qtwebengine_locales/ko.pak',
        'translations/qtwebengine_locales/lt.pak',
        'translations/qtwebengine_locales/lv.pak',
        'translations/qtwebengine_locales/ml.pak',
        'translations/qtwebengine_locales/mr.pak',
        'translations/qtwebengine_locales/ms.pak',
        'translations/qtwebengine_locales/nb.pak',
        'translations/qtwebengine_locales/nl.pak',
        'translations/qtwebengine_locales/pl.pak',
        'translations/qtwebengine_locales/pt-BR.pak',
        'translations/qtwebengine_locales/pt-PT.pak',
        'translations/qtwebengine_locales/ro.pak',
        'translations/qtwebengine_locales/ru.pak',
        'translations/qtwebengine_locales/sk.pak',
        'translations/qtwebengine_locales/sl.pak',
        'translations/qtwebengine_locales/sr.pak',
        'translations/qtwebengine_locales/sv.pak',
        'translations/qtwebengine_locales/sw.pak',
        'translations/qtwebengine_locales/ta.pak',
        'translations/qtwebengine_locales/te.pak',
        'translations/qtwebengine_locales/th.pak',
        'translations/qtwebengine_locales/tr.pak',
        'translations/qtwebengine_locales/uk.pak',
        'translations/qtwebengine_locales/vi.pak',
        'translations/qtwebengine_locales/zh-CN.pak',
        'translations/qtwebengine_locales/zh-TW.pak',
        # Qt Designer files
        'designer',
        # Qt QML files we don't use
        'QtQuick',
        'QtQml',
    ]
    
    filtered_datas = []
    for dest, source, typecode in datas:
        should_exclude = False
        for pattern in exclude_patterns:
            if pattern in dest.replace('\\', '/'):
                should_exclude = True
                break
        if not should_exclude:
            filtered_datas.append((dest, source, typecode))
    
    return binaries, filtered_datas

# Define the analysis
a = Analysis(
    ['main.py'],  # Use standalone entry point
    pathex=[current_dir, os.path.join(current_dir, 'src')],  # Add src directory to path
    binaries=[],
    datas=[],  # Don't collect all PySide6 data - only what's needed will be auto-detected
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        # Add refactored package modules
        'chatgpt_sidebar.app',
        'chatgpt_sidebar.main_window',
        'chatgpt_sidebar.ui.topbar',
        'chatgpt_sidebar.ui.sidebar',
        'chatgpt_sidebar.ui.theme',
        'chatgpt_sidebar.web.engine_qtwebengine',
        'chatgpt_sidebar.platform.appbar_win',
        'chatgpt_sidebar.features.screenshot',
        'chatgpt_sidebar.features.paste_js',
        'chatgpt_sidebar.settings.config',
        'chatgpt_sidebar.utils.logging',
        'chatgpt_sidebar.utils.paths',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused Qt modules to reduce size
        'PySide6.QtBluetooth',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtDesigner',
        'PySide6.QtHelp',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtNetworkAuth',
        'PySide6.QtNfc',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtQuick3D',
        'PySide6.QtQuickControls2',
        'PySide6.QtRemoteObjects',
        'PySide6.QtScxml',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtSerialBus',
        'PySide6.QtSql',
        'PySide6.QtStateMachine',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'PySide6.QtTest',
        'PySide6.QtTextToSpeech',
        'PySide6.QtUiTools',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
        'PySide6.Qt3DAnimation',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DExtras',
        'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic',
        'PySide6.Qt3DRender',
        # Exclude unused Python standard library modules
        'tkinter',
        'unittest',
        'test',
        'pydoc',
        'doctest',
        'xmlrpc',
        'pdb',
        'distutils',
        'setuptools',
        'pip',
        'numpy',
        'matplotlib',
        'pandas',
        'scipy',
        # Exclude encodings we don't need (keep UTF-8, ASCII, Latin-1)
        'encodings.cp949',
        'encodings.cp950',
        'encodings.euc_jp',
        'encodings.euc_jis_2004',
        'encodings.euc_jisx0213',
        'encodings.euc_kr',
        'encodings.gb2312',
        'encodings.gbk',
        'encodings.gb18030',
        'encodings.iso2022_jp',
        'encodings.iso2022_jp_1',
        'encodings.iso2022_jp_2',
        'encodings.iso2022_jp_2004',
        'encodings.iso2022_jp_3',
        'encodings.iso2022_jp_ext',
        'encodings.iso2022_kr',
        'encodings.shift_jis',
        'encodings.shift_jis_2004',
        'encodings.shift_jisx0213',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove unnecessary files (locales, translations, etc.)
a.binaries, a.datas = remove_unnecessary_files(a.binaries, a.datas)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create a single-file executable to avoid DLL path issues
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ChatGPT_Sidebar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Don't strip symbols to avoid DLL issues
    upx=False,  # Don't use UPX to avoid DLL issues
    upx_exclude=[
        # Exclude Qt WebEngine files from UPX as they don't compress well
        'Qt6WebEngineCore.dll',
        'QtWebEngineProcess.exe',
        'Qt6Network.dll',
        'Qt6Qml.dll',
        'Qt6Quick.dll',
        'vcruntime*.dll',
        'msvcp*.dll',
        'python312.dll',
    ],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,  # Enable traceback for debugging
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an icon file here if you have one
)
