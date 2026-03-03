# PDF Font Changer

PDFファイルのフォントおよびフォントサイズを一括変更するデスクトップアプリケーションです。**Windows / Linux / macOS** で完全オフライン動作します。

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
- **バックグラウンド処理**: UI凍結なし

## インストール

### 前提条件

- **Python 3.9以上** （3.12推奨）
- **Tkinter対応Python環境** （GUI実行に必須）

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
| **pdf_processor.py** | PyMuPDF を使用した PDF 処理。フォント情報抽出と変更ロジック |
| **font_scanner.py** | OS ごとのフォントディレクトリ検索。利用可能フォント検出 |
| **create_icon.py** | PNG → macOS `.icns` アイコン変換ツール |
| **requirements.txt** | pip でインストールする Python パッケージ一覧 |
| **LICENSE** | ライセンステキスト |

## 依存パッケージ

| パッケージ | バージョン | 説明 |
|-----------|-----------|------|
| **PyMuPDF** | 1.24.11 | PDF の読込・編集・レンダリング |
| **Pillow** | ≥12.0.0 | 画像処理と GUI での画像表示 |

最小限のシンプルな依存で構成されています。

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
- **テキストが画像化** → システムの OCR ツール（Tesseract等）を別途で使用してください
- **フォント埋め込みなし** → 変更不可能な場合あり

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

### 制約と注意

- 複雑レイアウト → 位置ズレの可能性
- PDF の制限事項 → 変更不可能な場合あり (フォント埋め込み不可など)
- 画像テキスト → OCR が必要です

## ライセンス

このプロジェクトは MIT License でライセンスされています。詳細は [LICENSE](LICENSE) を参照してください。

### 依存ライブラリのライセンス

本ソフトウェアは以下のサードパーティライブラリを使用しています：

#### PyMuPDF (1.24.11)
- **ライセンス**: GNU Affero General Public License v3.0 (AGPL-3.0)
- **著作権**: Copyright (C) 2015-2024 Artifex Software, Inc.
- **リンク**: https://github.com/pymupdf/PyMuPDF
- **重要**: AGPL-3.0 はコピーレフトライセンスです。本ソフトウェアを配布する場合、AGPL-3.0 の要件に従ってソースコードを公開する必要があります。商用/クローズドソース利用には [Artifex社の商用ライセンス](https://artifex.com/licensing/) が必要です。

#### Pillow (≥12.0.0)
- **ライセンス**: Historical Permission Notice and Disclaimer (HPND)
- **著作権**: Copyright (c) 1997-2024 by Secret Labs AB and contributors
- **リンク**: https://python-pillow.org/

完全なライセンステキストは [LICENSE](LICENSE) ファイルに含まれています。

## 関連リンク

- **GitHub リポジトリ**: [y-128/PDF-Font-Changer](https://github.com/y-128/PDF-Font-Changer)
- **Issue トラッカー**: [GitHub Issues](https://github.com/y-128/PDF-Font-Changer/issues)
