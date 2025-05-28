#!/usr/bin/env python3
"""
CogniRename 環境セットアップスクリプト

開発環境・依存関係のセットアップを自動化します。
"""

import subprocess
import sys
from pathlib import Path
import platform


def run_command(command: str, check: bool = True) -> bool:
    """コマンド実行
    
    Args:
        command: 実行するコマンド
        check: エラー時に例外を発生させるか
        
    Returns:
        成功時 True
    """
    print(f"実行中: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"エラー: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        return False


def check_python_version():
    """Python バージョンチェック"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11 以上が必要です")
        print(f"現在のバージョン: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python バージョン OK: {version.major}.{version.minor}.{version.micro}")
    return True


def check_system_requirements():
    """システム要件チェック"""
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"アーキテクチャ: {platform.machine()}")
    
    # Windows の場合は Visual Studio Build Tools の確認
    if platform.system() == "Windows":
        print("ℹ️  Windows 環境です")
        print("dlib インストールには Visual Studio Build Tools が必要です")
        print("https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022")


def install_dependencies():
    """依存関係のインストール"""
    print("\n📦 依存関係をインストールしています...")
    
    # pip アップデート
    if not run_command(f"{sys.executable} -m pip install --upgrade pip"):
        return False
    
    # requirements.txt からインストール
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    if requirements_file.exists():
        if not run_command(f"{sys.executable} -m pip install -r {requirements_file}"):
            return False
    else:
        print("❌ requirements.txt が見つかりません")
        return False
    
    return True


def install_package():
    """パッケージをエディタブルモードでインストール"""
    print("\n📦 CogniRename パッケージをインストールしています...")
    project_root = Path(__file__).parent.parent
    return run_command(f"{sys.executable} -m pip install -e {project_root}")


def create_data_directory():
    """データディレクトリの作成"""
    print("\n📁 データディレクトリを作成しています...")
    
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    
    # ディレクトリ作成
    data_dir.mkdir(exist_ok=True)
    (data_dir / "samples").mkdir(exist_ok=True)
    (data_dir / "temp").mkdir(exist_ok=True)
    (data_dir / "backup").mkdir(exist_ok=True)
    
    print(f"✅ データディレクトリ作成完了: {data_dir}")
    return True


def test_installation():
    """インストールテスト"""
    print("\n🧪 インストールをテストしています...")
    
    try:
        # パッケージインポートテスト
        import cognirename
        print(f"✅ パッケージインポート成功: v{cognirename.__version__}")
        
        # CLI コマンドテスト
        if run_command("cognirename --help", check=False):
            print("✅ CLI コマンド利用可能")
        
        # 主要ライブラリのインポートテスト
        import face_recognition
        import streamlit
        import click
        print("✅ 主要依存関係インポート成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        return False


def main():
    """メイン処理"""
    print("🔍 CogniRename 環境セットアップ")
    print("=" * 50)
    
    # Python バージョンチェック
    if not check_python_version():
        sys.exit(1)
    
    # システム要件チェック
    check_system_requirements()
    
    # 依存関係インストール
    if not install_dependencies():
        print("❌ 依存関係のインストールに失敗しました")
        sys.exit(1)
    
    # パッケージインストール
    if not install_package():
        print("❌ パッケージのインストールに失敗しました")
        sys.exit(1)
    
    # データディレクトリ作成
    if not create_data_directory():
        print("❌ データディレクトリの作成に失敗しました")
        sys.exit(1)
    
    # インストールテスト
    if not test_installation():
        print("❌ インストールテストに失敗しました")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 セットアップ完了！")
    print("\n使い方:")
    print("  GUI: streamlit run src/cognirename/ui/app.py")
    print("  CLI: cognirename --help")
    print("\n詳細は README.md を参照してください。")


if __name__ == "__main__":
    main() 