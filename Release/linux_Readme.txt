================================================================================
PDF Font Changer - Linux版 ビルド手順
================================================================================

【必要な環境】
- Linux（Ubuntu 20.04+, Fedora 35+, Debian 11+, Arch など）
- Python 3.10 以上（3.12 推奨）
- Tkinter（python3-tk）
- Git

================================================================================
【1】事前準備 - 必要パッケージのインストール
================================================================================

◆ Ubuntu / Debian 系：

   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv python3-tk git

◆ Fedora / RHEL 系：

   sudo dnf install -y python3 python3-pip python3-tkinter git

◆ Arch Linux：

   sudo pacman -S python python-pip tk git

◆ openSUSE：

   sudo zypper install python3 python3-pip python3-tk git

================================================================================
【2】リポジトリのクローン
================================================================================

1. ターミナルで以下を実行：

   git clone https://github.com/y-128/PDF-Font-Changer.git
   cd PDF-Font-Changer

2. または ZIP ダウンロード後に展開

================================================================================
【3】仮想環境の構築
================================================================================

1. プロジェクトルートで仮想環境を作成：

   python3 -m venv .venv

2. 仮想環境を有効化：

   source .venv/bin/activate

   ※ ターミナルプロンプトに (.venv) が表示されれば成功

================================================================================
【4】依存パッケージのインストール
================================================================================

仮想環境を有効化した状態で：

   pip install --upgrade pip
   pip install -r requirements.txt
   pip install pyinstaller

※ ndlocr-lite（OCR機能）の依存パッケージ（onnxruntime、opencv等）も
   自動的にインストールされます。インストール完了まで数分かかる場合があります。

================================================================================
【OCR機能（ndlocr-lite）について】
================================================================================

ndlocr-lite を含むビルドでは以下の点に注意してください:

- OCR モデルファイル（合計約 150MB）がバンドルされるため、
  最終バイナリは 300MB 以上になります
- プロジェクトフォルダのパスに日本語（全角文字）が含まれていると
  ndlocr-lite が動作しません
  NG例: /home/田中/projects/PDF-Font-Changer/
  OK例: /home/tanaka/projects/PDF-Font-Changer/
- OCR機能が不要な場合は requirements.txt から ndlocr-lite 行を削除して
  ビルドするとファイルサイズを大幅に削減できます
- Linux では python3-tk パッケージが必要です（apt install python3-tk）

================================================================================
【5】ビルドの実行
================================================================================

1. Release フォルダに移動：

   cd Release

2. PyInstaller でビルド実行：

   pyinstaller linux_build.spec

3. ビルドが完了すると、以下に実行ファイルが生成されます：

   Release/dist/pdf-font-changer

================================================================================
【6】動作確認
================================================================================

1. 実行ファイルに実行権限を付与（必要に応じて）：

   chmod +x dist/pdf-font-changer

2. アプリを起動：

   ./dist/pdf-font-changer

   または

   cd dist
   ./pdf-font-changer

3. GUIが正常に表示されることを確認
4. テスト用PDFを開いて動作を確認

================================================================================
【7】デスクトップエントリの作成（オプション）
================================================================================

アプリケーションメニューに登録する場合：

1. デスクトップエントリファイルを作成：

   cat > ~/.local/share/applications/pdf-font-changer.desktop << 'EOF'
   [Desktop Entry]
   Version=1.0
   Type=Application
   Name=PDF Font Changer
   Comment=Change fonts in PDF files
   Exec=/path/to/dist/pdf-font-changer
   Icon=/path/to/assets/icon.png
   Terminal=false
   Categories=Office;Utility;
   EOF

2. /path/to を実際のパスに置き換えて保存

3. デスクトップエントリを更新：

   update-desktop-database ~/.local/share/applications

================================================================================
【配布方法】
================================================================================

◆ 単一実行ファイルとして配布：

- dist/pdf-font-changer を配布
- ユーザーは chmod +x で実行権限を付与後、実行可能
- すべての依存ライブラリが実行ファイルに埋め込まれています

