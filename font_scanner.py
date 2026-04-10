"""
font_scanner.py - システムフォント検出モジュール

OS別のフォントディレクトリからTTF/OTF/TTCファイルを検出し、
フォント名とファイルパスの辞書を返却する。
"""

import os
import sys
import glob
import json
from fontTools.ttLib import TTFont, TTCollection
import unicodedata
import re


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


def normalize_font_key(name: str) -> str:
    """フォント名を比較用に正規化する。

    - 全角英数字を半角に（NFKC）
    - 大文字小文字を区別しない（casefold）
    - 空白や一部句読点を削除して前方一致比較に適する形にする
    """
    if not isinstance(name, str):
        return ""
    # 幅や表記の正規化（全角→半角など）
    s = unicodedata.normalize("NFKC", name)
    # 大文字小文字の差を吸収
    s = s.casefold()
    # 空白・ハイフン・スラッシュ等を削除（前方一致の比較用）
    s = re.sub(r"[\s\-_./,]+", "", s)
    return s


def _get_cache_path():
    """OSごとの標準キャッシュディレクトリにキャッシュファイルパスを返す。
    - macOS  : ~/Library/Caches/PDF-Font-Changer/font_cache.json
    - Windows: %LOCALAPPDATA%/PDF-Font-Changer/font_cache.json
    - Linux  : ~/.cache/PDF-Font-Changer/font_cache.json
    """
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return os.path.join(base, "PDF-Font-Changer", "font_cache.json")


def _get_dir_fingerprint(font_dirs):
    """フォントディレクトリの mtime をフィンガープリントとして返す。
    ディレクトリにフォントが追加・削除されると mtime が変わるため、
    これをキャッシュの有効性チェックに使用する。
    """
    return {d: os.path.getmtime(d) for d in font_dirs if os.path.isdir(d)}


def _load_font_cache(cache_path, fingerprint):
    """キャッシュが有効なら {表示名: パス} の辞書を返す。無効なら None を返す。"""
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("fingerprint") == fingerprint:
            return data["fonts"]
    except Exception:
        pass
    return None


def _save_font_cache(cache_path, fingerprint, fonts):
    """スキャン結果を JSON キャッシュに保存する。失敗してもサイレントに無視。"""
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"fingerprint": fingerprint, "fonts": fonts}, f, ensure_ascii=False)
    except Exception:
        pass


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


def _get_display_name(name_table):
    """
    NameRecordのリストから日本語または英語のフォント名を取得する。
    Name ID: 4 (Full Name), 1 (Family Name) を優先する。
    """
    name_candidates = {}
    for record in name_table.names:
        name_id = record.nameID
        platform_id = record.platformID
        lang_id = record.langID

        try:
            name_str = record.toUnicode()
        except UnicodeDecodeError:
            continue

        key = (name_id, platform_id, lang_id)
        name_candidates[key] = name_str

    # 優先順位リスト: (NameID, PlatformID, LangID)
    priority = [
        (4, 3, 1041), (1, 3, 1041),  # Windows, Japanese
        (4, 1, 11), (1, 1, 11),      # Macintosh, Japanese
        (4, 3, 1033), (1, 3, 1033),  # Windows, US English
        (4, 1, 0), (1, 1, 0),        # Macintosh, Roman
    ]
    for key in priority:
        if key in name_candidates:
            return name_candidates[key]

    # フォールバック: 最初に見つかったUnicode名
    for record in sorted(name_table.names, key=lambda r: r.nameID):
        try:
            return record.toUnicode()
        except UnicodeDecodeError:
            continue
    return None


def _get_font_names_from_file(filepath):
    """
    フォントファイルから適切な表示名（日本語優先）を取得する。
    TTCの場合は複数のフォント名を返す。
    """
    names = []
    try:
        if filepath.lower().endswith(".ttc"):
            ttc = TTCollection(filepath)
            for font in ttc.fonts:
                display_name = _get_display_name(font["name"])
                if display_name:
                    names.append(display_name)
        else:
            with TTFont(filepath, lazy=True) as font:
                display_name = _get_display_name(font["name"])
                if display_name:
                    names.append(display_name)
    except Exception:
        # 読み取れない場合はファイル名をフォールバック
        basename = os.path.splitext(os.path.basename(filepath))[0]
        names.append(basename)

    return list(set(names))  # 重複を除外


def scan_system_fonts():
    """
    システムにインストールされたフォントをスキャンする。
    キャッシュが有効な場合はスキャンをスキップして即座に返す。

    Returns:
        dict: {表示名: ファイルパス} の辞書
    """
    font_dirs = _get_font_directories()
    fingerprint = _get_dir_fingerprint(font_dirs)
    cache_path = _get_cache_path()

    cached = _load_font_cache(cache_path, fingerprint)
    if cached is not None:
        return cached

    # キャッシュなし or 無効: フルスキャン実行
    fonts = {}
    extensions = ("*.ttf", "*.otf", "*.ttc", "*.TTF", "*.OTF", "*.TTC")

    for font_dir in font_dirs:
        for ext in extensions:
            pattern = os.path.join(font_dir, "**", ext)
            for filepath in glob.glob(pattern, recursive=True):
                names = _get_font_names_from_file(filepath)
                for name in names:
                    if name not in fonts:
                        fonts[name] = filepath

    _save_font_cache(cache_path, fingerprint, fonts)
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
