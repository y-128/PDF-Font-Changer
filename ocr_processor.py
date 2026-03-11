"""
ocr_processor.py - ndlocr-lite を使用したOCRモジュール

スキャンPDFのページ画像からテキストを認識し、
テキストと位置情報（bounding box）を返す。
"""

import sys
import os
import importlib.util
import numpy as np
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET


def _get_ndlocr_site() -> Path:
    """ndlocr-lite がインストールされている site-packages ディレクトリを返す。"""
    # PyInstaller でフリーズされた場合は sys._MEIPASS 以下にデータが展開される
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    spec = importlib.util.find_spec("ocr")
    if spec and spec.origin:
        return Path(spec.origin).parent
    raise ImportError(
        "ndlocr-lite が見つかりません。"
        "pip install ndlocr-lite でインストールしてください。"
    )


def _is_available() -> bool:
    """ndlocr-lite が利用可能かどうかを確認する。"""
    try:
        _get_ndlocr_site()
        return True
    except ImportError:
        return False


# ─────────────────────────────────
#  遅延初期化済みモデルキャッシュ
# ─────────────────────────────────
_detector = None
_recognizer30 = None
_recognizer50 = None
_recognizer100 = None
_ndlocr_site: Path | None = None


def _ensure_models():
    """OCRモデルを遅延初期化する（初回呼び出し時のみロード）。"""
    global _detector, _recognizer30, _recognizer50, _recognizer100, _ndlocr_site

    if _detector is not None:
        return  # 既に初期化済み

    _ndlocr_site = _get_ndlocr_site()

    # 開発環境のみ: ndlocr-lite のパスを sys.path に追加
    # フリーズ済みアプリではモジュールはバンドル済みのため不要
    if not getattr(sys, "frozen", False):
        if not _ndlocr_site.is_dir():
            raise ImportError(f"ndlocr-lite のパスが無効です: {_ndlocr_site}")
        site_str = str(_ndlocr_site)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)

    from types import SimpleNamespace
    import ocr as ocr_mod

    args = SimpleNamespace(
        det_weights=str(_ndlocr_site / "model" / "deim-s-1024x1024.onnx"),
        det_classes=str(_ndlocr_site / "config" / "ndl.yaml"),
        det_score_threshold=0.2,
        det_conf_threshold=0.25,
        det_iou_threshold=0.2,
        rec_weights=str(
            _ndlocr_site / "model" / "parseq-ndl-16x768-100-tiny-165epoch-tegaki2.onnx"
        ),
        rec_weights30=str(
            _ndlocr_site / "model" / "parseq-ndl-16x256-30-tiny-192epoch-tegaki3.onnx"
        ),
        rec_weights50=str(
            _ndlocr_site / "model" / "parseq-ndl-16x384-50-tiny-146epoch-tegaki2.onnx"
        ),
        rec_classes=str(_ndlocr_site / "config" / "NDLmoji.yaml"),
        device="cpu",
    )

    print("[OCR] モデルをロード中...")
    _detector = ocr_mod.get_detector(args)
    _recognizer100 = ocr_mod.get_recognizer(args)
    _recognizer30 = ocr_mod.get_recognizer(args, weights_path=args.rec_weights30)
    _recognizer50 = ocr_mod.get_recognizer(args, weights_path=args.rec_weights50)
    print("[OCR] モデルのロード完了")


