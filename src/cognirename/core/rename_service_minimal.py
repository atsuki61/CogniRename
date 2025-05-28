"""
CogniRename リネームサービス（最小版）

dlibを使わない版のファイルリネーム処理
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..config import RENAME_CONFIG
from ..utils.path_helpers import clean_filename, get_unique_filename

logger = logging.getLogger(__name__)


class RenameServiceMinimal:
    """最小版リネームサービス"""
    
    def __init__(self, face_service=None):
        """
        Args:
            face_service: 顔認識サービス（最小版）
        """
        self.face_service = face_service
        self.max_names_per_file = RENAME_CONFIG["max_names_per_file"]
        self.name_separator = RENAME_CONFIG["name_separator"]
        self.duplicate_format = RENAME_CONFIG["duplicate_format"]
    
    def generate_new_filename(self, identified_names: List[str], original_path: Path) -> str:
        """新しいファイル名の生成
        
        Args:
            identified_names: 識別された人物名のリスト
            original_path: 元ファイルパス
            
        Returns:
            新しいファイル名
        """
        try:
            if not identified_names:
                return original_path.name
            
            # 名前数制限
            names_to_use = identified_names[:self.max_names_per_file]
            
            # ファイル名クリーニング
            clean_names = [clean_filename(name) for name in names_to_use]
            clean_names = [name for name in clean_names if name]  # 空文字除去
            
            if not clean_names:
                return original_path.name
            
            # 新ファイル名生成
            new_stem = self.name_separator.join(clean_names)
            new_filename = f"{new_stem}{original_path.suffix}"
            
            return new_filename
            
        except Exception as e:
            logger.error(f"ファイル名生成エラー: {str(e)}")
            return original_path.name
    
    def process_single_image(self, image_path: Path, dry_run: bool = True) -> Dict[str, Any]:
        """単一画像の処理
        
        Args:
            image_path: 画像ファイルパス
            dry_run: ドライランフラグ
            
        Returns:
            処理結果の辞書
        """
        result = {
            "original_path": image_path,
            "original_name": image_path.name,
            "new_name": image_path.name,
            "identified_names": [],
            "status": "no_change",
            "error": None
        }
        
        try:
            if not self.face_service:
                result["error"] = "顔認識サービスが利用できません"
                result["status"] = "error"
                return result
            
            # 顔認識処理
            identified_names = self.face_service.process_image_for_rename(image_path)
            result["identified_names"] = identified_names
            
            if identified_names:
                # 新ファイル名生成
                new_filename = self.generate_new_filename(identified_names, image_path)
                result["new_name"] = new_filename
                
                if new_filename != image_path.name:
                    result["status"] = "success"
                    
                    if not dry_run:
                        # 実際のリネーム（安全処理）
                        new_path = image_path.parent / new_filename
                        unique_path = get_unique_filename(new_path)
                        
                        # 実際のリネームは実装を簡略化
                        result["status"] = "dry_run_only"
                        result["error"] = "実際のリネームは未実装（ドライランのみ対応）"
                else:
                    result["status"] = "no_change"
            else:
                result["status"] = "no_faces"
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "error"
            logger.error(f"画像処理エラー: {image_path.name} - {str(e)}")
            return result
    
    def process_batch_images(self, image_paths: List[Path], dry_run: bool = True) -> Dict[str, Any]:
        """複数画像の一括処理
        
        Args:
            image_paths: 画像ファイルパスのリスト
            dry_run: ドライランフラグ
            
        Returns:
            一括処理結果の辞書
        """
        batch_result = {
            "total_files": len(image_paths),
            "successful": 0,
            "no_faces": 0,
            "no_change": 0,
            "failed": 0,
            "details": []
        }
        
        for image_path in image_paths:
            result = self.process_single_image(image_path, dry_run)
            batch_result["details"].append(result)
            
            # 統計更新
            if result["status"] == "success":
                batch_result["successful"] += 1
            elif result["status"] == "no_faces":
                batch_result["no_faces"] += 1
            elif result["status"] == "no_change":
                batch_result["no_change"] += 1
            else:
                batch_result["failed"] += 1
        
        return batch_result
    
    def validate_rename_operation(self, source_path: Path, target_name: str) -> tuple[bool, Optional[str]]:
        """リネーム操作の検証
        
        Args:
            source_path: 元ファイルパス
            target_name: 対象ファイル名
            
        Returns:
            (is_valid, error_message) のタプル
        """
        try:
            if not source_path.exists():
                return False, "元ファイルが存在しません"
            
            if not target_name or target_name.isspace():
                return False, "新ファイル名が無効です"
            
            # 無効文字チェック
            invalid_chars = '<>:"/\\|?*'
            if any(char in target_name for char in invalid_chars):
                return False, f"無効な文字が含まれています: {invalid_chars}"
            
            # パス長制限チェック（Windows）
            target_path = source_path.parent / target_name
            if len(str(target_path)) > 260:
                return False, "ファイルパスが長すぎます"
            
            return True, None
            
        except Exception as e:
            return False, f"検証エラー: {str(e)}" 