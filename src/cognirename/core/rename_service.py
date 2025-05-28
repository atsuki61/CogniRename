"""
CogniRename リネームサービス

顔認識結果に基づく画像ファイルのリネーム・重複回避機能を提供します。
命名規則: 名前1_名前2_名前3.拡張子
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import concurrent.futures
import time

from ..config import RENAME_CONFIG, PERFORMANCE_CONFIG, SUPPORTED_IMAGE_FORMATS
from .face_service import FaceService

logger = logging.getLogger(__name__)


class RenameService:
    """ファイルリネームサービスクラス
    
    顔認識結果に基づいて画像ファイルをリネームし、
    重複回避・バックアップ機能を提供します。
    """
    
    def __init__(self, face_service: Optional[FaceService] = None):
        """リネームサービス初期化
        
        Args:
            face_service: 顔認識サービス（未指定時は新規作成）
        """
        self.face_service = face_service or FaceService()
        self.name_separator = RENAME_CONFIG["name_separator"]
        self.duplicate_format = RENAME_CONFIG["duplicate_format"]
        self.max_workers = PERFORMANCE_CONFIG["max_workers"]
        
        logger.info("リネームサービス初期化完了")
    
    def generate_new_filename(self, names: List[str], original_path: Path) -> str:
        """人物名リストから新しいファイル名を生成
        
        Args:
            names: 人物名のリスト
            original_path: 元のファイルパス
            
        Returns:
            新しいファイル名（拡張子含む）
        """
        if not names:
            # 認識できなかった場合は元のファイル名を維持
            return original_path.name
        
        # 人物名を区切り文字で連結
        name_part = self.name_separator.join(names)
        
        # 拡張子を維持
        extension = original_path.suffix.lower()
        
        return f"{name_part}{extension}"
    
    def resolve_filename_conflict(self, target_path: Path) -> Path:
        """ファイル名重複を解決
        
        Args:
            target_path: 対象ファイルパス
            
        Returns:
            重複回避された新しいパス
        """
        if not target_path.exists():
            return target_path
        
        base_path = target_path.parent
        stem = target_path.stem
        suffix = target_path.suffix
        
        counter = 1
        while True:
            # (1), (2), ... の形式で連番付与
            duplicate_suffix = self.duplicate_format.format(n=counter)
            new_name = f"{stem}{duplicate_suffix}{suffix}"
            new_path = base_path / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            
            # 無限ループ防止（通常はありえない）
            if counter > 9999:
                timestamp = int(time.time())
                new_name = f"{stem}_{timestamp}{suffix}"
                return base_path / new_name
    
    def rename_single_file(self, image_path: Path, dry_run: bool = False) -> Dict[str, any]:
        """単一ファイルをリネーム
        
        Args:
            image_path: 画像ファイルパス
            dry_run: True時は実際のリネームを行わない
            
        Returns:
            処理結果の辞書
        """
        result = {
            "original_path": str(image_path),
            "success": False,
            "new_path": None,
            "identified_names": [],
            "error": None,
            "processing_time": 0
        }
        
        start_time = time.time()
        
        try:
            # 対応フォーマットチェック
            if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
                result["error"] = f"非対応フォーマット: {image_path.suffix}"
                return result
            
            # 顔認識処理
            identified_names = self.face_service.process_image_for_rename(image_path)
            result["identified_names"] = identified_names
            
            if not identified_names:
                result["error"] = "顔を認識できませんでした"
                return result
            
            # 新しいファイル名生成
            new_filename = self.generate_new_filename(identified_names, image_path)
            target_path = image_path.parent / new_filename
            
            # 重複回避
            if target_path != image_path:  # 名前が変わる場合のみ
                target_path = self.resolve_filename_conflict(target_path)
            
            result["new_path"] = str(target_path)
            
            # 実際のリネーム実行
            if not dry_run and target_path != image_path:
                image_path.rename(target_path)
                logger.info(f"リネーム完了: {image_path.name} → {target_path.name}")
            elif dry_run:
                logger.info(f"ドライラン: {image_path.name} → {target_path.name}")
            else:
                logger.debug(f"リネーム不要: {image_path.name}")
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"リネーム処理エラー: {str(e)}"
            result["error"] = error_msg
            logger.error(f"{error_msg} - {image_path.name}")
        
        finally:
            result["processing_time"] = time.time() - start_time
        
        return result
    
    def find_image_files(self, directory: Path, recursive: bool = False) -> List[Path]:
        """ディレクトリから画像ファイルを検索
        
        Args:
            directory: 検索対象ディレクトリ
            recursive: サブディレクトリも検索するか
            
        Returns:
            画像ファイルパスのリスト
        """
        if not directory.exists() or not directory.is_dir():
            logger.error(f"ディレクトリが見つかりません: {directory}")
            return []
        
        pattern = "**/*" if recursive else "*"
        image_files = []
        
        for file_path in directory.glob(pattern):
            if (file_path.is_file() and 
                file_path.suffix.lower() in SUPPORTED_IMAGE_FORMATS):
                image_files.append(file_path)
        
        logger.info(f"画像ファイル検索完了: {len(image_files)}件 - {directory}")
        return sorted(image_files)
    
    def rename_batch(self, 
                    image_files: List[Path], 
                    dry_run: bool = False,
                    progress_callback: Optional[callable] = None) -> Dict[str, any]:
        """複数ファイルの一括リネーム
        
        Args:
            image_files: 画像ファイルパスのリスト
            dry_run: True時は実際のリネームを行わない
            progress_callback: 進捗コールバック関数 (processed, total) → None
            
        Returns:
            処理結果の統計情報
        """
        total_files = len(image_files)
        if total_files == 0:
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "no_faces": 0,
                "results": [],
                "total_time": 0
            }
        
        logger.info(f"一括リネーム開始: {total_files}件 ({'ドライラン' if dry_run else '実行'})")
        start_time = time.time()
        
        results = []
        successful = 0
        failed = 0
        no_faces = 0
        
        # 並列処理でリネーム実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # タスク投入
            future_to_path = {
                executor.submit(self.rename_single_file, img_path, dry_run): img_path 
                for img_path in image_files
            }
            
            # 結果を順次処理
            for i, future in enumerate(concurrent.futures.as_completed(future_to_path)):
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
                    if "顔を認識できませんでした" in (result["error"] or ""):
                        no_faces += 1
                
                # 進捗コールバック
                if progress_callback:
                    progress_callback(i + 1, total_files)
        
        total_time = time.time() - start_time
        
        summary = {
            "total_files": total_files,
            "successful": successful,
            "failed": failed,
            "no_faces": no_faces,
            "results": results,
            "total_time": total_time,
            "avg_time_per_file": total_time / total_files if total_files > 0 else 0
        }
        
        logger.info(f"一括リネーム完了: 成功{successful}件, 失敗{failed}件, "
                   f"顔認識なし{no_faces}件 ({total_time:.1f}秒)")
        
        return summary
    
    def rename_directory(self, 
                        directory: Path, 
                        recursive: bool = False,
                        dry_run: bool = False,
                        progress_callback: Optional[callable] = None) -> Dict[str, any]:
        """ディレクトリ内の画像ファイルを一括リネーム
        
        Args:
            directory: 対象ディレクトリ
            recursive: サブディレクトリも処理するか
            dry_run: True時は実際のリネームを行わない
            progress_callback: 進捗コールバック関数
            
        Returns:
            処理結果の統計情報
        """
        # 画像ファイル検索
        image_files = self.find_image_files(directory, recursive)
        
        if not image_files:
            logger.warning(f"処理対象の画像ファイルが見つかりません: {directory}")
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "no_faces": 0,
                "results": [],
                "total_time": 0
            }
        
        # 一括リネーム実行
        return self.rename_batch(image_files, dry_run, progress_callback)
    
    def get_rename_preview(self, image_files: List[Path], max_preview: int = 10) -> List[Dict[str, any]]:
        """リネーム結果のプレビューを取得（実際のリネームは行わない）
        
        Args:
            image_files: 画像ファイルパスのリスト
            max_preview: プレビュー件数上限
            
        Returns:
            プレビュー結果のリスト
        """
        preview_files = image_files[:max_preview]
        previews = []
        
        for image_path in preview_files:
            try:
                identified_names = self.face_service.process_image_for_rename(image_path)
                new_filename = self.generate_new_filename(identified_names, image_path)
                
                previews.append({
                    "original_name": image_path.name,
                    "new_name": new_filename,
                    "identified_names": identified_names,
                    "has_faces": len(identified_names) > 0
                })
                
            except Exception as e:
                previews.append({
                    "original_name": image_path.name,
                    "new_name": image_path.name,
                    "identified_names": [],
                    "has_faces": False,
                    "error": str(e)
                })
        
        return previews 