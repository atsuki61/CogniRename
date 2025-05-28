"""
設定モジュールのテスト
"""

import pytest
from pathlib import Path

from cognirename.config import (
    PROJECT_ROOT,
    DATA_DIR,
    DB_PATH,
    FACE_RECOGNITION_CONFIG,
    RENAME_CONFIG,
    SUPPORTED_IMAGE_FORMATS,
    PERFORMANCE_CONFIG
)


class TestConfig:
    """設定値のテスト"""
    
    def test_project_root_exists(self):
        """プロジェクトルートが存在する"""
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()
    
    def test_data_dir_path(self):
        """データディレクトリパスが正しい"""
        expected = PROJECT_ROOT / "data"
        assert DATA_DIR == expected
    
    def test_db_path_format(self):
        """データベースパスの形式が正しい"""
        assert str(DB_PATH).endswith("faces.db")
    
    def test_face_recognition_config(self):
        """顔認識設定が正しい"""
        assert "tolerance" in FACE_RECOGNITION_CONFIG
        assert "model" in FACE_RECOGNITION_CONFIG
        assert "upsample" in FACE_RECOGNITION_CONFIG
        
        # 値の範囲チェック
        assert 0.0 <= FACE_RECOGNITION_CONFIG["tolerance"] <= 1.0
        assert FACE_RECOGNITION_CONFIG["model"] in ["hog", "cnn"]
        assert FACE_RECOGNITION_CONFIG["upsample"] >= 0
    
    def test_rename_config(self):
        """リネーム設定が正しい"""
        assert "max_names_per_file" in RENAME_CONFIG
        assert "name_separator" in RENAME_CONFIG
        assert "duplicate_format" in RENAME_CONFIG
        
        # 値の妥当性チェック
        assert RENAME_CONFIG["max_names_per_file"] > 0
        assert isinstance(RENAME_CONFIG["name_separator"], str)
        assert "{n}" in RENAME_CONFIG["duplicate_format"]
    
    def test_supported_image_formats(self):
        """対応画像フォーマットが正しい"""
        assert isinstance(SUPPORTED_IMAGE_FORMATS, set)
        assert len(SUPPORTED_IMAGE_FORMATS) > 0
        
        # 主要フォーマットの存在確認
        expected_formats = {".jpg", ".jpeg", ".png", ".webp"}
        assert expected_formats.issubset(SUPPORTED_IMAGE_FORMATS)
    
    def test_performance_config(self):
        """パフォーマンス設定が正しい"""
        assert "max_image_size" in PERFORMANCE_CONFIG
        assert "batch_size" in PERFORMANCE_CONFIG
        assert "max_workers" in PERFORMANCE_CONFIG
        
        # 値の範囲チェック
        assert PERFORMANCE_CONFIG["max_image_size"] > 0
        assert PERFORMANCE_CONFIG["batch_size"] > 0
        assert PERFORMANCE_CONFIG["max_workers"] > 0 