"""
CogniRename データベース管理

SQLite を使用した顔データの永続化・CRUD 操作を提供します。
対象規模: 200人・顔特徴量データの高速検索対応
"""

import sqlite3
import pickle
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Any
from contextlib import contextmanager

import numpy as np

from ..config import DB_PATH

logger = logging.getLogger(__name__)


class FaceDatabase:
    """顔データベース管理クラス
    
    persons テーブルと face_encodings テーブルを管理し、
    顔特徴量の保存・検索・更新機能を提供します。
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """データベース初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """データベーススキーマの初期化"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # persons テーブル: 人物マスタ
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # face_encodings テーブル: 顔特徴量
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    encoding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (person_id) REFERENCES persons (id) ON DELETE CASCADE
                )
            """)
            
            # インデックス作成（検索高速化）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_face_encodings_person_id 
                ON face_encodings (person_id)
            """)
            
            conn.commit()
            logger.info(f"データベース初期化完了: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")  # 外部キー制約有効化
        try:
            yield conn
        finally:
            conn.close()
    
    def add_person(self, name: str) -> int:
        """人物を追加
        
        Args:
            name: 人物名
            
        Returns:
            追加された人物の ID
            
        Raises:
            ValueError: 重複する名前の場合
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO persons (name) VALUES (?)",
                    (name,)
                )
                conn.commit()
                person_id = cursor.lastrowid
                logger.info(f"人物追加: {name} (ID: {person_id})")
                return person_id
            except sqlite3.IntegrityError:
                raise ValueError(f"人物名 '{name}' は既に存在します")
    
    def get_person_by_name(self, name: str) -> Optional[Tuple[int, str]]:
        """名前で人物を検索
        
        Args:
            name: 人物名
            
        Returns:
            (person_id, name) または None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name FROM persons WHERE name = ?",
                (name,)
            )
            result = cursor.fetchone()
            return result if result else None
    
    def get_all_persons(self) -> List[Tuple[int, str]]:
        """全人物の取得
        
        Returns:
            [(person_id, name), ...] のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM persons ORDER BY name")
            return cursor.fetchall()
    
    def add_face_encoding(self, person_id: int, encoding: np.ndarray) -> int:
        """顔特徴量を追加
        
        Args:
            person_id: 人物 ID
            encoding: 顔特徴量 (NumPy 配列)
            
        Returns:
            追加された特徴量の ID
        """
        encoding_blob = pickle.dumps(encoding)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO face_encodings (person_id, encoding) VALUES (?, ?)",
                (person_id, encoding_blob)
            )
            conn.commit()
            encoding_id = cursor.lastrowid
            logger.debug(f"顔特徴量追加: person_id={person_id}, encoding_id={encoding_id}")
            return encoding_id
    
    def get_all_face_encodings(self) -> List[Tuple[int, str, np.ndarray]]:
        """全顔特徴量の取得
        
        Returns:
            [(person_id, name, encoding), ...] のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fe.person_id, p.name, fe.encoding
                FROM face_encodings fe
                JOIN persons p ON fe.person_id = p.id
                ORDER BY p.name
            """)
            
            results = []
            for person_id, name, encoding_blob in cursor.fetchall():
                encoding = pickle.loads(encoding_blob)
                results.append((person_id, name, encoding))
            
            return results
    
    def get_face_encodings_by_person(self, person_id: int) -> List[np.ndarray]:
        """指定人物の顔特徴量を取得
        
        Args:
            person_id: 人物 ID
            
        Returns:
            顔特徴量のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT encoding FROM face_encodings WHERE person_id = ?",
                (person_id,)
            )
            
            encodings = []
            for (encoding_blob,) in cursor.fetchall():
                encoding = pickle.loads(encoding_blob)
                encodings.append(encoding)
            
            return encodings
    
    def delete_person(self, person_id: int) -> bool:
        """人物削除（関連する顔特徴量も削除）
        
        Args:
            person_id: 人物 ID
            
        Returns:
            削除成功時 True
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM persons WHERE id = ?", (person_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"人物削除: person_id={person_id}")
            return deleted
    
    def get_database_stats(self) -> dict:
        """データベース統計情報の取得
        
        Returns:
            統計情報の辞書
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 人物数
            cursor.execute("SELECT COUNT(*) FROM persons")
            person_count = cursor.fetchone()[0]
            
            # 顔特徴量数
            cursor.execute("SELECT COUNT(*) FROM face_encodings")
            encoding_count = cursor.fetchone()[0]
            
            # 人物あたりの平均特徴量数
            cursor.execute("""
                SELECT AVG(encoding_count) FROM (
                    SELECT COUNT(*) as encoding_count 
                    FROM face_encodings 
                    GROUP BY person_id
                )
            """)
            avg_encodings = cursor.fetchone()[0] or 0
            
            return {
                "person_count": person_count,
                "encoding_count": encoding_count,
                "avg_encodings_per_person": round(avg_encodings, 2),
                "db_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2)
            } 