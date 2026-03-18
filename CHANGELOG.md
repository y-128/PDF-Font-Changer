# CHANGELOG

All notable changes to this project are documented in this file.

## [1.2.0] - 2026-03-18

### Added
- フォント選択 UI の改善: 推奨フォントを優先表示し、一覧に仕切り線を挿入（仕切り線選択時は前回選択に復元する処理を追加）。
- システムフォント検出を強化: `fonttools` を使用して日本語名を優先して表示名を抽出、TTC（コレクション）対応を実装（`font_scanner.py`）。
- `requirements.txt` に `fonttools` を追加。

### Changed
- フォント関連の微調整。

## [1.1.1] - 2026-03-12

### Changed
- スケーリング機能の改善:
	- DPI / スケーリングの自動検出を導入し、tk のスケーリング設定を活用するように変更。
	- macOS 環境での過剰なスケーリングを抑制する補正を追加。
- CI / リリースワークフロー: リリースアセットのアップロードに使用する GitHub Action を v2 に更新。

## [1.1.0] - 2026-03-11

### Added
- OCR 機能の追加:
	- ndlocr-lite を利用した日本語 OCR 処理を実装（ocr_processor.py）。
	- OCR 結果をページ単位および矩形領域として保持し、検出したテキスト領域をフォント変更処理に反映できるようにした。
	- UI に OCR 有効化のトグルを追加。
- ドキュメント: README に OCR の使い方と依存関係に関する注意を追記。

### Changed
- 依存関係の整理とインストールに関する注意事項を追加。

## [1.0.0] - 2026-03-03

### Added
- 初回リリース:
	- PDF のフォント検出、一覧表示、選択したフォントの一括変更を行う GUI を提供。
	- Windows / Linux / macOS 向けのビルド設定と仕様ファイル（Release ディレクトリ）を追加。
	- ビルド手順と初期ドキュメントを README に追加。

## Unreleased
- (今後のリリースノートをここに追記します)
