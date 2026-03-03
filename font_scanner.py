"""
font_scanner.py - システムフォント検出モジュール

OS別のフォントディレクトリからTTF/OTF/TTCファイルを検出し、
フォント名とファイルパスの辞書を返却する。
"""

import os
import sys
import glob


# PDF標準フォント（常に利用可能）
BASE_14_FONTS = [
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
    "Symbol",
    "ZapfDingbats",
]


def _get_font_directories():
    """OS別のフォントディレクトリリストを返す"""
    dirs = []
    platform = sys.platform

    if platform == "darwin":  # macOS
        dirs = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            os.path.expanduser("~/Library/Fonts"),
        ]
    elif platform == "win32":  # Windows
        windir = os.environ.get("WINDIR", r"C:\Windows")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        dirs = [
            os.path.join(windir, "Fonts"),
        ]
        if localappdata:
            dirs.append(
                os.path.join(localappdata, "Microsoft", "Windows", "Fonts")
            )
    else:  # Linux / その他
        dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]

    return [d for d in dirs if os.path.isdir(d)]


def _extract_font_name(filepath):
    """ファイルパスからフォント名を推定する（ライブラリ不要）"""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # CamelCaseやハイフンをスペースに変換せず、そのまま使う
    return basename


def scan_system_fonts():
    """
    システムにインストールされたフォントをスキャンする。

    Returns:
        dict: {表示名: ファイルパス} の辞書
    """
    fonts = {}
    extensions = ("*.ttf", "*.otf", "*.ttc", "*.TTF", "*.OTF", "*.TTC")

    for font_dir in _get_font_directories():
        for ext in extensions:
            pattern = os.path.join(font_dir, "**", ext)
            for filepath in glob.glob(pattern, recursive=True):
                name = _extract_font_name(filepath)
                if name not in fonts:
                    fonts[name] = filepath

    return fonts


def get_all_fonts():
    """
    PDF標準フォント + システムフォントの統合リストを返す。

    Returns:
        tuple: (all_font_names: list[str], system_font_paths: dict[str, str])
            - all_font_names: 全フォント名のソート済みリスト
            - system_font_paths: システムフォント名→ファイルパスの辞書
    """
    system_fonts = scan_system_fonts()

    all_names = sorted(set(BASE_14_FONTS) | set(system_fonts.keys()))

    return all_names, system_fonts


if __name__ == "__main__":
    print("=== システムフォント検出テスト ===")
    names, paths = get_all_fonts()
    print(f"\n検出フォント数: {len(names)}")

    print("\n--- PDF標準フォント ---")
    for f in BASE_14_FONTS:
        print(f"  {f}")

    print(f"\n--- システムフォント (上位20件) ---")
    system_names = sorted(paths.keys())
    for name in system_names[:20]:
        print(f"  {name}: {paths[name]}")
    if len(system_names) > 20:
        print(f"  ... 他 {len(system_names) - 20} 件")
