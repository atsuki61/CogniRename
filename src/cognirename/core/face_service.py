"""
CogniRename 顔認識サービス

face_recognition ライブラリを使用した顔検出・特徴量抽出・照合機能を提供します。
対象規模: 200人規模での高精度認識・CPU最適化
"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import time

import face_recognition
import numpy as np
from PIL import Image

from ..config import FACE_RECOGNITION_CONFIG, PERFORMANCE_CONFIG
from .db import FaceDatabase

logger = logging.getLogger(__name__)


class FaceService:
    """顔認識サービスクラス
    
    顔検出・特徴量抽出・既知人物との照合機能を提供します。
    200人規模での効率的な処理を目指し、tolerance や model などの
    パラメータを最適化しています。
    """
    
    def __init__(self, db: Optional[FaceDatabase] = None):
        """顔認識サービス初期化
        
        Args:
            db: データベースインスタンス（未指定時は新規作成）
        """
        self.db = db or FaceDatabase()
        self.tolerance = FACE_RECOGNITION_CONFIG["tolerance"]
        self.model = FACE_RECOGNITION_CONFIG["model"]
        self.upsample = FACE_RECOGNITION_CONFIG["upsample"]
        
        # 既知顔データのキャッシュ
        self._known_encodings: List[np.ndarray] = []
        self._known_names: List[str] = []
        self._load_known_faces()
        
        logger.info(f"顔認識サービス初期化完了 - 既知人物: {len(self._known_names)}人")
    
    def _load_known_faces(self) -> None:
        """データベースから既知顔データを読み込みキャッシュ"""
        start_time = time.time()
        face_data = self.db.get_all_face_encodings()
        
        self._known_encodings = []
        self._known_names = []
        
        for person_id, name, encoding in face_data:
            self._known_encodings.append(encoding)
            self._known_names.append(name)
        
        load_time = time.time() - start_time
        logger.info(f"既知顔データ読み込み完了: {len(self._known_names)}人 ({load_time:.2f}秒)")
    
    def refresh_known_faces(self) -> None:
        """既知顔データの再読み込み（新規登録後に使用）"""
        self._load_known_faces()
    
    def detect_faces_in_image(self, image_path: Path) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """画像内の顔を検出し、特徴量と位置を返す
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            [(encoding, (top, right, bottom, left)), ...] のリスト
            
        Raises:
            FileNotFoundError: 画像ファイルが見つからない場合
            ValueError: 画像読み込みエラーの場合
        """
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # ファイルサイズチェック
        if image_path.stat().st_size > PERFORMANCE_CONFIG["max_image_size"]:
            raise ValueError(f"画像ファイルが大きすぎます: {image_path.stat().st_size / (1024*1024):.1f}MB")
        
        try:
            # 画像読み込み
            start_time = time.time()
            image = face_recognition.load_image_from_file(str(image_path))
            
            # 顔検出
            face_locations = face_recognition.face_locations(
                image, 
                number_of_times_to_upsample=self.upsample,
                model=self.model
            )
            
            if not face_locations:
                logger.debug(f"顔が検出されませんでした: {image_path.name}")
                return []
            
            # 特徴量抽出
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            detection_time = time.time() - start_time
            logger.debug(f"顔検出完了: {image_path.name} - {len(face_locations)}件 ({detection_time:.2f}秒)")
            
            return list(zip(face_encodings, face_locations))
            
        except Exception as e:
            logger.error(f"顔検出エラー: {image_path.name} - {str(e)}")
            raise ValueError(f"画像処理エラー: {str(e)}")
    
    def identify_faces(self, face_encodings: List[np.ndarray]) -> List[Optional[str]]:
        """顔特徴量から人物を識別
        
        Args:
            face_encodings: 顔特徴量のリスト
            
        Returns:
            識別された人物名のリスト（不明時は None）
        """
        if not self._known_encodings:
            logger.warning("既知顔データが登録されていません")
            return [None] * len(face_encodings)
        
        identified_names = []
        
        for encoding in face_encodings:
            # 既知顔との距離計算
            distances = face_recognition.face_distance(self._known_encodings, encoding)
            
            # 最も近い顔を特定
            min_distance_idx = np.argmin(distances)
            min_distance = distances[min_distance_idx]
            
            if min_distance <= self.tolerance:
                name = self._known_names[min_distance_idx]
                logger.debug(f"顔認識成功: {name} (距離: {min_distance:.3f})")
                identified_names.append(name)
            else:
                logger.debug(f"顔認識失敗: 最小距離 {min_distance:.3f} > 閾値 {self.tolerance}")
                identified_names.append(None)
        
        return identified_names
    
    def process_image_for_rename(self, image_path: Path) -> List[str]:
        """画像を処理してリネーム用の人物名リストを取得
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            識別された人物名のリスト（重複除去済み、最大3名）
        """
        try:
            # 顔検出・特徴量抽出
            face_data = self.detect_faces_in_image(image_path)
            if not face_data:
                return []
            
            # 顔認識
            encodings = [encoding for encoding, _ in face_data]
            identified_names = self.identify_faces(encodings)
            
            # 有効な名前のみ抽出・重複除去
            valid_names = [name for name in identified_names if name is not None]
            unique_names = list(dict.fromkeys(valid_names))  # 順序保持で重複除去
            
            # 最大3名まで制限
            from ..config import RENAME_CONFIG
            max_names = RENAME_CONFIG["max_names_per_file"]
            return unique_names[:max_names]
            
        except Exception as e:
            logger.error(f"画像処理エラー: {image_path.name} - {str(e)}")
            return []
    
    def register_face_from_image(self, image_path: Path, person_name: str) -> bool:
        """画像から顔を登録
        
        Args:
            image_path: 画像ファイルパス
            person_name: 人物名
            
        Returns:
            登録成功時 True
            
        Raises:
            ValueError: 顔が検出されない、複数顔がある場合
        """
        # 顔検出
        face_data = self.detect_faces_in_image(image_path)
        
        if not face_data:
            raise ValueError(f"顔が検出されませんでした: {image_path.name}")
        
        if len(face_data) > 1:
            raise ValueError(f"複数の顔が検出されました: {image_path.name} ({len(face_data)}件)")
        
        encoding, _ = face_data[0]
        
        try:
            # 人物をデータベースに追加（既存時は ID を取得）
            existing_person = self.db.get_person_by_name(person_name)
            if existing_person:
                person_id = existing_person[0]
                logger.info(f"既存人物に顔特徴量を追加: {person_name} (ID: {person_id})")
            else:
                person_id = self.db.add_person(person_name)
                logger.info(f"新規人物登録: {person_name} (ID: {person_id})")
            
            # 顔特徴量を追加
            self.db.add_face_encoding(person_id, encoding)
            
            # キャッシュ更新
            self.refresh_known_faces()
            
            logger.info(f"顔登録完了: {person_name} - {image_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"顔登録エラー: {person_name} - {str(e)}")
            return False
    
    def get_recognition_stats(self) -> Dict[str, any]:
        """認識統計情報の取得
        
        Returns:
            統計情報の辞書
        """
        db_stats = self.db.get_database_stats()
        
        return {
            **db_stats,
            "tolerance": self.tolerance,
            "model": self.model,
            "upsample": self.upsample,
            "cached_faces": len(self._known_names)
        } 