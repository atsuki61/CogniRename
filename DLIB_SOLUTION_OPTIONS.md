# dlib 問題 根本解決提案書

## 現状の問題

### ❌ 発生している問題

- **dlib DLL 読み込みエラー**: `ImportError: DLL load failed while importing _dlib_pybind11`
- **Python 3.13 互換性**: Python 3.13 用のビルド済み wheel が限定的
- **Windows 環境**: 特に Windows 10 環境でのビルドエラー頻発

### ⚠️ 現在の回避策と限界

- **OpenCV Haar Cascade**: 基本的な顔検出のみ、認識精度は大幅に劣る
- **実写画像依存**: 描画画像や条件の悪い画像では検出困難
- **リアルタイム性**: face_recognition と比較して処理速度・精度ともに劣る

---

## 解決案オプション

### 🔧 オプション 1: dlib 問題の直接解決

#### A. 動作確認済み wheel 使用

```bash
# Python 3.12環境への変更
pyenv install 3.12.7
pyenv local 3.12.7

# 動作確認済みwheel
pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl
pip install face-recognition>=1.3.0
```

#### B. conda 環境使用

```bash
# conda環境でdlib安定版使用
conda create -n cognirename python=3.11
conda activate cognirename
conda install -c conda-forge dlib
pip install face-recognition streamlit click
```

#### C. Visual Studio Build Tools 使用

```bash
# Microsoft C++ Build Toolsインストール後
pip install cmake
pip install dlib --no-cache-dir
```

### 🚀 オプション 2: 代替高精度ライブラリ

#### A. MediaPipe (Google)

**メリット**: 高精度・高速・軽量、商用利用可能

```python
import mediapipe as mp

# 実装例
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

# 顔検出＋特徴点抽出
with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
    results = face_detection.process(image)
```

**依存関係**:

```bash
pip install mediapipe>=0.10.0
pip install opencv-python>=4.8.0
```

#### B. InsightFace (中国の OSS プロジェクト)

**メリット**: 最新の深層学習モデル、face_recognition より高精度

```python
import insightface

# 実装例
app = insightface.app.FaceAnalysis()
app.prepare(ctx_id=0, det_size=(640, 640))

# 顔認識＋特徴量抽出
faces = app.get(image)
```

**依存関係**:

```bash
pip install insightface>=0.7.0
pip install onnxruntime>=1.16.0
```

#### C. RetinaFace + ArcFace

**メリット**: 学術研究レベルの最高精度

```python
from retinaface import RetinaFace
import numpy as np

# 顔検出
faces = RetinaFace.detect_faces(image_path)

# 特徴量抽出
embeddings = RetinaFace.extract_faces(image_path, align=True)
```

**依存関係**:

```bash
pip install retina-face>=0.0.17
pip install tensorflow>=2.10.0
```

### 🔬 オプション 3: ハイブリッド手法

#### A. MediaPipe + 軽量特徴量

1. **顔検出**: MediaPipe（高精度・高速）
2. **特徴量抽出**: 顔のランドマーク位置ベース簡易特徴量
3. **類似度計算**: ユークリッド距離・コサイン類似度

#### B. OpenCV DNN + カスタム分類器

1. **顔検出**: OpenCV DNN（SSD MobileNet）
2. **顔認識**: 軽量 CNN 分類器（TensorFlow Lite）
3. **特徴量**: 128 次元エンベディング

---

## 推奨解決順序

### 🥇 第 1 優先: MediaPipe 採用

**理由**:

- Google の公式サポート、安定性が高い
- dlib 不要で依存関係がシンプル
- face_recognition に近い精度
- 商用利用可能

**実装工数**: 中程度（2-3 日）

### 🥈 第 2 優先: dlib 問題直接解決

**理由**:

- 既存コードの変更最小
- face_recognition の高精度をそのまま利用
- 実績のあるライブラリ

**実装工数**: 低（1 日）

### 🥉 第 3 優先: InsightFace 採用

**理由**:

- 最高レベルの精度
- 最新の深層学習技術
- 大規模データセット対応

**実装工数**: 高（1 週間）

---

## 具体的実装案 (MediaPipe)

### インストール

```bash
pip install mediapipe>=0.10.0
pip install numpy>=1.24.0
pip install opencv-python>=4.8.0
```

### 基本実装

```python
import mediapipe as mp
import cv2
import numpy as np

class FaceServiceMediaPipe:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh

    def detect_faces(self, image_path):
        image = cv2.imread(str(image_path))
        with self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            results = face_detection.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            if results.detections:
                return [(det.location_data.relative_bounding_box.xmin,
                        det.location_data.relative_bounding_box.ymin,
                        det.location_data.relative_bounding_box.width,
                        det.location_data.relative_bounding_box.height,
                        det.score[0]) for det in results.detections]
        return []

    def extract_face_landmarks(self, image_path):
        image = cv2.imread(str(image_path))
        with self.mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as face_mesh:
            results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                # 468個のランドマークから特徴量ベクトル生成
                feature_vector = self._landmarks_to_feature_vector(landmarks)
                return feature_vector
        return None
```

---

## 実装スケジュール

### Phase 1: 即座対応 (1-2 日)

1. MediaPipe 実装＋テスト
2. 既存システムとの統合
3. 基本動作確認

### Phase 2: 精度向上 (3-5 日)

1. 特徴量抽出アルゴリズム最適化
2. 類似度計算ロジック改良
3. 大量データでの性能テスト

### Phase 3: 本格運用 (1 週間)

1. 包括的テスト
2. パフォーマンス最適化
3. ドキュメント更新

---

## 期待される改善効果

| 項目       | 現状(Haar Cascade) | MediaPipe 版 | face_recognition(目標)  |
| ---------- | ------------------ | ------------ | ----------------------- |
| 顔検出精度 | 60-70%             | 90-95%       | 95%+                    |
| 顔認識精度 | 未実装             | 80-85%       | 95%+                    |
| 処理速度   | 3-5 秒/枚          | 1-2 秒/枚    | 2-3 秒/枚               |
| 依存関係   | OpenCV のみ        | MediaPipe    | dlib + face_recognition |
| 実装難易度 | 低                 | 中           | 低（問題解決すれば）    |

---

**推奨**: まず**MediaPipe 版の実装**を進め、並行して**dlib 問題の根本解決**を試行する併用アプローチを提案します。
