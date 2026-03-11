"""PDF Font Changer - メインGUIアプリケーション

PDFファイルのフォントサイズを一括変更するデスクトップアプリケーション。
Windows / Linux / macOS で完全オフラインで動作する。
"""

import os
import io
import sys
import threading
import queue
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import fitz

from pdf_processor import scan_fonts, change_fonts
from font_scanner import get_all_fonts, BASE_14_FONTS
import ocr_processor

# バージョン情報（セマンティック バージョニング）
__version__ = "1.1.1"


def get_build_version():
    """ビルドバージョンを取得"""
    return __version__


class PDFFontChangerApp:
    """PDFフォントサイズ変更アプリケーション"""

    APP_TITLE = "PDF Font Changer"
    WINDOW_MIN_SIZE = (600, 500)

    def __init__(self, root):
        self.root = root
        self.root.title(self.APP_TITLE)

        # 解像度に応じたスケーリング係数を取得
        self.scale_factor = 1.0
        try:
            if sys.platform == "win32":
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            # tk scaling が使えるなら使う
            self.scale_factor = self.root.tk.call('tk', 'scaling')
        except (ImportError, tk.TclError):
            try:
                # 代替手段 (ウィンドウ表示後でないと正確でない場合がある)
                self.scale_factor = self.root.winfo_fpixels('1i') / 72.0
            except tk.TclError:
                pass # これも失敗したら 1.0 のまま
        
        # macOSでのスケールが大きすぎる場合があるので調整
        if sys.platform == "darwin" and self.scale_factor > 1.5:
            self.scale_factor /= 1.5

        # スケーリングを適用したサイズ計算
        min_width = int(self.WINDOW_MIN_SIZE[0] * self.scale_factor)
        min_height = int(self.WINDOW_MIN_SIZE[1] * self.scale_factor)
        default_width = int(800 * self.scale_factor)
        default_height = int(600 * self.scale_factor)
        
        self.root.minsize(min_width, min_height)
        self.root.geometry(f"{default_width}x{default_height}")

        # 状態変数
        self.pdf_path = None
        self.font_list = []  # [{font, size, count}, ...]
        self.all_font_names = []
        self.system_font_paths = {}
        self.progress_queue = queue.Queue()
        self.is_processing = False

        # OCR関連
        self.use_ocr_var = tk.BooleanVar(value=False)
        self.ocr_results = {}  # {page_idx: [{"text": str, "bbox": (x0,y0,x1,y1)}, ...]}

        # PDF プレビュー関連
        self.pdf_doc = None  # PyMuPDF ドキュメント
        self.current_page = 0  # 現在表示中のページ番号
        self.region_bboxes = []  # [{"page": int, "bbox": (x0, y0, x1, y1)}, ...]
        self.canvas_image = None  # Canvas 用の PIL Image
        self.is_selecting = False  # 矩形選択中フラグ
        self.selection_start = None  # 矩形選択の開始座標
        self.page_zoom = 0.5  # PDF表示のズーム倍率
        self.preview_window = None
        self.preview_canvas = None
        self.page_label = None
        self.region_label = None
        self.canvas_photo = None
        self.display_scale = 1.0
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.region_tree = None

        # スタイル設定
        self._setup_styles()

        # UIを構築
        self._build_ui()

        # システムフォントをバックグラウンドで読み込み
        self._load_fonts_async()

        # 進捗チェックタイマー
        self.root.after(100, self._check_progress)

    # ─────────────────────────────────
    #  スタイル設定
    # ─────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        
        # スケーリングされた値を計算するヘルパー
        def scale(value):
            return int(value * self.scale_factor)

        # フォントサイズはスケーリングせず、Tkinterの自動スケーリングに任せる
        # パディングや高さなど、ジオメトリ関連は手動でスケーリング
        style.configure("Title.TLabel", font=("", 14, "bold"))
        style.configure("Status.TLabel", font=("", 10))
        style.configure(
            "Action.TButton",
            font=("", 11),
            padding=(scale(12), scale(6))
        )
        style.configure(
            "Treeview",
            font=("", 11),
            rowheight=scale(26),
        )
        style.configure("Treeview.Heading", font=("", 11, "bold"))
        
        # Checkbuttonのスタイル設定
        style.configure("TCheckbutton", font=("", 10))

        # Progressbarのスタイル設定（進捗部分を青色に）
        style.configure(
            "Horizontal.TProgressbar",
            background="blue",
            lightcolor="blue",
            darkcolor="blue",
        )

    # ─────────────────────────────────
    #  UI構築
    # ─────────────────────────────────
    def _build_ui(self):
        # メニューバー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._show_about)
        
        # メインコンテナ
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ── ツールバー ──
        toolbar = ttk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(
            toolbar, text="📂 PDFを開く", command=self._open_pdf,
            style="Action.TButton"
        ).pack(side=tk.LEFT)

        ttk.Checkbutton(
            toolbar, text="OCR（スキャンPDF）",
            variable=self.use_ocr_var,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.path_label = ttk.Label(
            toolbar, text="ファイルが選択されていません",
            style="Status.TLabel"
        )
        self.path_label.pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True)

        # ── コンテンツ領域（左右分割）──
        content = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 左: フォント一覧
        left_frame = ttk.LabelFrame(content, text="フォント一覧", padding=8)
        content.add(left_frame, weight=3)
        self._build_font_list(left_frame)

        # 右: 設定パネル
        right_frame = ttk.LabelFrame(content, text="フォント変更設定", padding=12)
        content.add(right_frame, weight=2)
        self._build_settings_panel(right_frame)

        # ── ステータスバー ──
        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(
            status_frame, mode="determinate", length=300
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.status_label = ttk.Label(
            status_frame, text="準備完了", style="Status.TLabel"
        )
        self.status_label.pack(side=tk.RIGHT)

    def _build_pdf_preview(self, parent):
        """PDFプレビューキャンバスを構築"""
        # Canvas
        self.preview_canvas = tk.Canvas(
            parent, bg="#2b2b2b", height=200, cursor="crosshair"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", self._on_preview_canvas_resize)

        # マウスイベント
        self.preview_canvas.bind("<Button-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # ページナビゲーション
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(
            nav_frame, text="◀ 前ページ", command=self._prev_page, width=10
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.page_label = ttk.Label(nav_frame, text="ページ: -/-")
        self.page_label.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            nav_frame, text="次ページ ▶", command=self._next_page, width=10
        ).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Button(
            nav_frame, text="🔄 リセット", command=self._reset_region, width=10
        ).pack(side=tk.RIGHT, padx=(4, 0))

        self.region_label = ttk.Label(
            nav_frame, text="領域: なし", foreground="blue"
        )
        self.region_label.pack(side=tk.RIGHT, padx=(4, 0))

    def _open_preview_window(self):
        """プレビュー専用ウィンドウを開く"""
        if not self.pdf_doc:
            messagebox.showwarning("未選択", "先にPDFファイルを開いてください。")
            return

        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.lift()
            self.preview_window.focus_force()
            self._render_pdf_page()
            return

        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("置換範囲選択（ドラッグで領域指定）")
        self.preview_window.geometry("900x700")
        self.preview_window.minsize(700, 500)

        preview_frame = ttk.Frame(self.preview_window, padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        self._build_pdf_preview(preview_frame)

        self._update_region_label()

        self.preview_window.protocol("WM_DELETE_WINDOW", self._close_preview_window)
        self._render_pdf_page()

    def _on_preview_canvas_resize(self, event):
        """プレビューCanvasのリサイズ時に再描画する"""
        if self.canvas_image:
            self._display_canvas_image()

    def _close_preview_window(self):
        """プレビュー専用ウィンドウを閉じる"""
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_canvas = None
        self.page_label = None
        self.region_label = None
        self.canvas_photo = None

    def _prev_page(self):
        """前ページを表示"""
        if self.pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self._render_pdf_page()

    def _next_page(self):
        """次ページを表示"""
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self._render_pdf_page()

    def _render_pdf_page(self):
        """現在のページをレンダリング"""
        if not self.pdf_doc:
            return

        page = self.pdf_doc[self.current_page]
        # PDFページを画像に変換（ズーム係数を使用）
        mat = fitz.Matrix(self.page_zoom, self.page_zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("ppm")
        self.canvas_image = Image.open(io.BytesIO(img_data))

        # Canvas に表示（プレビューウィンドウが開いている時のみ）
        if self.preview_canvas and self.preview_canvas.winfo_exists():
            self._display_canvas_image()

        # ページ情報を更新
        if self.page_label and self.page_label.winfo_exists():
            self.page_label.config(
                text=f"ページ: {self.current_page + 1}/{len(self.pdf_doc)}"
            )
        self._update_region_label()

    def _display_canvas_image(self):
        """Canvas に画像を表示"""
        if not self.canvas_image or not self.preview_canvas or not self.preview_canvas.winfo_exists():
            return

        # Canvas のサイズを調整
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas のサイズが確定していない場合は遅延実行
            self.preview_canvas.after(100, self._display_canvas_image)
            return

        # アスペクト比を維持してページ全体を収める
        img_width, img_height = self.canvas_image.size
        if img_width <= 0 or img_height <= 0:
            return

        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        self.display_scale = min(scale_x, scale_y)

        draw_width = max(1, int(img_width * self.display_scale))
        draw_height = max(1, int(img_height * self.display_scale))

        self.display_offset_x = (canvas_width - draw_width) // 2
        self.display_offset_y = (canvas_height - draw_height) // 2

        img_resized = self.canvas_image.resize((draw_width, draw_height), Image.Resampling.LANCZOS)

        # Canvas をクリア
        self.preview_canvas.delete("all")

        # Canvas に描画
        self.canvas_photo = ImageTk.PhotoImage(img_resized)
        self.preview_canvas.create_image(
            self.display_offset_x, self.display_offset_y,
            image=self.canvas_photo, anchor="nw"
        )

        # ページ境界線（背景との境目を見やすくする）
        self.preview_canvas.create_rectangle(
            self.display_offset_x,
            self.display_offset_y,
            self.display_offset_x + draw_width,
            self.display_offset_y + draw_height,
            outline="#d0d0d0",
            width=1,
        )

        # 選択矩形がある場合は描画
        self._draw_region_rects()

    def _draw_region_rects(self):
        """現在ページの選択矩形を Canvas に描画"""
        if not self.preview_canvas or not self.preview_canvas.winfo_exists():
            return

        page_regions = [
            r for r in self.region_bboxes
            if r.get("all_pages", False) or int(r["page"]) == self.current_page
        ]

        for region in page_regions:
            x0, y0, x1, y1 = region["bbox"]
            canvas_x0 = x0 * self.page_zoom * self.display_scale + self.display_offset_x
            canvas_y0 = y0 * self.page_zoom * self.display_scale + self.display_offset_y
            canvas_x1 = x1 * self.page_zoom * self.display_scale + self.display_offset_x
            canvas_y1 = y1 * self.page_zoom * self.display_scale + self.display_offset_y
            self.preview_canvas.create_rectangle(
                canvas_x0, canvas_y0, canvas_x1, canvas_y1,
                outline="red", width=2, fill=""
            )

    def _on_canvas_press(self, event):
        """Canvas マウスダウン"""
        self.is_selecting = True
        self.selection_start = (event.x, event.y)

    def _on_canvas_drag(self, event):
        """Canvas マウスドラッグ"""
        if not self.is_selecting or not self.selection_start:
            return

        # 矩形を描画
        self.preview_canvas.delete("selection_rect")
        x0, y0 = self.selection_start
        x1, y1 = event.x, event.y

        # 画像外はクランプ
        min_x = self.display_offset_x
        min_y = self.display_offset_y
        max_x = self.display_offset_x + int(self.canvas_image.size[0] * self.display_scale)
        max_y = self.display_offset_y + int(self.canvas_image.size[1] * self.display_scale)
        x0 = min(max(x0, min_x), max_x)
        y0 = min(max(y0, min_y), max_y)
        x1 = min(max(x1, min_x), max_x)
        y1 = min(max(y1, min_y), max_y)

        self.preview_canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="blue", width=2, fill="", tags="selection_rect"
        )

    def _on_canvas_release(self, event):
        """Canvas マウスリリース"""
        if not self.is_selecting or not self.selection_start:
            return

        self.is_selecting = False

        x0, y0 = self.selection_start
        x1, y1 = event.x, event.y

        # 座標を正規化
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)

        if x1 - x0 > 5 and y1 - y0 > 5:  # 最小サイズチェック
            # Canvas座標（レターボックス込み）をPDF座標に変換
            if self.canvas_image and self.display_scale > 0:
                img_x0 = (x0 - self.display_offset_x) / self.display_scale
                img_y0 = (y0 - self.display_offset_y) / self.display_scale
                img_x1 = (x1 - self.display_offset_x) / self.display_scale
                img_y1 = (y1 - self.display_offset_y) / self.display_scale

                pdf_x0 = img_x0 / self.page_zoom
                pdf_y0 = img_y0 / self.page_zoom
                pdf_x1 = img_x1 / self.page_zoom
                pdf_y1 = img_y1 / self.page_zoom

                page_rect = self.pdf_doc[self.current_page].rect
                pdf_x0 = min(max(pdf_x0, 0), page_rect.width)
                pdf_y0 = min(max(pdf_y0, 0), page_rect.height)
                pdf_x1 = min(max(pdf_x1, 0), page_rect.width)
                pdf_y1 = min(max(pdf_y1, 0), page_rect.height)

                self.region_bboxes.append({
                    "page": self.current_page,
                    "bbox": (pdf_x0, pdf_y0, pdf_x1, pdf_y1),
                    "all_pages": False,
                })
                self._refresh_region_tree()
                self._update_region_label()

        self.selection_start = None
        self._display_canvas_image()

    def _reset_region(self):
        """選択矩形を全リセット"""
        self.region_bboxes.clear()
        self._refresh_region_tree()
        self._update_region_label()
        if self.preview_canvas and self.preview_canvas.winfo_exists():
            self._display_canvas_image()

    def _update_region_label(self):
        """置換範囲ラベルを更新"""
        if not self.region_label or not self.region_label.winfo_exists():
            return

        total_count = len(self.region_bboxes)
        page_count = len([
            r for r in self.region_bboxes
            if r.get("all_pages", False) or int(r["page"]) == self.current_page
        ])

        if total_count == 0:
            self.region_label.config(text="領域: なし")
        else:
            self.region_label.config(text=f"領域: {total_count} 件（このページ {page_count} 件）")

    # ─────────────────────────────────
    #  フォント一覧
    # ─────────────────────────────────

    def _build_font_list(self, parent):

        """フォント一覧ツリービューを構築"""
        # 検索バー
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_font_list)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # ツリービュー
        columns = ("font", "size", "count")
        self.tree = ttk.Treeview(
            parent, columns=columns, show="headings",
            selectmode="extended", height=10
        )
        self.tree.heading("font", text="フォント名", anchor=tk.W)
        self.tree.heading("size", text="サイズ", anchor=tk.CENTER)
        self.tree.heading("count", text="出現数", anchor=tk.CENTER)

        self.tree.column("font", width=250, minwidth=150)
        self.tree.column("size", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column("count", width=80, minwidth=60, anchor=tk.CENTER)

        # スクロールバー
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 選択イベント
        self.tree.bind("<<TreeviewSelect>>", self._on_font_select)

        # 全選択ボタン
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(
            btn_frame, text="全選択", command=self._select_all_fonts
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            btn_frame, text="選択解除", command=self._deselect_all_fonts
        ).pack(side=tk.LEFT)

        ttk.Button(
            parent, text="🖼 置換範囲選択", command=self._open_preview_window,
            style="Action.TButton"
        ).pack(fill=tk.X, pady=(6, 0))

    def _build_region_panel(self, parent):
        """置換範囲一覧パネルを構築"""
        columns = ("page", "x0", "y0", "x1", "y1")
        self.region_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=11,
        )
        self.region_tree.heading("page", text="ページ", anchor=tk.CENTER)
        self.region_tree.heading("x0", text="x0", anchor=tk.CENTER)
        self.region_tree.heading("y0", text="y0", anchor=tk.CENTER)
        self.region_tree.heading("x1", text="x1", anchor=tk.CENTER)
        self.region_tree.heading("y1", text="y1", anchor=tk.CENTER)

        self.region_tree.column("page", width=60, minwidth=50, anchor=tk.CENTER)
        self.region_tree.column("x0", width=70, minwidth=60, anchor=tk.CENTER)
        self.region_tree.column("y0", width=70, minwidth=60, anchor=tk.CENTER)
        self.region_tree.column("x1", width=70, minwidth=60, anchor=tk.CENTER)
        self.region_tree.column("y1", width=70, minwidth=60, anchor=tk.CENTER)
        self.region_tree.bind("<Button-1>", self._on_region_tree_click, add="+")

        region_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.region_tree.yview)
        self.region_tree.configure(yscrollcommand=region_scroll.set)

        self.region_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        region_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            btn_frame, text="選択削除", command=self._remove_selected_regions
        ).pack(fill=tk.X, pady=(0, 4))

        ttk.Button(
            btn_frame, text="全削除", command=self._clear_all_regions
        ).pack(fill=tk.X)

    def _refresh_region_tree(self):
        """置換範囲一覧を更新"""
        if not self.region_tree:
            return

        self.region_tree.delete(*self.region_tree.get_children())
        for idx, region in enumerate(self.region_bboxes):
            x0, y0, x1, y1 = region["bbox"]
            all_pages = region.get("all_pages", False)
            page_text = "☑ 全" if all_pages else f"☐ {region['page'] + 1}"
            self.region_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(page_text, int(x0), int(y0), int(x1), int(y1)),
            )

    def _on_region_tree_click(self, event):
        """置換範囲一覧のページ列クリックで全ページ適用を切替"""
        if not self.region_tree:
            return

        region = self.region_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.region_tree.identify_column(event.x)
        row_id = self.region_tree.identify_row(event.y)
        if column != "#1" or not row_id:
            return

        index = int(row_id)
        if 0 <= index < len(self.region_bboxes):
            current = self.region_bboxes[index].get("all_pages", False)
            self.region_bboxes[index]["all_pages"] = not current
            self._refresh_region_tree()
            self._update_region_label()
            if self.preview_canvas and self.preview_canvas.winfo_exists():
                self._display_canvas_image()
        return "break"

    def _remove_selected_regions(self):
        """選択中の置換範囲を削除"""
        if not self.region_tree:
            return
        selected = self.region_tree.selection()
        if not selected:
            return

        indices = sorted((int(item_id) for item_id in selected), reverse=True)
        for index in indices:
            if 0 <= index < len(self.region_bboxes):
                self.region_bboxes.pop(index)

        self._refresh_region_tree()
        self._update_region_label()
        if self.preview_canvas and self.preview_canvas.winfo_exists():
            self._display_canvas_image()

    def _clear_all_regions(self):
        """置換範囲を全削除"""
        self.region_bboxes.clear()
        self._refresh_region_tree()
        self._update_region_label()
        if self.preview_canvas and self.preview_canvas.winfo_exists():
            self._display_canvas_image()

    def _build_settings_panel(self, parent):
        """設定パネルを構築"""
        top_row = ttk.Frame(parent)
        top_row.pack(fill=tk.X, pady=(0, 12))
        top_row.columnconfigure(0, weight=1, uniform="top_cols")
        top_row.columnconfigure(1, weight=1, uniform="top_cols")

        left_settings = ttk.Frame(top_row)
        left_settings.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        region_panel = ttk.LabelFrame(top_row, text="置換範囲指定一覧 ※ ページ列のチェックで全ページ適用", padding=8)
        region_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._build_region_panel(region_panel)

        # 現在のフォント情報
        info_frame = ttk.LabelFrame(left_settings, text="選択中のフォント", padding=8)
        info_frame.pack(fill=tk.X, pady=(0, 12))

        self.selected_info_label = ttk.Label(
            info_frame, text="フォントを選択してください",
            wraplength=300
        )
        self.selected_info_label.pack(fill=tk.X)

        # 新しいフォント設定
        new_frame = ttk.LabelFrame(left_settings, text="新しい設定", padding=8)
        new_frame.pack(fill=tk.X, pady=(0, 12))

        # 新フォント
        ttk.Label(new_frame, text="新しいフォント:").pack(anchor=tk.W, pady=(0, 4))
        self.new_font_var = tk.StringVar(value="Helvetica")
        self.font_combo = ttk.Combobox(
            new_frame, textvariable=self.new_font_var,
            state="readonly", height=10
        )
        self.font_combo.pack(fill=tk.X, pady=(0, 10))

        # フォントフィルタ
        filter_frame = ttk.Frame(new_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="フォント検索:").pack(side=tk.LEFT)
        self.font_filter_var = tk.StringVar()
        self.font_filter_var.trace_add("write", self._filter_font_combo)
        font_filter_entry = ttk.Entry(
            filter_frame, textvariable=self.font_filter_var, width=20
        )
        font_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # 新サイズ
        ttk.Label(new_frame, text="新しいサイズ (pt):").pack(anchor=tk.W, pady=(0, 4))
        self.new_size_var = tk.StringVar(value="12.0")
        size_frame = ttk.Frame(new_frame)
        size_frame.pack(fill=tk.X, pady=(0, 4))

        self.size_spinbox = ttk.Spinbox(
            size_frame, from_=1, to=200, increment=0.5,
            textvariable=self.new_size_var, width=10
        )
        self.size_spinbox.pack(side=tk.LEFT)

        ttk.Label(size_frame, text=" pt").pack(side=tk.LEFT)

        # サイズ変更モード
        self.size_mode_var = tk.StringVar(value="absolute")
        mode_frame = ttk.LabelFrame(left_settings, text="サイズ変更モード", padding=8)
        mode_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Radiobutton(
            mode_frame, text="絶対値 (指定サイズに変更)",
            variable=self.size_mode_var, value="absolute"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            mode_frame, text="相対値 (現在のサイズに加算)",
            variable=self.size_mode_var, value="relative"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            mode_frame, text="倍率 (現在のサイズに乗算)",
            variable=self.size_mode_var, value="scale"
        ).pack(anchor=tk.W)

        # アクションボタン (Add Task)
        btn_frame = ttk.Frame(left_settings)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        self.add_task_btn = ttk.Button(
            btn_frame, text="➕ タスクに追加",
            command=self._add_tasks,
            style="Action.TButton"
        )
        self.add_task_btn.pack(fill=tk.X)

        # ── タスクリスト領域 ──
        task_frame = ttk.LabelFrame(parent, text="変更タスク一覧", padding=8)
        task_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        task_tree_frame = ttk.Frame(task_frame)
        task_tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("orig_font", "orig_size", "new_font", "new_size")
        self.task_tree = ttk.Treeview(
            task_tree_frame, columns=columns, show="headings",
            selectmode="extended", height=3
        )
        self.task_tree.heading("orig_font", text="対象フォント", anchor=tk.W)
        self.task_tree.heading("orig_size", text="対象サイズ", anchor=tk.CENTER)
        self.task_tree.heading("new_font", text="新フォント", anchor=tk.W)
        self.task_tree.heading("new_size", text="新サイズ", anchor=tk.CENTER)
        
        self.task_tree.column("orig_font", width=120, minwidth=80)
        self.task_tree.column("orig_size", width=70, minwidth=50, anchor=tk.CENTER)
        self.task_tree.column("new_font", width=120, minwidth=80)
        self.task_tree.column("new_size", width=70, minwidth=50, anchor=tk.CENTER)

        task_scroll = ttk.Scrollbar(task_tree_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=task_scroll.set)
        
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        task_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # タスク操作ボタン
        task_btn_frame = ttk.Frame(task_frame)
        task_btn_frame.pack(fill=tk.X, pady=(4, 0))
        
        ttk.Button(
            task_btn_frame, text="選択削除", command=self._remove_selected_tasks
        ).pack(side=tk.LEFT, padx=(0, 4))
        
        ttk.Button(
            task_btn_frame, text="全クリア", command=self._clear_all_tasks
        ).pack(side=tk.LEFT)

        # 適用して保存ボタン
        self.apply_btn = ttk.Button(
            task_frame, text="✅ タスクを適用して保存",
            command=self._apply_changes,
            style="Action.TButton"
        )
        self.apply_btn.pack(fill=tk.X, pady=(8, 0))

    # ─────────────────────────────────
    #  フォント読み込み
    # ─────────────────────────────────
    def _load_fonts_async(self):
        """システムフォントをバックグラウンドで読み込む"""
        self.status_label.config(text="システムフォントを読み込み中...")

        def _load():
            names, paths = get_all_fonts()
            self.root.after(0, lambda: self._on_fonts_loaded(names, paths))

        threading.Thread(target=_load, daemon=True).start()

    def _on_fonts_loaded(self, names, paths):
        self.all_font_names = names
        self.system_font_paths = paths
        self.font_combo["values"] = names
        self.status_label.config(
            text=f"準備完了 — {len(names)} フォント検出"
        )

    # ─────────────────────────────────
    #  PDF読み込み
    # ─────────────────────────────────
    def _open_pdf(self):
        if self.is_processing:
            messagebox.showwarning("処理中", "PDF処理が完了するまでお待ちください。")
            return

        path = filedialog.askopenfilename(
            title="PDFファイルを選択",
            filetypes=[("PDF ファイル", "*.pdf"), ("すべてのファイル", "*.*")]
        )
        if not path:
            return

        self.pdf_path = path
        self.path_label.config(text=os.path.basename(path))

        # PDFドキュメントを開く
        try:
            if self.pdf_doc:
                self.pdf_doc.close()
            self.pdf_doc = fitz.open(path)
            self.current_page = 0
            self.region_bboxes.clear()
            self._refresh_region_tree()
            self._update_region_label()
            if self.preview_window and self.preview_window.winfo_exists():
                self._render_pdf_page()
        except Exception as e:
            messagebox.showerror("エラー", f"PDFが開けません:\n{e}")
            return

        # バックグラウンドでフォントスキャン開始
        use_ocr = self.use_ocr_var.get()
        pdf_path_local = path

        self.is_processing = True
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(15)
        self.status_label.config(text="PDFを解析中...")

        def _scan():
            try:
                fonts = scan_fonts(pdf_path_local)
                self.root.after(0, lambda: self._on_fonts_scanned(fonts, use_ocr, pdf_path_local))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: self._on_scan_error(msg))

        threading.Thread(target=_scan, daemon=True).start()

    def _on_fonts_scanned(self, fonts, use_ocr, pdf_path):
        """フォントスキャン完了後の処理（メインスレッドで実行）"""
        if use_ocr and len(fonts) > 0:
            answer = messagebox.askyesno(
                "フォント検出",
                f"このPDFには {len(fonts)} 種類の埋め込みフォントが検出されました。\n"
                "テキストデータを持つPDFの可能性があります。\n\n"
                "このままOCRで続行しますか？\n"
                "（「いいえ」を選ぶとOCRをスキップして通常モードで開きます）",
                parent=self.root
            )
            if not answer:
                self._on_scan_done(fonts)
                return

        if use_ocr:
            self._start_ocr(fonts, pdf_path)
        else:
            self._on_scan_done(fonts)

    def _start_ocr(self, fonts, pdf_path):
        """OCR処理をバックグラウンドで実行"""
        def _run_ocr():
            ocr_results = {}
            try:
                doc_ocr = fitz.open(pdf_path)
                try:
                    page_count = len(doc_ocr)
                    print(f"[OCR] OCRを実行中... 全{page_count}ページ")
                    for page_idx in range(page_count):
                        self.root.after(
                            0,
                            lambda i=page_idx, n=page_count: self.status_label.config(
                                text=f"OCR処理中... {i + 1}/{n} ページ"
                            ),
                        )
                        try:
                            page = doc_ocr[page_idx]
                            ocr_zoom = 2.0
                            mat = fitz.Matrix(ocr_zoom, ocr_zoom)
                            pix = page.get_pixmap(matrix=mat)
                            pil_img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                            lines = ocr_processor.run_ocr(pil_img)
                            pdf_lines = []
                            for ln in lines:
                                x0, y0, x1, y1 = ln["bbox"]
                                bbox_h = y1 - y0
                                bbox_w = x1 - x0
                                size_pt = round(min(bbox_h, bbox_w) / ocr_zoom, 1)
                                pdf_lines.append({
                                    "text": ln["text"],
                                    "bbox": (
                                        x0 / ocr_zoom,
                                        y0 / ocr_zoom,
                                        x1 / ocr_zoom,
                                        y1 / ocr_zoom,
                                    ),
                                    "size_pt": size_pt,
                                })
                            if pdf_lines:
                                ocr_results[page_idx] = pdf_lines
                            print(f"[OCR] ページ {page_idx + 1}/{page_count}: {len(pdf_lines)} 行を検出")
                        except Exception as e:
                            import traceback
                            print(f"[OCR] ページ {page_idx + 1} のOCRに失敗: {e}")
                            traceback.print_exc()
                finally:
                    doc_ocr.close()
            except Exception as e:
                import traceback
                print(f"[OCR] OCR処理でエラー: {e}")
                traceback.print_exc()
            self.root.after(0, lambda: self._on_scan_done(fonts, ocr_results))

        threading.Thread(target=_run_ocr, daemon=True).start()

    def _on_scan_done(self, fonts, ocr_results=None):
        # ステータスバーを停止
        self.is_processing = False
        self.progress_bar.config(mode="determinate")
        self.progress_bar.stop()
        self.progress_bar["value"] = 0

        self.ocr_results = ocr_results or {}
        is_scanned = len(fonts) == 0

        # OCR結果がある場合、サイズ別に「OCR検出」エントリをフォントリストに追加
        display_fonts = list(fonts)
        if self.ocr_results:
            # size_pt ごとにグループ化
            size_counts: dict[float, int] = {}
            for page_lines in self.ocr_results.values():
                for ln in page_lines:
                    sp = ln.get("size_pt", 0.0)
                    size_counts[sp] = size_counts.get(sp, 0) + 1
            for sp in sorted(size_counts):
                display_fonts.append({"font": "OCR検出", "size": sp, "count": size_counts[sp]})

        self.font_list = display_fonts
        self.is_scanned_pdf = is_scanned
        self._populate_tree(display_fonts)
        print(f"[DEBUG] PDF scan completed - Found {len(fonts)} font types:")
        for f in fonts[:10]:
            print(f"[DEBUG]   Font: {f['font']:<30} Size: {f['size']:>6} Count: {f['count']:>4}")
        if len(fonts) > 10:
            print(f"[DEBUG]   ... and {len(fonts) - 10} more")
        if self.ocr_results:
            total = sum(len(v) for v in self.ocr_results.values())
            print(f"[DEBUG]   OCR: {total} 行を認識")
        self.status_label.config(
            text=f"解析完了 — {len(fonts)} 種類のフォント/サイズを検出"
            + (f"、OCR {sum(len(v) for v in self.ocr_results.values())} 行" if self.ocr_results else "")
        )

        # スキャンPDFかつOCR未使用の場合は案内を表示
        if is_scanned and not self.ocr_results:
            messagebox.showwarning(
                "スキャンPDF検出",
                "このPDFは画像のみで構成されています。\n\n"
                "ツールバーの「OCR（スキャンPDF）」チェックボックスを\n"
                "ONにしてから再度PDFを開いてください。"
            )

    def _on_scan_error(self, error_msg):
        self.is_processing = False
        self.progress_bar.config(mode="determinate")
        self.progress_bar.stop()
        self.progress_bar["value"] = 0
        self.status_label.config(text="エラーが発生しました")
        messagebox.showerror("エラー", f"PDF解析に失敗しました:\n{error_msg}")

    def _populate_tree(self, fonts):
        """ツリービューにフォントデータを挿入"""
        self.tree.delete(*self.tree.get_children())
        for i, f in enumerate(fonts):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "", tk.END,
                values=(f["font"], f["size"], f["count"]),
                tags=(tag,)
            )
        self.tree.tag_configure("even", background="#f8f8f8")
        self.tree.tag_configure("odd", background="#ffffff")

    # ─────────────────────────────────
    #  フィルタ・選択
    # ─────────────────────────────────
    def _filter_font_list(self, *args):
        """フォント一覧を検索でフィルタ"""
        query = self.search_var.get().lower()
        if not query:
            self._populate_tree(self.font_list)
            return

        filtered = [
            f for f in self.font_list
            if query in f["font"].lower()
        ]
        self._populate_tree(filtered)

    def _filter_font_combo(self, *args):
        """フォント選択コンボボックスをフィルタ"""
        query = self.font_filter_var.get().lower()
        if not query:
            self.font_combo["values"] = self.all_font_names
            return

        filtered = [n for n in self.all_font_names if query in n.lower()]
        self.font_combo["values"] = filtered
        if filtered:
            self.font_combo.set(filtered[0])

    def _on_font_select(self, event):
        """フォント選択時の処理"""
        selected = self.tree.selection()
        if not selected:
            self.selected_info_label.config(text="フォントを選択してください")
            return

        if len(selected) == 1:
            values = self.tree.item(selected[0], "values")
            font_name, size, count = values
            self.selected_info_label.config(
                text=f"{font_name}\nサイズ: {size} pt  |  出現数: {count}"
            )
            # 現在のサイズを自動入力
            self.new_size_var.set(str(size))
        else:
            sizes = set()
            for item in selected:
                values = self.tree.item(item, "values")
                sizes.add(values[1])
            self.selected_info_label.config(
                text=f"{len(selected)} 件選択中\nサイズ: {', '.join(sorted(sizes))} pt"
            )

    def _select_all_fonts(self):
        items = self.tree.get_children()
        self.tree.selection_set(items)

    def _deselect_all_fonts(self):
        self.tree.selection_remove(self.tree.selection())

    # ─────────────────────────────────
    #  タスク管理・変更適用
    # ─────────────────────────────────
    def _add_tasks(self):
        if self.is_processing:
            messagebox.showwarning("処理中", "PDF処理が完了するまでお待ちください。")
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("未選択", "変更する元のフォントを選択してください。")
            return

        new_font = self.new_font_var.get()
        if not new_font:
            messagebox.showwarning("未入力", "新しいフォントを選択してください。")
            return

        try:
            new_size_value = float(self.new_size_var.get())
        except ValueError:
            messagebox.showwarning("不正な値", "サイズには数値を入力してください。")
            return

        if new_size_value <= 0 and self.size_mode_var.get() == "absolute":
            messagebox.showwarning("不正な値", "サイズは0より大きい値を指定してください。")
            return

        size_mode = self.size_mode_var.get()
        
        for item in selected:
            values = self.tree.item(item, "values")
            orig_font = values[0]
            orig_size = float(values[1])

            if size_mode == "absolute":
                final_size = new_size_value
            elif size_mode == "relative":
                final_size = orig_size + new_size_value
            elif size_mode == "scale":
                final_size = orig_size * new_size_value
            else:
                final_size = new_size_value

            final_size = max(0.5, round(final_size, 1))

            # 重複チェック (同一対象があれば更新)
            task_exists = False
            for child in self.task_tree.get_children():
                t_vals = self.task_tree.item(child, "values")
                if t_vals[0] == orig_font and float(t_vals[1]) == orig_size:
                    self.task_tree.item(child, values=(orig_font, orig_size, new_font, final_size))
                    task_exists = True
                    break
            
            if not task_exists:
                self.task_tree.insert(
                    "", tk.END,
                    values=(orig_font, orig_size, new_font, final_size)
                )

    def _remove_selected_tasks(self):
        selected = self.task_tree.selection()
        if not selected:
            return
        for item in selected:
            self.task_tree.delete(item)

    def _clear_all_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

    def _apply_changes(self):
        if self.is_processing:
            messagebox.showwarning("処理中", "PDF処理が完了するまでお待ちください。")
            return

        if not self.pdf_path:
            messagebox.showwarning("未選択", "まずPDFファイルを開いてください。")
            return

        task_items = self.task_tree.get_children()
        if not task_items:
            messagebox.showwarning("タスクなし", "適用するタスクがありません。\n\"➕ タスクに追加\"ボタンでタスクを追加してください。")
            return

        # 保存先を選択
        base, ext = os.path.splitext(os.path.basename(self.pdf_path))
        default_name = f"{base}_modified{ext}"
        output_path = filedialog.asksaveasfilename(
            title="保存先を選択",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF ファイル", "*.pdf")]
        )
        if not output_path:
            return

        # 変換ルールを作成
        replacements = []
        for item in task_items:
            values = self.task_tree.item(item, "values")
            orig_font = values[0]
            orig_size = float(values[1])
            new_font = values[2]
            new_size = float(values[3])

            replacements.append({
                "orig_font": orig_font,
                "orig_size": orig_size,
                "new_font": new_font,
                "new_size": new_size,
            })
        
        print(f"[DEBUG] Created {len(replacements)} replacement rules:")
        for r in replacements:
            print(f"[DEBUG]   {r['orig_font']:<30} {r['orig_size']:>6} -> {r['new_font']:<30} {r['new_size']:>6}")

        # バックグラウンドで処理
        self.is_processing = True
        self.apply_btn.config(state=tk.DISABLED)
        self.add_task_btn.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_label.config(text="PDF変換中...")

        def _process():
            try:
                # PDF処理
                print(f"[DEBUG] Processing PDF - changing existing text fonts")
                result = change_fonts(
                    self.pdf_path,
                    output_path,
                    replacements,
                    system_font_paths=self.system_font_paths,
                    progress_callback=lambda cur, total: self.progress_queue.put(
                        ("progress", cur, total)
                    ),
                    region_bboxes=self.region_bboxes if self.region_bboxes else None,
                    ocr_results=self.ocr_results if self.ocr_results else None,
                )
                print(f"[DEBUG] PDF conversion completed:")
                print(f"[DEBUG]   Pages processed: {result['pages']}")
                print(f"[DEBUG]   Font spans changed: {result['changed_spans']}")
                self.progress_queue.put(("done", result))
            except Exception as e:
                print(f"[ERROR] PDF conversion failed: {e}")
                import traceback
                traceback.print_exc()
                self.progress_queue.put(("error", str(e)))

        threading.Thread(target=_process, daemon=True).start()

    # ─────────────────────────────────
    #  進捗管理
    # ─────────────────────────────────
    def _check_progress(self):
        """キューから進捗メッセージを取得して UI を更新"""
        latest_progress = None
        try:
            # 1回の呼び出しで最大100件程度のメッセージを処理し、UIを重くしない
            for _ in range(100):
                msg = self.progress_queue.get_nowait()
                if msg[0] == "progress":
                    latest_progress = msg
                elif msg[0] == "done":
                    result = msg[1]
                    self.is_processing = False
                    self.apply_btn.config(state=tk.NORMAL)
                    self.add_task_btn.config(state=tk.NORMAL)
                    self.progress_bar.config(mode="determinate")
                    self.progress_bar.stop()
                    self.progress_bar["value"] = 100
                    self.status_label.config(text="変換完了!")
                    
                    # 完了メッセージを表示
                    message = (
                        f"PDFの変換が完了しました。\n\n"
                        f"ページ数: {result['pages']}\n"
                        f"変更スパン数: {result['changed_spans']}"
                    )
                    
                    messagebox.showinfo("完了", message)
                    break
                elif msg[0] == "error":
                    self.is_processing = False
                    self.apply_btn.config(state=tk.NORMAL)
                    self.add_task_btn.config(state=tk.NORMAL)
                    self.progress_bar.config(mode="determinate")
                    self.progress_bar.stop()
                    self.progress_bar["value"] = 0
                    self.status_label.config(text="エラーが発生しました")
                    messagebox.showerror(
                        "エラー", f"PDF変換に失敗しました:\n{msg[1]}"
                    )
                    break
        except queue.Empty:
            pass

        if latest_progress:
            current, total = latest_progress[1], latest_progress[2]
            if current == "saving":
                self.progress_bar.config(mode="indeterminate")
                self.progress_bar.start(10)
                self.status_label.config(
                    text="ファイル保存中... (データ圧縮・最適化のため数分かかる場合があります)"
                )
            else:
                self.progress_bar.config(mode="determinate")
                self.progress_bar.stop()
                pct = (current / total) * 100
                self.progress_bar["value"] = pct
                self.status_label.config(
                    text=f"処理中... {current}/{total} ページ"
                )

        self.root.after(100, self._check_progress)

    def _show_about(self):
        """バージョン情報ダイアログを表示"""
        version = get_build_version()
        about_text = f"""PDF Font Changer
Version {version}

PDFファイルのフォントを一括変更するデスクトップアプリケーション

Copyright (c) 2026 y-128
Licensed under MIT License

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
使用ライブラリ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PyMuPDF 1.24.11
  Copyright (C) 2015-2024 Artifex Software, Inc.
  Licensed under AGPL-3.0
  https://github.com/pymupdf/PyMuPDF

Pillow ≥12.0.0
  Copyright (c) 1997-2024 Secret Labs AB
  Licensed under HPND
  https://python-pillow.org/

ndlocr-lite 1.1.2
  Copyright (C) National Diet Library of Japan
  Licensed under CC-BY-4.0
  https://github.com/ndl-lab/ndlocr-lite

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 重要なライセンス情報:
本ソフトウェアは PyMuPDF (AGPL-3.0) を使用しています。
AGPL-3.0 はコピーレフトライセンスのため、本ソフトウェアを
再配布する場合はソースコードの公開が必要です。

ソースコード・完全なライセンス情報:
https://github.com/y-128/PDF-Font-Changer"""

        # トップレベルウィンドウを作成
        about_window = tk.Toplevel(self.root)
        about_window.title("バージョン情報")
        about_window.geometry("600x560")
        about_window.resizable(False, False)
        
        # テキストウィジェット
        text_frame = ttk.Frame(about_window, padding=20)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("", 10),
            relief=tk.FLAT,
            bg=self.root.cget('bg')
        )
        text_widget.insert("1.0", about_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 閉じるボタン
        button_frame = ttk.Frame(about_window, padding=(0, 10, 20, 20))
        button_frame.pack(fill=tk.X)
        ttk.Button(
            button_frame,
            text="閉じる",
            command=about_window.destroy,
            width=10
        ).pack(side=tk.RIGHT)
        
        # ウィンドウを中央に配置
        about_window.transient(self.root)
        about_window.grab_set()
        
        # 中央配置
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (about_window.winfo_screenheight() // 2) - (560 // 2)
        about_window.geometry(f"600x500+{x}+{y}")


def main():
    root = tk.Tk()

    # DPIスケーリング対応
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PDFFontChangerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
