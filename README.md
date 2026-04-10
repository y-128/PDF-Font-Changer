# PDF Font Changer

PDFファイルのフォントおよびフォントサイズを一括変更するデスクトップアプリケーションです。
Windows / Linux / macOS で完全オフライン動作します。

スキャンPDF（画像のみのPDF）は [NDLOCR-Lite](https://github.com/ndl-lab/ndlocr-lite) によるOCRで文字認識してからフォント変更できます。

> Windows (x64, Windows 11)、Mac (arm, macOS Tahoe) 環境で動作確認済み。

## 主な機能

| 機能 | 説明 |
|------|------|
| フォント情報の解析 | PDFに含まれるフォント名・サイズ・出現回数を一覧表示 |
| ドラッグ&ドロップ | PDFファイルをウィンドウにドロップして開く（全OS対応） |
| プレビュー表示 | PDF内容をリアルタイムで確認しながら編集 |
| 豊富なフォント選択 | PDF標準14フォント + システムにインストールされた全フォント |
| 柔軟なサイズ変更 | 絶対値・相対値（加算/減算）・倍率の3モード |
| 複数フォント一括変更 | 複数のフォントを同時に処理 |
| 範囲指定変更 | PDFの特定の矩形範囲のみを対象に変更 |
| スキャンPDF対応 | NDLOCR-Lite によるOCRでスキャン画像から文字認識 |
| バックグラウンド処理 | UI凍結なしで処理を実行 |

## セットアップ

### 前提条件

- **Python 3.10以上**（3.12推奨）
- **Tkinter対応Python環境**（GUI実行に必須）

### インストール

```bash
git clone https://github.com/y-128/PDF-Font-Changer.git
cd PDF-Font-Changer
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### OS別の注意事項

<details>
<summary>Windows</summary>

- [python.org](https://www.python.org/) から Python 3.12をダウンロード
- インストーラ実行時に **「Add python.exe to PATH」** にチェック
- PowerShell で実行ポリシーエラーが出る場合:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

</details>

<details>
<summary>macOS</summary>

Homebrewでの Python + Tkinter インストール推奨:

```bash
brew install python@3.12
brew install python-tk@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

<details>
<summary>Linux</summary>

Tkinter が別パッケージの場合:

```bash
# Ubuntu / Debian
sudo apt install python3-tk
# Fedora / RHEL
sudo dnf install python3-tkinter
# Arch
sudo pacman -S tk
```

</details>

## 使い方

```bash
python main.py
```

### 基本操作

1. **「PDFを開く」** でPDFを選択、またはウィンドウに **ドラッグ&ドロップ**
2. **フォント一覧** から変更対象のフォントを選択（複数選択可）
3. **新フォント** と **新サイズ** を入力
4. **サイズ変更モード** を選択:
   - **絶対値**: 例 `14` → すべてをサイズ14に統一
   - **相対値**: 例 `+2` → 各フォントのサイズに2を加算
   - **倍率**: 例 `1.5` → 各フォントのサイズを1.5倍
5. 必要に応じて **「置換範囲選択」** で特定の領域のみを対象に指定
6. **「タスクに追加」** → **「タスクを適用して保存」** で完了

### スキャンPDF（画像PDF）の変換

1. ツールバーの **「OCR（スキャンPDF）」** チェックボックスをON
2. **「PDFを開く」** でスキャンPDFを選択（バックグラウンドでOCR処理が実行される）
3. フォント一覧に **「OCR検出」** エントリが推定サイズ別に表示される
4. エントリを選択し、新しいフォント・サイズを設定して **「タスクに追加」**
5. **「タスクを適用して保存」** で変換（元の画像テキスト部分は白で塗りつぶして新フォントで上書き）

> **注意**: OCR使用時はプロジェクトフォルダをASCII文字のみのパスに配置してください（NDLOCR-Liteの制約）。

### 範囲指定変更

1. フォント一覧でフォントを選択し、新フォント・新サイズを設定
2. **「置換範囲選択」** ボタンをクリック
3. プレビューウィンドウでドラッグして矩形領域を指定
4. タスクを追加して実行

タスクリストの範囲一覧の **ページ列をクリック** すると、その範囲を全ページに適用する/しないを切り替え可能です。

## ビルド

PyInstaller を使って各 OS 向けの単一実行ファイルをビルドできます。

```bash
pip install pyinstaller

# macOS
cd Release && pyinstaller mac_build.spec
# → Release/dist/PDF Font Changer.app

# Windows
cd Release && pyinstaller win_build.spec
# → Release\dist\PDF Font Changer.exe

# Linux
cd Release && pyinstaller linux_build.spec
# → Release/dist/pdf-font-changer
```

| 構成 | 概算サイズ |
|------|------------|
| OCR あり（ndlocr-lite 含む） | 300MB 以上 |
| OCR なし（ndlocr-lite 除外） | 50MB 前後 |

OCR 不要な場合は `requirements.txt` から `ndlocr-lite` の行を削除してからインストール・ビルドしてください。spec ファイルは ndlocr-lite が未インストールの場合は自動的にスキップします。

各 OS の詳細なビルド手順:
- [macOS ビルドガイド](Release/mac_Readme.txt)
- [Windows ビルドガイド](Release/win_Readme.txt)
- [Linux ビルドガイド](Release/linux_Readme.txt)

## プロジェクト構成

```
PDF-Font-Changer/
├── main.py              # GUI アプリケーションメイン (Tkinter)
├── pdf_processor.py     # PDF 処理 (フォント抽出・変更, PyMuPDF)
├── ocr_processor.py     # NDLOCR-Lite ラッパー (スキャンPDF OCR)
├── font_scanner.py      # システムフォント検出
├── create_icon.py       # macOS アイコン生成スクリプト
├── requirements.txt     # Python 依存パッケージ
├── assets/              # アイコンリソース (png, icns, ico)
└── Release/             # OS別ビルド設定 (spec ファイル)
```

## 依存パッケージ

| パッケージ | 用途 |
|-----------|------|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF の読込・編集・レンダリング |
| [fonttools](https://github.com/fonttools/fonttools) | フォントメタデータ解析 (TTF/TTC) |
| [Pillow](https://python-pillow.org/) | 画像処理・GUI での画像表示 |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | ドラッグ&ドロップ対応（全OS） |
| [ndlocr-lite](https://github.com/ndl-lab/ndlocr-lite) | スキャンPDF OCR（国立国会図書館） |

> `Pillow` は `ndlocr-lite` の依存パッケージとして自動インストールされます。`requirements.txt` にはバージョン競合を避けるため直接記載していません。

## 技術的な詳細

### PDFフォント変更の仕組み

1. PyMuPDF で PDF ページ内のテキストを走査
2. 対象フォントを検出
3. 元のテキストを Redaction（墨消し）で削除
4. 新しいフォント・サイズで再挿入

### スキャンPDFのOCR処理フロー

1. 各ページをPNG画像に変換（zoom=2.0, 144 dpi相当）
2. NDLOCR-Lite の DEIM 検出器でテキスト行のバウンディングボックスを検出
3. PARSEQ 認識器で各テキスト行の文字列を認識
4. バウンディングボックスの高さ/幅からフォントサイズを推定
5. タスク適用時に白の Redaction で画像テキストを消去し、新フォントで再挿入

### 制約

- 複雑なレイアウト（表・複数カラム等）では位置ズレの可能性あり
- フォント埋め込み不可のPDFは変更できない場合あり
- OCRフォントサイズはバウンディングボックスからの推定値（元PDFとの完全一致は不可）
- NDLOCR-Lite は日本語文書に最適化されている
- インストールパスに日本語（全角文字）を含むと ndlocr-lite が動作しない場合あり

## トラブルシューティング

<details>
<summary>アプリが起動しない</summary>

```bash
# 仮想環境が有効化されているか確認
which python  # macOS/Linux
# 出力例: /path/to/.venv/bin/python

# 依存パッケージの確認
pip list
```

</details>

<details>
<summary>PDFが正しく処理されない</summary>

- **レイアウトが複雑** → 位置ズレの可能性あり
- **テキストが画像化（スキャンPDF）** → 「OCR（スキャンPDF）」チェックボックスをONにして再度開く
- **フォント埋め込みなし** → 変更不可能な場合あり

</details>

<details>
<summary>OCR関連のトラブル</summary>

- **OCR処理が開始しない**: チェックボックスがONか確認。テキストPDFでは「OCR検出」は表示されない
- **ImportError / モデルが見つからない**: `pip install -r requirements.txt` で再インストール
- **パスエラー**: プロジェクトパスに日本語（全角文字）が含まれていないか確認
- **サイズが不正確**: バウンディングボックスからの推定のため、変換後に手動調整が必要

</details>

<details>
<summary>macOS で Tkinter エラー</summary>

```bash
brew install python-tk@3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

## ライセンス

### このアプリケーション

[MIT License](LICENSE) — Copyright (c) 2026 y-128

### サードパーティライブラリ

このアプリケーションは以下のオープンソースライブラリを使用しています。
詳細は [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) を参照してください。

| ライブラリ | ライセンス |
|-----------|-----------|
| PyMuPDF | AGPL-3.0 |
| fonttools | MIT |
| Pillow | HPND |
| tkinterdnd2 | MIT |
| ndlocr-lite | CC-BY-4.0 |
| onnxruntime, numpy 他 | MIT / BSD / Apache-2.0 |

> **PyMuPDF について**: AGPL-3.0 はコピーレフトライセンスです。このソフトウェアを配布する場合は、ソースコードを AGPL-3.0 の条件で公開する必要があります。商用クローズドソースでの利用には Artifex Software の商用ライセンスが必要です。

## リンク

- [GitHub リポジトリ](https://github.com/y-128/PDF-Font-Changer)
- [Issue トラッカー](https://github.com/y-128/PDF-Font-Changer/issues)
- [CHANGELOG](CHANGELOG.md)
