"""
pdf_processor.py - PDF読み込み・フォントサイズ変更モジュール

PyMuPDFを使用してPDFのフォント情報を抽出し、
指定されたルールに基づいてフォント・サイズを変更する。
"""

import time
import fitz  # PyMuPDF
from font_scanner import BASE_14_FONTS


UNICODE_FALLBACK_FONT_KEYWORDS = [
    "notosanscjk",
    "notoserifcjk",
    "sourcehansans",
    "sourcehanserif",
    "hiragino",
    "yugothic",
    "yumincho",
    "msgothic",
    "meiryo",
    "ipa",
    "ipag",
    "ipam",
]


def scan_fonts(pdf_path):
    """
    PDFファイルからフォント情報を抽出する。

    Args:
        pdf_path: PDFファイルのパス

    Returns:
        list[dict]: フォント情報のリスト
            各要素: {"font": str, "size": float, "count": int}
    """
    font_map = {}  # (font, size) -> count

    doc = fitz.open(pdf_path)
    try:
        for page_idx, page in enumerate(doc):
            if page_idx % 10 == 0:
                time.sleep(0.001)  # UIフリーズ防止のためのスリープ
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:  # テキストブロックのみ
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_name = span.get("font", "Unknown")
                        size = round(span.get("size", 0), 1)
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        key = (font_name, size)
                        font_map[key] = font_map.get(key, 0) + 1
    finally:
        doc.close()

    result = []
    for (font, size), count in sorted(font_map.items()):
        result.append({"font": font, "size": size, "count": count})

    return result


def change_fonts(pdf_path, output_path, replacements, system_font_paths=None,
                 progress_callback=None, region_bbox=None, region_bboxes=None):
    """
    PDFのフォント・サイズを変更して保存する。

    Args:
        pdf_path: 入力PDFファイルのパス
        output_path: 出力PDFファイルのパス
        replacements: 変換ルールのリスト
            各要素: {"orig_font": str, "orig_size": float,
                     "new_font": str, "new_size": float}
        system_font_paths: システムフォント名→パスの辞書 (Noneならシステムフォント非使用)
        progress_callback: 進捗通知関数 (current_page, total_pages) -> None
        region_bbox: 変換対象の矩形領域 (x0, y0, x1, y1) タプル（後方互換）
        region_bboxes: 変換対象の矩形領域一覧
                  [{"page": int, "bbox": (x0, y0, x1, y1)}, ...]
                  Noneの場合は全ページ対象

    Returns:
        dict: 処理結果 {"pages": int, "changed_spans": int}
    """
    if system_font_paths is None:
        system_font_paths = {}

    # 変換ルールを高速検索用の辞書に変換
    rule_map = {}
    for r in replacements:
        key = (r["orig_font"], r["orig_size"])
        rule_map[key] = (r["new_font"], r["new_size"])
    
    print(f"[DEBUG] Font replacement rules: {len(rule_map)}")
    for key, val in list(rule_map.items())[:10]:
        print(f"[DEBUG]   {key[0]:<30} {key[1]:>6} -> {val[0]:<30} {val[1]:>6}")

    # 矩形フィルタを設定（後方互換: region_bbox）
    region_rect = None
    if region_bbox:
        region_rect = fitz.Rect(region_bbox)

    page_region_rects = {}
    global_region_rects = []
    if region_bboxes:
        for region in region_bboxes:
            bbox = region.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            if region.get("all_pages", False):
                global_region_rects.append(fitz.Rect(bbox))
                continue

            page_idx = int(region.get("page", -1))
            if page_idx < 0:
                continue
            page_region_rects.setdefault(page_idx, []).append(fitz.Rect(bbox))

    unicode_fallback = _pick_unicode_fallback_font(system_font_paths)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    total_changed = 0

    try:
        for page_idx in range(total_pages):
            if page_idx % 10 == 0:
                time.sleep(0.001)  # UIフリーズ防止のためのスリープ
            page = doc[page_idx]
            page_regions = global_region_rects + page_region_rects.get(page_idx, [])

            # 複数範囲指定時、対象ページに領域がなければスキップ
            if region_bboxes is not None and len(region_bboxes) > 0 and not page_regions:
                if progress_callback:
                    progress_callback(page_idx + 1, total_pages)
                continue

            # 1. テキスト情報を収集
            spans_to_replace = []
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_name = span.get("font", "Unknown")
                        size = round(span.get("size", 0), 1)
                        text = span.get("text", "")
                        if not text.strip():
                            continue

                        key = (font_name, size)
                        if key in rule_map:
                            # 矩形フィルタを適用
                            span_bbox = fitz.Rect(span["bbox"])
                            if region_rect and not region_rect.intersects(span_bbox):
                                continue
                            if page_regions and not any(r.intersects(span_bbox) for r in page_regions):
                                continue

                            new_font, new_size = rule_map[key]
                            spans_to_replace.append({
                                "bbox": span_bbox,
                                "text": text,
                                "origin": fitz.Point(span["origin"]),
                                "color": _parse_color(span.get("color", 0)),
                                "new_font": new_font,
                                "new_size": new_size,
                            })

            if not spans_to_replace:
                if progress_callback:
                    progress_callback(page_idx + 1, total_pages)
                continue
            
            print(f"[DEBUG] Page {page_idx + 1}: Found {len(spans_to_replace)} spans to replace")

            # 2. Redactionを追加（元テキストを削除するため）
            for sp in spans_to_replace:
                annot = page.add_redact_annot(sp["bbox"])
                annot.set_colors(stroke=None, fill=None)  # 背景色と枠線をなしに設定

            # 3. Redactionを適用（元テキストを消去、画像や図形は保持）
            page.apply_redactions(images=0, graphics=0)

            # 4. 新しいテキストを挿入
            inserted_font_aliases = set()
            for sp in spans_to_replace:
                requested_font = sp["new_font"]
                text = sp["text"]

                resolved_fontname, resolved_fontfile = _resolve_font_for_text(
                    requested_font=requested_font,
                    text=text,
                    system_font_paths=system_font_paths,
                    unicode_fallback_path=unicode_fallback,
                )

                try:
                    if resolved_fontfile:
                        font_alias = _make_embedded_font_alias(
                            requested_font=resolved_fontname,
                            fontfile=resolved_fontfile,
                        )
                        if font_alias not in inserted_font_aliases:
                            page.insert_font(fontname=font_alias, fontfile=resolved_fontfile)
                            inserted_font_aliases.add(font_alias)
                        insert_fontname = font_alias
                    else:
                        insert_fontname = resolved_fontname
                        if insert_fontname == "cjk" and "cjk" not in inserted_font_aliases:
                            page.insert_font(fontname="cjk", fontbuffer=fitz.Font("cjk").buffer)
                            inserted_font_aliases.add("cjk")

                    page.insert_text(
                        sp["origin"],
                        text,
                        fontname=insert_fontname,
                        fontsize=sp["new_size"],
                        color=sp["color"],
                    )
                except Exception as e:
                    print(f"Font embedding failed: {e}")
                    if unicode_fallback:
                        try:
                            fallback_alias = _make_embedded_font_alias("fallback", unicode_fallback)
                            if fallback_alias not in inserted_font_aliases:
                                page.insert_font(fontname=fallback_alias, fontfile=unicode_fallback)
                                inserted_font_aliases.add(fallback_alias)
                            page.insert_text(
                                sp["origin"],
                                text,
                                fontname=fallback_alias,
                                fontsize=sp["new_size"],
                                color=sp["color"],
                            )
                            continue
                        except Exception:
                            pass

                    page.insert_font(fontname="cjk", fontbuffer=fitz.Font("cjk").buffer)
                    page.insert_text(
                        sp["origin"],
                        text,
                        fontname="cjk",
                        fontsize=sp["new_size"],
                        color=sp["color"],
                    )

            total_changed += len(spans_to_replace)

            if progress_callback:
                progress_callback(page_idx + 1, total_pages)

        # 保存
        if progress_callback:
            progress_callback("saving", 0)
        doc.save(output_path, garbage=4, deflate=True)

    finally:
        doc.close()

    return {"pages": total_pages, "changed_spans": total_changed}


