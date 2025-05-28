#!/usr/bin/env python3
"""
CogniRename 最小版アプリ起動スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# アプリを起動
if __name__ == "__main__":
    # Streamlitアプリを起動
    from cognirename.ui.app_minimal import main
    try:
        main()
    except Exception as e:
        print(f"アプリ起動エラー: {e}")
        import traceback
        traceback.print_exc() 