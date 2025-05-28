"""
ユーティリティ関数のテスト
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from PIL import Image

from cognirename.utils.path_helpers import (
    clean_filename,
    get_unique_filename,
    validate_path_safety
)
from cognirename.utils.image_io import (
    validate_image_file,
    get_image_info
)


class TestPathHelpers:
    """パスヘルパー関数のテスト"""
    
    def test_clean_filename(self):
        """ファイル名クリーニングのテスト"""
        # 無効文字の置換
        assert clean_filename("test<file>name") == "test_file_name"
        assert clean_filename("file:with|invalid*chars") == "file_with_invalid_chars"
        
        # 連続アンダースコアの処理
        assert clean_filename("test__multiple___underscores") == "test_multiple_underscores"
        
        # 先頭・末尾の処理
        assert clean_filename(" .test. ") == "test"
        
        # 空文字列の処理
        assert clean_filename("") == "unnamed"
        assert clean_filename("   ") == "unnamed"
    
    def test_get_unique_filename(self):
        """一意ファイル名生成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 元ファイルが存在しない場合
            test_file = temp_path / "test.txt"
            assert get_unique_filename(test_file) == test_file
            
            # 元ファイルが存在する場合
            test_file.touch()
            unique_file = get_unique_filename(test_file)
            assert unique_file.name == "test(1).txt"
            
            # 複数の重複
            (temp_path / "test(1).txt").touch()
            unique_file = get_unique_filename(test_file)
            assert unique_file.name == "test(2).txt"
    
    def test_validate_path_safety(self):
        """パス安全性検証のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            
            # 安全なパス
            safe_path = base_dir / "subfolder" / "file.txt"
            assert validate_path_safety(safe_path, base_dir) == True
            
            # 危険なパス（ディレクトリトラバーサル）
            dangerous_path = base_dir / ".." / "dangerous.txt"
            assert validate_path_safety(dangerous_path, base_dir) == False


class TestImageIO:
    """画像I/O関数のテスト"""
    
    def create_test_image(self, path: Path, size: tuple = (100, 100)) -> None:
        """テスト画像の作成"""
        image = Image.new("RGB", size, color="red")
        image.save(path)
    
    def test_validate_image_file(self):
        """画像ファイル検証のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 存在しないファイル
            non_existent = temp_path / "nonexistent.jpg"
            is_valid, error = validate_image_file(non_existent)
            assert not is_valid
            assert "見つかりません" in error
            
            # 有効な画像ファイル
            valid_image = temp_path / "valid.jpg"
            self.create_test_image(valid_image)
            is_valid, error = validate_image_file(valid_image)
            assert is_valid
            assert error is None
            
            # 非対応フォーマット
            invalid_format = temp_path / "test.xyz"
            invalid_format.touch()
            is_valid, error = validate_image_file(invalid_format)
            assert not is_valid
            assert "非対応フォーマット" in error
    
    def test_get_image_info(self):
        """画像情報取得のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # テスト画像作成
            test_image = temp_path / "test.jpg"
            self.create_test_image(test_image, (200, 150))
            
            # 画像情報取得
            info = get_image_info(test_image)
            
            assert info["filename"] == "test.jpg"
            assert info["dimensions"] == (200, 150)
            assert info["format"] == "JPEG"
            assert info["size_bytes"] > 0
            assert info["error"] is None


class TestUtils:
    """その他ユーティリティのテスト"""
    
    def test_imports(self):
        """主要モジュールのインポートテスト"""
        # インポートエラーが発生しないことを確認
        from cognirename.utils import image_io
        from cognirename.utils import path_helpers
        
        assert hasattr(image_io, 'validate_image_file')
        assert hasattr(path_helpers, 'clean_filename') 