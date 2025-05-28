"""
CogniRename 画像 I/O ユーティリティ

画像読み込み・変換・検証・メタデータ処理機能を提供します。
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import io

from PIL import Image, ExifTags
import numpy as np

from ..config import SUPPORTED_IMAGE_FORMATS, PERFORMANCE_CONFIG

logger = logging.getLogger(__name__)


def validate_image_file(image_path: Path) -> Tuple[bool, Optional[str]]:
    """画像ファイルの検証
    
    Args:
        image_path: 画像ファイルパス
        
    Returns:
        (is_valid, error_message) のタプル
    """
    try:
        # ファイル存在確認
        if not image_path.exists():
            return False, "ファイルが見つかりません"
        
        if not image_path.is_file():
            return False, "ディレクトリです"
        
        # 拡張子チェック
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            return False, f"非対応フォーマット: {image_path.suffix}"
        
        # ファイルサイズチェック
        file_size = image_path.stat().st_size
        if file_size > PERFORMANCE_CONFIG["max_image_size"]:
            return False, f"ファイルサイズが大きすぎます: {file_size / (1024*1024):.1f}MB"
        
        # 画像として読み込み可能かチェック
        try:
            with Image.open(image_path) as img:
                img.verify()  # 画像の整合性チェック
        except Exception as e:
            return False, f"画像ファイルが破損しています: {str(e)}"
        
        return True, None
        
    except Exception as e:
        return False, f"検証エラー: {str(e)}"


def load_image_safely(image_path: Path) -> Optional[Image.Image]:
    """安全な画像読み込み
    
    Args:
        image_path: 画像ファイルパス
        
    Returns:
        PIL Image オブジェクトまたは None
    """
    try:
        is_valid, error_msg = validate_image_file(image_path)
        if not is_valid:
            logger.error(f"画像検証失敗: {image_path.name} - {error_msg}")
            return None
        
        # EXIF の自動回転を適用して読み込み
        image = Image.open(image_path)
        image = apply_exif_rotation(image)
        
        return image
        
    except Exception as e:
        logger.error(f"画像読み込みエラー: {image_path.name} - {str(e)}")
        return None


def apply_exif_rotation(image: Image.Image) -> Image.Image:
    """EXIF 情報に基づく画像回転の適用
    
    Args:
        image: PIL Image オブジェクト
        
    Returns:
        回転適用後の Image オブジェクト
    """
    try:
        exif = image.getexif()
        if exif is not None:
            for tag, value in exif.items():
                if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                    if value == 3:
                        image = image.rotate(180, expand=True)
                    elif value == 6:
                        image = image.rotate(270, expand=True)
                    elif value == 8:
                        image = image.rotate(90, expand=True)
                    break
    except Exception as e:
        logger.debug(f"EXIF 回転処理スキップ: {str(e)}")
    
    return image


def resize_image_for_display(image: Image.Image, max_size: Tuple[int, int] = (800, 600)) -> Image.Image:
    """表示用画像リサイズ
    
    Args:
        image: PIL Image オブジェクト
        max_size: 最大サイズ (width, height)
        
    Returns:
        リサイズ後の Image オブジェクト
    """
    try:
        # アスペクト比を維持してリサイズ
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    except Exception as e:
        logger.error(f"画像リサイズエラー: {str(e)}")
        return image


def convert_image_to_bytes(image: Image.Image, format: str = "JPEG", quality: int = 85) -> bytes:
    """画像をバイト列に変換
    
    Args:
        image: PIL Image オブジェクト
        format: 出力フォーマット
        quality: JPEG 品質 (1-100)
        
    Returns:
        画像のバイト列
    """
    try:
        # RGBA → RGB 変換（JPEG 対応）
        if format.upper() == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = rgb_image
        
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=quality, optimize=True)
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"画像変換エラー: {str(e)}")
        return b""


def get_image_info(image_path: Path) -> Dict[str, Any]:
    """画像ファイル情報の取得
    
    Args:
        image_path: 画像ファイルパス
        
    Returns:
        画像情報の辞書
    """
    info = {
        "filename": image_path.name,
        "size_bytes": 0,
        "size_mb": 0.0,
        "dimensions": None,
        "format": None,
        "mode": None,
        "has_exif": False,
        "error": None
    }
    
    try:
        # ファイルサイズ
        info["size_bytes"] = image_path.stat().st_size
        info["size_mb"] = round(info["size_bytes"] / (1024 * 1024), 2)
        
        # 画像情報
        with Image.open(image_path) as img:
            info["dimensions"] = img.size
            info["format"] = img.format
            info["mode"] = img.mode
            info["has_exif"] = bool(img.getexif())
            
    except Exception as e:
        info["error"] = str(e)
        logger.error(f"画像情報取得エラー: {image_path.name} - {str(e)}")
    
    return info


def create_thumbnail(image_path: Path, thumbnail_size: Tuple[int, int] = (150, 150)) -> Optional[bytes]:
    """サムネイル画像の生成
    
    Args:
        image_path: 画像ファイルパス
        thumbnail_size: サムネイルサイズ
        
    Returns:
        サムネイル画像のバイト列または None
    """
    try:
        image = load_image_safely(image_path)
        if image is None:
            return None
        
        # サムネイル生成
        image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        
        # バイト列に変換
        return convert_image_to_bytes(image, "JPEG", quality=90)
        
    except Exception as e:
        logger.error(f"サムネイル生成エラー: {image_path.name} - {str(e)}")
        return None


def batch_validate_images(image_paths: list[Path]) -> Dict[str, list]:
    """複数画像の一括検証
    
    Args:
        image_paths: 画像ファイルパスのリスト
        
    Returns:
        検証結果の辞書 {"valid": [...], "invalid": [...]}
    """
    valid_images = []
    invalid_images = []
    
    for image_path in image_paths:
        is_valid, error_msg = validate_image_file(image_path)
        if is_valid:
            valid_images.append(image_path)
        else:
            invalid_images.append({
                "path": image_path,
                "error": error_msg
            })
    
    logger.info(f"画像検証完了: 有効{len(valid_images)}件, 無効{len(invalid_images)}件")
    
    return {
        "valid": valid_images,
        "invalid": invalid_images
    } 