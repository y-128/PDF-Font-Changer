# PDF Font Changer

PDFファイルのフォントおよびフォントサイズを一括変更するデスクトップアプリケーションです。**Windows / Linux / macOS** で完全オフライン動作します。
スキャンPDF（画像のみのPDF）は [NDLOCR-Lite](https://github.com/ndl-lab/ndlocr-lite) によるOCRで文字認識してからフォント変更できます。
Windows(x64, Windows 11)、Mac(Apple M1, macOS Tahoe)環境で動作確認を行いました。

## 主な機能

- **フォント情報の解析**: PDFに含まれるフォント（フォント名、サイズ、出現回数）を一覧表示
- **プレビュー表示**: PDF内容をリアルタイムで確認しながら編集
- **豊富なフォント選択**: PDF標準14フォント + システムにインストールされているすべてのフォント
- **柔軟なサイズ変更**: 3つのモード
  - **絶対値**: すべてのフォントを同じサイズに統一
  - **相対値**: 現在のサイズから加算・減算
  - **倍率**: 現在のサイズに乗算
- **複数フォント一括変更**: 複数のフォントを同時に処理
- **範囲指定変更**: PDFの特定の矩形範囲のみを対象に変更可能
- **スキャンPDF対応（OCR）**: NDLOCR-Lite を使い、スキャン画像から文字を認識してフォント変更
- **バックグラウンド処理**: UI凍結なし

## インストール

### 前提条件

- **Python 3.10以上** （3.12推奨）
- **Tkinter対応Python環境** （GUI実行に必須）
- **OCR機能を使う場合**: ndlocr-lite の依存パッケージ（onnxruntime 等）が自動インストールされます

> ⚠️ **パスの注意（OCR使用時）**: NDLOCR-Lite は日本語（全角文字）を含むパスに配置すると起動しないことがあります。プロジェクトフォルダはASCII文字のみのパスに置いてください。

### セットアップ手順

#### 1. リポジトリをクローン

```bash
git clone https://github.com/y-128/PDF-Font-Changer.git
cd PDF-Font-Changer
```

#### 2. 仮想環境を構築

```bash
# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1
# Windows (Command Prompt):
# .venv\Scripts\activate.bat
```

#### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

> **Note**: `Pillow` は `ndlocr-lite` の依存パッケージとして自動インストールされます。
> `requirements.txt` に直接 `Pillow` を記載すると `ndlocr-lite` が要求するバージョンと競合する可能性があるため、意図的に除外しています。

### OS別の注意事項

#### Windows

- [python.org](https://www.python.org/) から Python 3.12をダウンロード
- インストーラ実行時に **「Add python.exe to PATH」** にチェック
- PowerShell を使用する場合、実行ポリシーの変更が必要な場合があります

#### macOS

Homebrewでの Python + Tkinter インストール推奨：

```bash
brew install python@3.12
brew install python-tk@3.12
```

その後、仮想環境を以下で作成：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Linux

ほとんどのディストリビューションで Python 3 が既にインストール済みです。Tkinter が別パッケージの場合：

```bash
# Ubuntu / Debian:
sudo apt install python3-tk

# Fedora / RHEL:
sudo dnf install python3-tkinter

# Arch:
sudo pacman -S tk
```

## ビルド（単一実行ファイル）

PyInstaller を使って各 OS 向けの単一実行ファイルをビルドできます。

### 前提

```bash
pip install pyinstaller
```

> ⚠️ **ビルド時のパス制約**: OCR 機能（ndlocr-lite）をビルドに含める場合、プロジェクトフォルダのパスに日本語（全角文字）を含めないでください。

### ビルド手順

各 OS の `Release/` フォルダ内の spec ファイルを使用します。

```bash
# macOS → .app バンドル（~300MB）
cd Release
pyinstaller mac_build.spec
# → Release/dist/PDF Font Changer.app

# Windows → 単一 .exe（~300MB）
cd Release
pyinstaller win_build.spec
# → Release\dist\PDF Font Changer.exe

# Linux → 単一バイナリ（~300MB）
cd Release
pyinstaller linux_build.spec
# → Release/dist/pdf-font-changer
```

### ビルドサイズについて

| 構成 | 概算サイズ |
|------|------------|
| OCR あり（ndlocr-lite 含む） | **300MB 以上** |
| OCR なし（ndlocr-lite 除外） | **50MB 前後** |

OCR 不要な場合は `requirements.txt` から `ndlocr-lite` の行を削除してから `pip install -r requirements.txt` を実行し、ビルドしてください。spec ファイルは ndlocr-lite が未インストールの場合は自動的にスキップします。

詳細な手順は各 OS のビルドガイドを参照してください:
- [macOS ビルドガイド](Release/mac_Readme.txt)
- [Windows ビルドガイド](Release/win_Readme.txt)
- [Linux ビルドガイド](Release/linux_Readme.txt)

## 使用方法

### アプリケーション起動

```bash
python main.py
```

### 基本操作

1. **「📂 PDFを開く」** をクリックして対象PDFを選択
2. **フォント一覧** から変更対象のフォントを選択（複数選択可）
3. **新フォント** と **新サイズ** を入力
4. **サイズ変更モード** を選択：
   - **絶対値**: 例えば「14」を入力 → すべてをサイズ14に統一
   - **相対値**: 例えば「+2」を入力 → 各フォントのサイズに2を加算
   - **倍率**: 例えば「1.5」を入力 → 各フォントのサイズを1.5倍
5. オプション: **「🖼 置換範囲選択」** で特定の領域のみを対象に変更可能
6. **「➕ タスクに追加」** でタスクリストに追加
7. **「✅ タスクを適用して保存」** をクリック
8. 保存先を指定して完了

### スキャンPDF（画像PDF）の変換

テキストデータを持たないスキャンPDFに対して、NDLOCR-Lite でOCRを行ってからフォント変換できます。

1. ツールバーの **「OCR（スキャンPDF）」チェックボックスをON** にする
2. **「📂 PDFを開く」** でスキャンPDFを選択
   - バックグラウンドでOCR処理が実行されます（ページ数・解像度によって数分かかります）
   - 初回はモデルのロードがあるため、さらに時間がかかります
3. フォント一覧に **「OCR検出」** エントリが推定サイズ別に表示されます
   - サイズはバウンディングボックスの高さ/幅から推定した近似値です
4. 「OCR検出」エントリを選択し、新しいフォント・サイズを設定して **「➕ タスクに追加」**
5. **「✅ タスクを適用して保存」** で変換
   - 変換時に元の画像テキスト部分は **白で塗りつぶし** てから新しいフォントで上書きします

> ⚠️ **OCRサイズ推定の精度について**: フォントサイズはバウンディングボックスから推定するため、原稿の品質やレイアウトによって誤差が生じます。出力後に確認してください。

> ⚠️ **対応言語**: NDLOCR-Lite は日本語文書（特に図書・雑誌等の活字）に最適化されています。手書き文字や縦書き文書も一定程度対応しますが、精度は文書によって異なります。

### 範囲指定変更

PDFの特定の矩形範囲のみをフォント変更対象にしたい場合：

1. フォント一覧でフォントを選択
2. 新フォント・新サイズを設定
3. **「🖼 置換範囲選択」** ボタンをクリック
4. プレビューウィンドウでドラッグして矩形領域を指定
5. タスクを追加して実行

タスクリストの範囲一覧の **ページ列をクリック** すると、その範囲を全ページに適用する/しないを切り替え可能です。

## プロジェクト構成

```
PDF-Font-Changer/
├── main.py                     # GUI アプリケーションメイン
├── pdf_processor.py            # PDF 処理（フォント抽出・変更）
├── ocr_processor.py            # NDLOCR-Lite ラッパー（スキャンPDF OCR）
├── font_scanner.py             # システムフォント検出
├── create_icon.py              # macOS アイコン生成スクリプト
├── requirements.txt            # Python 依存パッケージ
├── LICENSE                     # ライセンス
├── README.md                   # このファイル
└── assets/                     # リソースファイル
    ├── icon.png                # アプリケーションアイコン
    └── icon.icns               # macOS 用アイコン
```

### ファイル説明

| ファイル | 説明 |
|---------|------|
| **main.py** | Tkinter GUI の主要コード。ウィンドウ構築、イベント処理担当 |
| **pdf_processor.py** | PyMuPDF を使用した PDF 処理。フォント情報抽出・変更・OCR結果の白塗り埋め込みロジック |
| **ocr_processor.py** | NDLOCR-Lite の初期化・OCR実行ラッパー。モデルの遅延ロード対応 |
| **font_scanner.py** | OS ごとのフォントディレクトリ検索。利用可能フォント検出 |
| **create_icon.py** | PNG → macOS `.icns` アイコン変換ツール |
| **requirements.txt** | pip でインストールする Python パッケージ一覧 |
| **LICENSE** | ライセンステキスト |

## 依存パッケージ

| パッケージ | バージョン | 説明 |
|-----------|-----------|------|
| **PyMuPDF** | 1.24.11 | PDF の読込・編集・レンダリング |
| **Pillow** | ≥12.0.0 | 画像処理と GUI での画像表示 |
| **ndlocr-lite** | ≥1.0.0 | スキャンPDF OCR（NDLOCR-Lite, 国立国会図書館）|

ndlocr-lite は以下の重い依存パッケージを自動インストールします（OCR機能を使わない場合は不要）：

| パッケージ | 説明 |
|-----------|------|
| **onnxruntime** | DEIM テキスト検出モデル実行 |
| **opencv-python** | 画像前処理 |
| **numpy** | 数値計算 |

## トラブルシューティング

### アプリが起動しない

```bash
# 仮想環境が有効化されているか確認
which python  # macOS/Linux
# 出力例: /path/to/.venv/bin/python

# 依存パッケージが正しくインストールされているか確認
pip list
```

### PDFが正しく処理されない

- **レイアウトが複雑** (表・複数カラム等) → 位置ズレの可能性あり
- **テキストが画像化（スキャンPDF）** → ツールバーの「OCR（スキャンPDF）」チェックボックスをONにして再度PDFを開いてください
- **フォント埋め込みなし** → 変更不可能な場合あり

### OCR関連のトラブル

**OCR処理が開始しない / 「OCR検出」が表示されない**
- 「OCR（スキャンPDF）」チェックボックスがONになっているか確認
- PDFに実際にスキャン画像が含まれているか確認（テキストPDFでは「OCR検出」は表示されません）
- ndlocr-lite が正しくインストールされているか確認: `pip show ndlocr-lite`

**OCRが実行できない（ImportError / モデルファイルが見つからない）**
- ndlocr-lite の依存パッケージを再インストール: `pip install -r requirements.txt`
- アプリのパスに日本語（全角文字）が含まれていないか確認（ndlocr-lite の制約）
  - NG例: `/Users/田中/Projects/PDF-Font-Changer/`
  - OK例: `/Users/tanaka/Projects/PDF-Font-Changer/`

**OCR後のフォントサイズが不正確**
- ndlocr-lite はフォントサイズ情報を返さないため、バウンディングボックスから推定しています
- 元のPDFのスキャン解像度が低い場合、推定精度が下がります
- 変換後にサイズを手動で調整してください

### macOS で Tkinter エラー

```bash
brew install python-tk@3.12

# または仮想環境を再構築
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows で実行ファイルが起動しない

- PowerShell 実行ポリシーエラーが出た場合：
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

## 技術的な詳細

### PDF フォント変更の仕組み

1. PyMuPDF で PDF ページ内のテキストを走査
2. 対象フォントを検出
3. 元のテキストを **Redaction** (墨消し) で削除
4. 新しいフォント・サイズで再挿入

### スキャンPDF の OCR 処理フロー

1. **OCRモードON** でPDFを開くと、バックグラウンドスレッドで各ページを処理
2. 各ページをPNG画像に変換（zoom=2.0、144 dpi相当）
3. NDLOCR-Lite の DEIM 検出器でテキスト行のバウンディングボックスを検出
4. PARSEQ 認識器で各テキスト行の文字列を認識
5. バウンディングボックスの高さ（横書き）または幅（縦書き）からフォントサイズを推定
6. OCR結果はページ・行単位で保存し、フォント一覧に「OCR検出 / サイズ / 行数」形式で表示
7. タスク適用時：
   - 各OCR行の位置に白の Redaction（矩形塗りつぶし）を適用し、スキャン画像のテキストを消去
   - `page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)` で画像ピクセルまで白塗り
   - 新しいフォント・サイズで認識テキストを再挿入

### 制約と注意

- 複雑レイアウト → 位置ズレの可能性
- PDF の制限事項 → 変更不可能な場合あり (フォント埋め込み不可など)
- **スキャン画像テキスト** → OCRモードで対応（「OCR（スキャンPDF）」チェックボックスをON）
- **OCRフォントサイズ** → バウンディングボックスから推定した近似値。元PDFとの完全一致は不可
- **ndlocr-lite パス制約** → インストールパスに日本語文字（全角）を含むと動作しないことがあります

### 安全な利用のために

- **信頼できるソースの PDF のみ**を処理してください。悪意ある細工をされた PDF は PDF パーサの脆弱性を突く可能性があります
- 定期的に依存パッケージを更新してください: `pip install --upgrade PyMuPDF Pillow ndlocr-lite`
- アプリのインストールパスに日本語（全角文字）を含めないでください（ndlocr-lite の制約）

## ライセンス

このプロジェクトは MIT License でライセンスされています。使用している依存ライブラリのライセンス情報を含む詳細は [LICENSE](LICENSE) を参照してください。

## 関連リンク

- **GitHub リポジトリ**: [y-128/PDF-Font-Changer](https://github.com/y-128/PDF-Font-Changer)
- **Issue トラッカー**: [GitHub Issues](https://github.com/y-128/PDF-Font-Changer/issues)
