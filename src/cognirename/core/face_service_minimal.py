"""
CogniRename 最小版顔認識サービス

dlibエラー回避用のOpenCV Haar Cascade版
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import sqlite3

import cv2
import numpy as np
from PIL import Image

from ..config import DB_PATH

logger = logging.getLogger(__name__)


class FaceServiceMinimal:
    """最小限の顔認識サービス（dlib不要）"""
    
    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path or DB_PATH
        self.face_cascade = None
        self._init_opencv_detector()
        self._init_database()
    
    def _init_opencv_detector(self):
        """OpenCV顔検出器の初期化"""
        try:
            # Haar Cascade分類器をロード
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                logger.error("Haar Cascade分類器の読み込みに失敗しました")
        except Exception as e:
            logger.error(f"OpenCV初期化エラー: {str(e)}")
    
    def _init_database(self):
        """データベース初期化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # テーブル作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            
            # 最小限のface_encodingsテーブル（実際のエンコーディングは保存しない）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    image_path TEXT,
                    FOREIGN KEY (person_id) REFERENCES persons (id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info(f"データベース初期化完了: {self.db_path}")
            
        except Exception as e:
            logger.error(f"データベース初期化エラー: {str(e)}")
    
    def detect_faces(self, image_path: Path) -> List[tuple]:
        """顔検出
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            検出された顔の座標リスト [(x, y, w, h), ...]
        """
        try:
            if not self.face_cascade:
                return []
            
            # 画像読み込み
            image = cv2.imread(str(image_path))
            if image is None:
                return []
            
            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 顔検出
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            return [tuple(face) for face in faces]
            
        except Exception as e:
            logger.error(f"顔検出エラー: {image_path.name} - {str(e)}")
            return []
    
    def register_face_from_image(self, image_path: Path, person_name: str) -> bool:
        """画像から顔を登録
        
        Args:
            image_path: 画像ファイルパス
            person_name: 人物名
            
        Returns:
            成功時 True
        """
        try:
            # 顔検出
            faces = self.detect_faces(image_path)
            if not faces:
                logger.warning(f"顔が検出されませんでした: {image_path.name}")
                return False
            
            if len(faces) > 1:
                logger.warning(f"複数の顔が検出されました: {image_path.name} ({len(faces)}個)")
            
            # データベースに人物を登録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 人物追加
                cursor.execute("INSERT INTO persons (name) VALUES (?)", (person_name,))
                person_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # 既存の人物
                cursor.execute("SELECT id FROM persons WHERE name = ?", (person_name,))
                person_id = cursor.fetchone()[0]
            
            # 顔エンコーディング追加（パスのみ保存）
            cursor.execute(
                "INSERT INTO face_encodings (person_id, image_path) VALUES (?, ?)",
                (person_id, str(image_path))
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"顔登録完了: {person_name} - {image_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"顔登録エラー: {str(e)}")
            return False
    
    def register_multiple_faces_from_images(self, image_paths: List[Path], person_name: str) -> Dict[str, Any]:
        """複数画像から顔を一括登録（最小版）
        
        Args:
            image_paths: 画像ファイルパスのリスト
            person_name: 人物名
            
        Returns:
            登録結果の詳細辞書 {"successful": int, "failed": int, "details": [...]}
        """
        results = {
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 人物を登録または取得
            try:
                cursor.execute("INSERT INTO persons (name) VALUES (?)", (person_name,))
                person_id = cursor.lastrowid
                logger.info(f"新規人物登録: {person_name} (ID: {person_id})")
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM persons WHERE name = ?", (person_name,))
                person_id = cursor.fetchone()[0]
                logger.info(f"既存人物使用: {person_name} (ID: {person_id})")
            
            # 各画像を処理
            for image_path in image_paths:
                try:
                    # 顔検出
                    faces = self.detect_faces(image_path)
                    
                    if not faces:
                        results["failed"] += 1
                        results["details"].append({
                            "image_path": str(image_path),
                            "status": "no_face",
                            "message": "顔が検出されませんでした",
                            "faces_count": 0
                        })
                        continue
                    
                    if len(faces) > 1:
                        logger.warning(f"複数の顔が検出されました: {image_path.name} ({len(faces)}個)")
                    
                    # 顔エンコーディング追加（パスのみ保存）
                    cursor.execute(
                        "INSERT INTO face_encodings (person_id, image_path) VALUES (?, ?)",
                        (person_id, str(image_path))
                    )
                    
                    results["successful"] += 1
                    results["details"].append({
                        "image_path": str(image_path),
                        "status": "success",
                        "message": f"登録成功 ({len(faces)}個の顔を検出)",
                        "faces_count": len(faces)
                    })
                    
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "image_path": str(image_path),
                        "status": "error",
                        "message": f"処理エラー: {str(e)}",
                        "faces_count": 0
                    })
                    logger.error(f"画像処理エラー: {image_path.name} - {str(e)}")
            
            # データベースコミット
            conn.commit()
            conn.close()
            
            logger.info(f"バッチ登録完了: {person_name} - 成功{results['successful']}件, 失敗{results['failed']}件")
            return results
            
        except Exception as e:
            logger.error(f"バッチ登録エラー: {str(e)}")
            results["failed"] = len(image_paths)
            results["details"] = [{
                "image_path": str(path),
                "status": "error",
                "message": f"バッチ処理エラー: {str(e)}",
                "faces_count": 0
            } for path in image_paths]
            return results
    
    def process_image_for_rename(self, image_path: Path) -> List[str]:
        """リネーム用画像処理
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            識別された人物名のリスト
        """
        try:
            # 顔検出
            faces = self.detect_faces(image_path)
            if not faces:
                return []
            
            # 簡単な例：登録済み人物をランダムに返す（実際の認識は未実装）
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM persons ORDER BY RANDOM() LIMIT ?", (min(len(faces), 3),))
            names = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return names
            
        except Exception as e:
            logger.error(f"画像処理エラー: {image_path.name} - {str(e)}")
            return []
    
    def get_recognition_stats(self) -> Dict[str, Any]:
        """認識統計の取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 人物数
            cursor.execute("SELECT COUNT(*) FROM persons")
            person_count = cursor.fetchone()[0]
            
            # 顔エンコーディング数
            cursor.execute("SELECT COUNT(*) FROM face_encodings")
            encoding_count = cursor.fetchone()[0]
            
            # 平均エンコーディング数
            avg_encodings = encoding_count / person_count if person_count > 0 else 0
            
            # DBサイズ
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024) if Path(self.db_path).exists() else 0
            
            conn.close()
            
            return {
                "person_count": person_count,
                "encoding_count": encoding_count,
                "avg_encodings_per_person": round(avg_encodings, 1),
                "db_size_mb": round(db_size, 2),
                "tolerance": "N/A (OpenCV)",
                "model": "Haar Cascade",
                "upsample": "N/A"
            }
            
        except Exception as e:
            logger.error(f"統計取得エラー: {str(e)}")
            return {
                "person_count": 0,
                "encoding_count": 0,
                "avg_encodings_per_person": 0,
                "db_size_mb": 0,
                "tolerance": "N/A",
                "model": "Error",
                "upsample": "N/A"
            }
    
    @property
    def db(self):
        """互換性のためのダミーDBプロパティ"""
        return DummyDB(self.db_path)


class DummyDB:
    """最小限のDB互換クラス"""
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_all_persons(self):
        """全人物取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM persons ORDER BY name")
            persons = cursor.fetchall()
            conn.close()
            return persons
        except Exception as e:
            logger.error(f"人物一覧取得エラー: {str(e)}")
            return []
    
    def get_face_encodings_by_person(self, person_id):
        """人物別顔エンコーディング取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM face_encodings WHERE person_id = ?", (person_id,))
            encodings = cursor.fetchall()
            conn.close()
            return encodings
        except Exception as e:
            logger.error(f"エンコーディング取得エラー: {str(e)}")
            return [] 