def _parse_color(color_int):
    """
    PyMuPDFのカラー整数値を (r, g, b) タプル（0.0〜1.0）に変換する。
    """
    if isinstance(color_int, (list, tuple)):
        return tuple(color_int)

    # 整数値の場合（0xRRGGBB形式）
    color_int = int(color_int)
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    return (r, g, b)


def _contains_non_latin_text(text):
    """ASCIIを超える文字を含むか判定する。"""
    return any(ord(char) > 0x7F for char in text)


def _pick_unicode_fallback_font(system_font_paths):
    """Unicodeコピー互換性の高いシステムフォントを優先順位で選択する。"""
    if not system_font_paths:
        return None

    lowered = [(name, path, name.lower()) for name, path in system_font_paths.items()]
    for keyword in UNICODE_FALLBACK_FONT_KEYWORDS:
        for name, path, lowered_name in lowered:
            if keyword in lowered_name:
                return path

    # キーワード一致がなければ先頭を採用
    return next(iter(system_font_paths.values()), None)


def _make_embedded_font_alias(requested_font, fontfile):
    """PDF内部で使う埋め込みフォント名（ASCIIのみ）を作る。"""
    safe_font = "".join(ch for ch in requested_font if ch.isalnum())[:24] or "font"
    safe_key = str(abs(hash(fontfile)) % 10_000_000)
    return f"f_{safe_font}_{safe_key}"


def _resolve_font_for_text(requested_font, text, system_font_paths, unicode_fallback_path):
    """テキスト内容に応じて挿入フォントとフォントファイルを解決する。"""
    built_in_fonts = set(BASE_14_FONTS) | {"cjk"}

    if requested_font in system_font_paths:
        return requested_font, system_font_paths[requested_font]

    if requested_font in built_in_fonts:
        if _contains_non_latin_text(text) and unicode_fallback_path:
            return requested_font, unicode_fallback_path
        return requested_font, None

    if unicode_fallback_path:
        return requested_font, unicode_fallback_path

    return "cjk", None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("使い方: python pdf_processor.py <PDFファイル>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"スキャン中: {path}")
    fonts = scan_fonts(path)
    print(f"\n検出フォント: {len(fonts)} 種類")
    for f in fonts:
        print(f"  {f['font']}  サイズ: {f['size']}  出現数: {f['count']}")
