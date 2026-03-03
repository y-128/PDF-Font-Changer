#!/usr/bin/env python3
"""
アイコンファイルを作成するスクリプト
icon.png から macOS用の.icnsファイルを生成します
"""

import os
import subprocess
from pathlib import Path

def create_icns_from_png(png_path, output_icns_path):
    """PNGファイルから.icnsファイルを生成"""
    
    if not os.path.exists(png_path):
        print(f"エラー: {png_path} が見つかりません")
        print("添付された画像を 'assets/icon.png' として保存してください")
        return False
    
    # iconsetフォルダを作成
    iconset_path = "assets/icon.iconset"
    os.makedirs(iconset_path, exist_ok=True)
    
    # 必要なサイズのアイコンを生成
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    
    print(f"アイコンを生成中: {png_path} -> {output_icns_path}")
    
    for size, filename in sizes:
        output_path = os.path.join(iconset_path, filename)
        cmd = [
            "sips",
            "-z", str(size), str(size),
            png_path,
            "--out", output_path
        ]
        print(f"  生成: {size}x{size} -> {filename}")
        subprocess.run(cmd, check=True, capture_output=True)
    
    # .icnsファイルを生成
    print(f"\n.icnsファイルを生成中...")
    cmd = ["iconutil", "-c", "icns", iconset_path, "-o", output_icns_path]
    subprocess.run(cmd, check=True)
    
    print(f"✓ 完成: {output_icns_path}")
    
    # iconsetフォルダを削除
    import shutil
    shutil.rmtree(iconset_path)
    
    return True

if __name__ == "__main__":
    png_path = "assets/icon.png"
    icns_path = "assets/icon.icns"
    
    print("=" * 60)
    print("PDF Font Changer with OCR - アイコン生成ツール")
    print("=" * 60)
    print()
    
    if create_icns_from_png(png_path, icns_path):
        print("\n✅ アイコンファイルの生成が完了しました")
        print(f"   {icns_path}")
        print("\n次のステップ:")
        print("   1. PyInstallerの.specファイルにアイコンを設定")
        print("   2. アプリを再ビルド")
    else:
        print("\n❌ アイコンファイルの生成に失敗しました")
        print("\n手順:")
        print("   1. 添付された画像を 'assets/icon.png' として保存")
        print("   2. このスクリプトを再実行")