◆ AppImage として配布（推奨）：

AppImage 形式にすることで、より配布しやすくなります：

1. appimagetool をダウンロード：

   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage

2. AppDir 構造を作成：

   mkdir -p AppDir/usr/bin
   cp dist/pdf-font-changer AppDir/usr/bin/
   cp ../../assets/icon.png AppDir/

3. .desktop ファイルを作成：

   cat > AppDir/pdf-font-changer.desktop << 'EOF'
   [Desktop Entry]
   Name=PDF Font Changer
   Exec=pdf-font-changer
   Icon=icon
   Type=Application
   Categories=Office;Utility;
   EOF

4. AppImage を生成：

   ./appimagetool-x86_64.AppImage AppDir PDF Font Changer-x86_64.AppImage

5. 生成された PDF Font Changer-x86_64.AppImage を配布

◆ Flatpak として配布：

より高度なサンドボックス環境が必要な場合は Flatpak への変換も可能です。
詳細は https://docs.flatpak.org/ を参照してください。

================================================================================
【トラブルシューティング】
================================================================================

◆ ビルドエラーが発生する場合：

   1. Python と Tkinter が正しくインストールされているか確認：
      python3 -c "import tkinter; print('OK')"
      → OK と表示されること

   2. 開発用パッケージが必要な場合：
      # Ubuntu/Debian:
      sudo apt install python3-dev

      # Fedora/RHEL:
      sudo dnf install python3-devel

   3. 仮想環境を再構築：
      deactivate
      rm -rf .venv
      python3 -m venv .venv
      source .venv/bin/activate
      pip install -r requirements.txt
      pip install pyinstaller

   4. キャッシュをクリア：
      rm -rf build dist __pycache__

◆ 実行ファイルが起動しない場合：

   1. 実行権限を確認：
      ls -l dist/pdf-font-changer
      → -rwxr-xr-x のように x が付いていること

   2. 依存ライブラリを確認：
      ldd dist/pdf-font-changer
      → "not found" が無いことを確認

   3. コンソール付きで起動してエラーを確認：
      linux_build.spec の console=False を console=True に変更
      再ビルドしてエラーメッセージを確認

◆ Tkinter エラーが発生する場合：

   1. Tkinter パッケージを再インストール：
      # Ubuntu/Debian:
      sudo apt install --reinstall python3-tk

      # Fedora/RHEL:
      sudo dnf reinstall python3-tkinter

   2. DISPLAY 環境変数を確認：
      echo $DISPLAY
      → :0 や :1 などが表示されること（GUIセッション内）

◆ UPX エラーが発生する場合：

   UPX がインストールされていない場合、ビルド時に警告が出ます。
   必須ではありませんが、インストールすると実行ファイルサイズが小さくなります：

   # Ubuntu/Debian:
   sudo apt install upx

   # Fedora/RHEL:
   sudo dnf install upx

   # Arch:
   sudo pacman -S upx

================================================================================
【カスタマイズ】
================================================================================

linux_build.spec を編集することで、以下のカスタマイズが可能：

- 実行ファイル名の変更（name='...' の部分）
- コンソール表示/非表示（console=True/False）
- UPX圧縮の有効化/無効化（upx=True/False）

編集後は再度 pyinstaller linux_build.spec を実行してください。

================================================================================
【異なるディストリビューション向けのビルド】
================================================================================

PyInstaller でビルドした実行ファイルは、ビルドしたシステムと同等以上のglibc
バージョンを持つシステムでのみ動作します。

より広い互換性が必要な場合：

1. 古めの安定版ディストリビューション（Ubuntu 20.04 LTS など）でビルド
2. または Docker を使用して特定環境でビルド：

   docker run --rm -v $(pwd):/work -w /work ubuntu:20.04 bash -c \
     "apt update && apt install -y python3 python3-pip python3-tk && \
      pip3 install pyinstaller && \
       cd Release && pyinstaller linux_build.spec"

================================================================================
