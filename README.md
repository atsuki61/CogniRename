# 🔍 CogniRename

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Face Recognition](https://img.shields.io/badge/AI-Face%20Recognition-orange.svg)](https://github.com/ageitgey/face_recognition)

**顔認識による写真自動リネームツール**

大量の写真を顔認識技術で自動的にリネームし、整理を効率化するツールです。200 人・7000 枚規模の個人写真管理に対応しています。

## ✨ 特徴

- 🎯 **高精度顔認識**: `face_recognition` ライブラリによる高精度な顔検出・照合
- ⚡ **大量処理対応**: 並列処理による高速な一括リネーム（5000 枚/30 分）
- 🖥️ **CUI/GUI 両対応**: コマンドライン・Streamlit GUI どちらでも利用可能
- 📊 **200 人規模対応**: 大規模な人物データベースでも効率的に処理
- 🔒 **プライバシー重視**: 完全ローカル処理・顔特徴量のみ保存
- 🛠️ **柔軟な設定**: 命名規則・認識精度の調整可能

## 🚀 クイックスタート

### インストール

```bash
# リポジトリクローン
git clone https://github.com/cognirename/cognirename.git
cd cognirename

# 依存関係インストール
pip install -r requirements.txt

# パッケージインストール（開発モード）
pip install -e .
```

### GUI 版を起動

```bash
streamlit run src/cognirename/ui/app.py
```

ブラウザで `http://localhost:8501` にアクセス

### CLI 版を使用

```bash
# 顔登録
cognirename register --name "田中太郎" --image-path "./photos/tanaka.jpg"

# 写真リネーム（ドライラン）
cognirename rename --input-folder "./photos" --recursive --dry-run

# 実際のリネーム実行
cognirename rename --input-folder "./photos" --recursive

# 登録人物一覧
cognirename list-persons
```

## 📖 使い方

### 1. 顔登録

事前に人物の顔画像を登録します：

**GUI 版:**

1. 「顔登録」タブを開く
2. 顔画像をアップロード
3. 人物名を入力
4. 「顔を登録」をクリック

**CLI 版:**

```bash
cognirename register --name "佐藤花子" --image-path "./faces/sato.jpg"
```

### 2. 写真リネーム

登録済みの人物が写った写真を自動リネーム：

**GUI 版:**

1. 「写真リネーム」タブを開く
2. リネームする画像をアップロード
3. プレビューで確認
4. 「リネーム実行」をクリック

**CLI 版:**

```bash
# プレビュー確認
cognirename preview --input-folder "./photos" --max-preview 5

# 実際のリネーム
cognirename rename --input-folder "./photos" --recursive
```

### 3. 結果例

```
元ファイル名: IMG_20231201_001.jpg
↓
新ファイル名: 田中太郎_佐藤花子_山田次郎.jpg
```

## ⚙️ 設定

### 顔認識パラメータ

`src/cognirename/config.py` で調整可能：

```python
FACE_RECOGNITION_CONFIG = {
    "tolerance": 0.6,  # 類似度閾値（小さいほど厳格）
    "model": "hog",    # 検出モデル（hog/cnn）
    "upsample": 1,     # アップサンプル回数
}
```

### リネーム設定

```python
RENAME_CONFIG = {
    "max_names_per_file": 3,     # 1ファイルあたり最大人数
    "name_separator": "_",       # 名前区切り文字
    "duplicate_format": "({n})", # 重複時連番フォーマット
}
```

## 🏗️ アーキテクチャ

```
src/cognirename/
├── core/              # コアロジック
│   ├── db.py         # データベース管理
│   ├── face_service.py    # 顔認識サービス
│   └── rename_service.py  # リネームサービス
├── cli/              # コマンドライン
│   └── commands.py   # Click コマンド
├── ui/               # GUI
│   ├── app.py        # Streamlit アプリ
│   └── components.py # UI コンポーネント
├── utils/            # ユーティリティ
│   ├── image_io.py   # 画像処理
│   └── path_helpers.py   # パス操作
└── config.py         # 設定管理
```

## 📊 パフォーマンス

### 処理速度目安（CPU: 中程度）

| 処理               | 目標時間      | 備考           |
| ------------------ | ------------- | -------------- |
| 顔検出・特徴量抽出 | 1 ～ 3 秒/枚  | 画像サイズ依存 |
| DB 照合（200 人）  | 0.1 秒/顔     | NumPy 最適化   |
| リネーム処理       | 5000 枚/30 分 | 並列処理時     |

### メモリ使用量

- **通常時**: 100MB 以下
- **大量処理時**: 500MB 以下（バッチサイズ制御）

## 🔧 開発

### 環境セットアップ

```bash
# 開発依存関係インストール
pip install -r requirements.txt -e ".[dev]"

# コードフォーマット
black src/ tests/

# 静的解析
flake8 src/
mypy src/

# テスト実行
pytest tests/
```

### ディレクトリ構成

```
CogniRename/
├── src/cognirename/    # メインパッケージ
├── tests/              # テストコード
├── docs/               # ドキュメント
├── data/               # データファイル（DB等）
├── scripts/            # 補助スクリプト
├── requirements.txt    # 依存関係
├── pyproject.toml     # パッケージ設定
└── README.md          # このファイル
```

## 📋 対応フォーマット

### 入力画像

- **主要**: JPEG, PNG, WebP, JFIF
- **その他**: BMP, TIFF, TIF
- **制限**: 最大 50MB/ファイル

### 出力

- **命名規則**: `名前1_名前2_名前3.拡張子`
- **重複回避**: `ファイル名(1).拡張子` 形式
- **文字制限**: OS 対応安全文字のみ

## 🛡️ プライバシー・セキュリティ

- ✅ **完全ローカル処理** - クラウドアップロード無し
- ✅ **顔特徴量のみ保存** - 元画像は保持しない
- ✅ **個人利用想定** - 商用利用は非推奨
- ⚠️ **肖像権配慮** - 適切な利用権限を確保してください

## 🔍 トラブルシューティング

### よくある問題

**Q: 顔を認識できない**

- A: 画像が鮮明か、顔がはっきり写っているか確認
- A: `tolerance` 値を調整（0.4-0.8）

**Q: 処理が遅い**

- A: `max_workers` 数を調整
- A: 画像サイズを縮小

**Q: dlib インストール エラー**

- A: Visual Studio Build Tools をインストール（Windows）
- A: cmake をインストール

### ログ確認

```bash
# 詳細ログ有効化
cognirename --verbose rename --input-folder "./photos"
```

## 🤝 コントリビューション

1. Fork このリポジトリ
2. フィーチャーブランチ作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエスト作成

## 📜 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## 🙏 謝辞

- [face_recognition](https://github.com/ageitgey/face_recognition) - 顔認識ライブラリ
- [dlib](http://dlib.net/) - 機械学習ライブラリ
- [Streamlit](https://streamlit.io/) - GUI フレームワーク
- [Click](https://click.palletsprojects.com/) - CLI フレームワーク

## 📞 サポート

- 💬 GitHub Issues で質問・バグ報告
- 📖 [Wiki](../../wiki) で詳細ドキュメント
- ⭐ 役に立ったらスターをお願いします！

---

<p align="center">
Made with ❤️ for efficient photo management
</p>
