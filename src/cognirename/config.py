"""
CogniRename 共通設定

アプリケーション全体で使用する設定値・パス・環境変数を管理します。
"""

import os
from pathlib import Path

# プロジェクトルートディレクトリの取得
PROJECT_ROOT = Path(__file__).parent.parent.parent

# データディレクトリ
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# データベース設定
DEFAULT_DB_PATH = DATA_DIR / "faces.db"
DB_PATH = os.getenv("COGNIRENAME_DB_PATH", str(DEFAULT_DB_PATH))

# 顔認識設定
FACE_RECOGNITION_CONFIG = {
    "tolerance": 0.6,  # 200人規模で誤認識を抑制
    "model": "hog",    # CPU効率優先（GPU不要）
    "upsample": 1,     # 精度と速度のバランス
}

# リネーム設定
RENAME_CONFIG = {
    "max_names_per_file": 3,     # 1ファイルあたり最大3名まで
    "name_separator": "_",       # 名前区切り文字
    "duplicate_format": "({n})", # 重複時の連番フォーマット
}

# 対応画像フォーマット
SUPPORTED_IMAGE_FORMATS = {
    ".jpg", ".jpeg", ".png", ".webp", ".jfif", 
    ".bmp", ".tiff", ".tif"
}

# パフォーマンス設定
PERFORMANCE_CONFIG = {
    "max_image_size": 50 * 1024 * 1024,  # 50MB制限
    "batch_size": 10,                     # バッチ処理サイズ
    "max_workers": 4,                     # 並列処理スレッド数
}

# ログ設定
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
} 