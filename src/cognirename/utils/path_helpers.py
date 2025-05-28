"""
CogniRename パスヘルパー

ファイルパス操作・検索・バックアップ・安全処理機能を提供します。
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Generator, Dict
import tempfile
import time

from ..config import SUPPORTED_IMAGE_FORMATS

logger = logging.getLogger(__name__)


def find_images_recursive(directory: Path, max_depth: Optional[int] = None) -> Generator[Path, None, None]:
    """再帰的画像ファイル検索
    
    Args:
        directory: 検索ディレクトリ
        max_depth: 最大検索深度（None で無制限）
        
    Yields:
        見つかった画像ファイルパス
    """
    if not directory.exists() or not directory.is_dir():
        logger.warning(f"ディレクトリが見つかりません: {directory}")
        return
    
    def _search_directory(current_dir: Path, current_depth: int = 0):
        try:
            for item in current_dir.iterdir():
                if item.is_file():
                    # 画像ファイルかチェック
                    if item.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
                        yield item
                elif item.is_dir():
                    # 深度制限チェック
                    if max_depth is None or current_depth < max_depth:
                        yield from _search_directory(item, current_depth + 1)
        except PermissionError:
            logger.warning(f"アクセス権限がありません: {current_dir}")
        except Exception as e:
            logger.error(f"ディレクトリ検索エラー: {current_dir} - {str(e)}")
    
    yield from _search_directory(directory)


def create_backup_path(original_path: Path, backup_dir: Optional[Path] = None) -> Path:
    """バックアップファイルパスの生成
    
    Args:
        original_path: 元ファイルパス
        backup_dir: バックアップディレクトリ（None時は元ディレクトリ）
        
    Returns:
        バックアップファイルパス
    """
    if backup_dir is None:
        backup_dir = original_path.parent
    
    # タイムスタンプ付きファイル名
    timestamp = int(time.time())
    stem = original_path.stem
    suffix = original_path.suffix
    
    backup_filename = f"{stem}_backup_{timestamp}{suffix}"
    return backup_dir / backup_filename


def safe_rename(source: Path, destination: Path, create_backup: bool = True) -> bool:
    """安全なファイルリネーム
    
    Args:
        source: 元ファイルパス
        destination: 新ファイルパス
        create_backup: バックアップ作成フラグ
        
    Returns:
        成功時 True
    """
    try:
        if not source.exists():
            logger.error(f"元ファイルが見つかりません: {source}")
            return False
        
        # バックアップ作成
        backup_path = None
        if create_backup and destination.exists():
            backup_path = create_backup_path(destination)
            shutil.copy2(destination, backup_path)
            logger.info(f"バックアップ作成: {backup_path}")
        
        # リネーム実行
        source.rename(destination)
        logger.info(f"リネーム完了: {source.name} → {destination.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"リネームエラー: {source.name} → {destination.name} - {str(e)}")
        
        # バックアップから復元
        if backup_path and backup_path.exists():
            try:
                shutil.move(backup_path, destination)
                logger.info("バックアップから復元しました")
            except Exception as restore_error:
                logger.error(f"復元エラー: {str(restore_error)}")
        
        return False


def ensure_directory_exists(directory: Path) -> bool:
    """ディレクトリ存在確認・作成
    
    Args:
        directory: ディレクトリパス
        
    Returns:
        成功時 True
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"ディレクトリ作成エラー: {directory} - {str(e)}")
        return False


def get_unique_filename(base_path: Path) -> Path:
    """一意なファイル名の生成
    
    Args:
        base_path: ベースファイルパス
        
    Returns:
        一意なファイルパス
    """
    if not base_path.exists():
        return base_path
    
    directory = base_path.parent
    stem = base_path.stem
    suffix = base_path.suffix
    
    counter = 1
    while True:
        new_name = f"{stem}({counter}){suffix}"
        new_path = directory / new_name
        
        if not new_path.exists():
            return new_path
        
        counter += 1
        
        # 無限ループ防止
        if counter > 9999:
            timestamp = int(time.time())
            new_name = f"{stem}_{timestamp}{suffix}"
            return directory / new_name


def clean_filename(filename: str) -> str:
    """ファイル名の無効文字除去
    
    Args:
        filename: 元ファイル名
        
    Returns:
        クリーンなファイル名
    """
    # Windows/Unix 両対応の無効文字
    invalid_chars = '<>:"/\\|?*'
    
    cleaned = filename
    for char in invalid_chars:
        cleaned = cleaned.replace(char, '_')
    
    # 連続するアンダースコアを単一化
    while '__' in cleaned:
        cleaned = cleaned.replace('__', '_')
    
    # 先頭・末尾のピリオドとスペースを除去
    cleaned = cleaned.strip('. ')
    
    # 空文字列の場合はデフォルト名
    if not cleaned:
        cleaned = "unnamed"
    
    return cleaned


def calculate_directory_size(directory: Path) -> Dict[str, int]:
    """ディレクトリサイズ計算
    
    Args:
        directory: ディレクトリパス
        
    Returns:
        サイズ情報の辞書
    """
    total_size = 0
    file_count = 0
    dir_count = 0
    
    try:
        for item in directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
    except Exception as e:
        logger.error(f"サイズ計算エラー: {directory} - {str(e)}")
    
    return {
        "total_bytes": total_size,
        "total_mb": round(total_size / (1024 * 1024), 2),
        "file_count": file_count,
        "dir_count": dir_count
    }


def create_temp_copy(original_path: Path) -> Optional[Path]:
    """一時ファイルコピーの作成
    
    Args:
        original_path: 元ファイルパス
        
    Returns:
        一時ファイルパスまたは None
    """
    try:
        with tempfile.NamedTemporaryFile(
            suffix=original_path.suffix,
            delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
        
        shutil.copy2(original_path, temp_path)
        logger.debug(f"一時ファイル作成: {temp_path}")
        
        return temp_path
        
    except Exception as e:
        logger.error(f"一時ファイル作成エラー: {original_path.name} - {str(e)}")
        return None


def cleanup_temp_files(temp_paths: List[Path]) -> None:
    """一時ファイルのクリーンアップ
    
    Args:
        temp_paths: 一時ファイルパスのリスト
    """
    for temp_path in temp_paths:
        try:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"一時ファイル削除: {temp_path}")
        except Exception as e:
            logger.warning(f"一時ファイル削除失敗: {temp_path} - {str(e)}")


def organize_files_by_extension(directory: Path) -> Dict[str, List[Path]]:
    """拡張子別ファイル整理
    
    Args:
        directory: 対象ディレクトリ
        
    Returns:
        拡張子別ファイル辞書
    """
    files_by_ext = {}
    
    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext not in files_by_ext:
                    files_by_ext[ext] = []
                files_by_ext[ext].append(file_path)
    except Exception as e:
        logger.error(f"ファイル整理エラー: {directory} - {str(e)}")
    
    return files_by_ext


def validate_path_safety(path: Path, base_directory: Path) -> bool:
    """パス安全性の検証（ディレクトリトラバーサル対策）
    
    Args:
        path: 検証対象パス
        base_directory: ベースディレクトリ
        
    Returns:
        安全時 True
    """
    try:
        # 絶対パスに解決
        resolved_path = path.resolve()
        resolved_base = base_directory.resolve()
        
        # ベースディレクトリ内かチェック
        return str(resolved_path).startswith(str(resolved_base))
        
    except Exception as e:
        logger.warning(f"パス安全性検証エラー: {path} - {str(e)}")
        return False 