def run_ocr(pil_image: Image.Image) -> list[dict]:
    """
    PIL Image に対してOCRを実行し、認識されたテキストと位置情報を返す。

    Args:
        pil_image: OCR対象のPIL Image（ページ画像）

    Returns:
        list[dict]: 認識結果のリスト。各要素は以下のキーを持つ。
            - "text"  (str) : 認識されたテキスト
            - "bbox"  (tuple): 画素座標での位置 (x0, y0, x1, y1)
    """
    _ensure_models()

    site_str = str(_ndlocr_site)
    # 開発環境のみ sys.path を操作（フリーズ済みではモジュールはバンドル済み）
    if not getattr(sys, "frozen", False) and site_str not in sys.path:
        sys.path.insert(0, site_str)

    import ocr as ocr_mod
    from ndl_parser import convert_to_xml_string3
    from reading_order.xy_cut.eval import eval_xml

    img = np.array(pil_image.convert("RGB"))
    img_h, img_w = img.shape[:2]
    imgname = "page.jpg"

    # 検出
    detections, classeslist = ocr_mod.process_detector(
        _detector, imgname, img, outputpath="", issaveimg=False
    )

    # XML 構造に変換
    resultobj = [dict(), dict()]
    resultobj[0][0] = []
    for i in range(17):
        resultobj[1][i] = []
    for det in detections:
        xmin, ymin, xmax, ymax = det["box"]
        conf = det["confidence"]
        if det["class_index"] == 0:
            resultobj[0][0].append([xmin, ymin, xmax, ymax])
        resultobj[1][det["class_index"]].append([xmin, ymin, xmax, ymax, conf])

    xmlstr = convert_to_xml_string3(img_w, img_h, imgname, classeslist, resultobj)
    xmlstr = "<OCRDATASET>" + xmlstr + "</OCRDATASET>"
    try:
        root = ET.fromstring(xmlstr)
    except ET.ParseError as e:
        print(f"[OCR] XML解析エラー: {e}")
        return []
    eval_xml(root, logger=None)

    # テキスト行を収集
    alllineobj = []
    for idx, lineobj in enumerate(root.findall(".//LINE")):
        xmin = int(lineobj.get("X"))
        ymin = int(lineobj.get("Y"))
        line_w = int(lineobj.get("WIDTH"))
        line_h = int(lineobj.get("HEIGHT"))
        try:
            pred_char_cnt = float(lineobj.get("PRED_CHAR_CNT"))
        except (TypeError, ValueError):
            pred_char_cnt = 100.0
        lineimg = img[ymin : ymin + line_h, xmin : xmin + line_w, :]
        linerecogobj = ocr_mod.RecogLine(lineimg, idx, pred_char_cnt)
        alllineobj.append(linerecogobj)

    # 検出はあるが LINE 要素がない場合、検出領域を LINE として扱う
    if len(alllineobj) == 0 and len(detections) > 0:
        page_elem = root.find("PAGE")
        for idx, det in enumerate(detections):
            xmin, ymin, xmax, ymax = det["box"]
            line_w = int(xmax - xmin)
            line_h = int(ymax - ymin)
            if line_w > 0 and line_h > 0:
                line_elem = ET.SubElement(page_elem, "LINE")
                line_elem.set("TYPE", "本文")
                line_elem.set("X", str(int(xmin)))
                line_elem.set("Y", str(int(ymin)))
                line_elem.set("WIDTH", str(line_w))
                line_elem.set("HEIGHT", str(line_h))
                line_elem.set("CONF", f"{det['confidence']:0.3f}")
                pred_char_cnt = det.get("pred_char_count", 100.0)
                line_elem.set("PRED_CHAR_CNT", f"{pred_char_cnt:0.3f}")
                lineimg = img[int(ymin) : int(ymax), int(xmin) : int(xmax), :]
                linerecogobj = ocr_mod.RecogLine(lineimg, idx, pred_char_cnt)
                alllineobj.append(linerecogobj)

    if not alllineobj:
        return []

    # テキスト認識
    resultlinesall = ocr_mod.process_cascade(
        alllineobj, _recognizer30, _recognizer50, _recognizer100, is_cascade=True
    )

    # LINE要素に認識テキストをセットして結果を収集
    results = []
    line_elems = root.findall(".//LINE")
    for idx, (lineobj_elem, text) in enumerate(zip(line_elems, resultlinesall)):
        if not text.strip():
            continue
        xmin = int(lineobj_elem.get("X"))
        ymin = int(lineobj_elem.get("Y"))
        line_w = int(lineobj_elem.get("WIDTH"))
        line_h = int(lineobj_elem.get("HEIGHT"))
        results.append({
            "text": text,
            "bbox": (xmin, ymin, xmin + line_w, ymin + line_h),
        })

    return results
