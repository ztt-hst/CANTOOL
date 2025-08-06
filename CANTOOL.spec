# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 数据文件
datas = [
    ('ControlCAN.dll', '.'),
    ('can_protocol_config.py', '.'),
    ('language_manager.py', '.'),
    ('BQC.ico', '.'),
    # 添加语言文件
    ('languages/chinese.json', 'languages'),
    ('languages/english.json', 'languages'),
]

# 隐藏导入
hiddenimports = [
    'ctypes',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'threading',
    'time',
    'datetime',
    'json',
    'struct',
    'can_protocol_config',
    'language_manager',
]

# 分析
a = Analysis(
    ['can_host_computer.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 打包
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CAN_TOOL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='BQC.ico' if os.path.exists('BQC.ico') else None,  # 修正图标路径
) 