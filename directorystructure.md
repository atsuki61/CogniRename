# CogniRename ディレクトリ構成

## プロジェクト規模

- **対象**: 200 人・7000 枚写真（学習済み 2000 枚 + 処理対象 5000 枚）
- **用途**: 個人写真管理・顔認識自動リネーム

---

CogniRename/ # ルート（＝リポジトリ直下）
├─ .cursor/ # Cursor 関連ファイル
│ ├─ rules/ # ルール・テンプレート格納場所
│ │ └─ global.mdc # リポジトリ全体に適用するテンプレート
│ └─ resources/ # 追加テンプレ or メタがあれば
│
├─ .spcestory/ # 拡張機能 "SpecStory" 用フォルダ（自動生成）
│ └─ history/ # 変更履歴など（プラグイン依存）
│
├─ src/ # Python パッケージは "src 配置" に統一
│ └─ cognirename/ # アプリ本体パッケージ ✅ 実装完了
│ ├─ **init**.py # パッケージ情報・バージョン ✅
│ ├─ config.py # 共通設定（DB パス・環境変数）✅
│ │
│ ├─ core/ # ★ ドメインロジック層 ✅ 実装完了
│ │ ├─ **init**.py ✅
│ │ ├─ face_service.py # 顔検出 & 特徴量抽出 ✅
│ │ ├─ rename_service.py # リネーム規則 + 重複回避 ✅
│ │ └─ db.py # SQLite CRUD & スキーマ管理 ✅
│ │
│ ├─ cli/ # ★CUI：Click コマンド群 ✅ 実装完了
│ │ ├─ **init**.py ✅
│ │ └─ commands.py # register / rename / list-persons ✅
│ │
│ ├─ ui/ # ★GUI：Streamlit アプリ ✅ 実装完了
│ │ ├─ **init**.py ✅
│ │ ├─ app.py # streamlit run で起動 ✅
│ │ └─ components.py # 共通 UI パーツ ✅
│ │
│ └─ utils/ # 汎用ヘルパー ✅ 実装完了
│ ├─ **init**.py ✅
│ ├─ image_io.py # 画像処理・検証・変換 ✅
│ └─ path_helpers.py # パス操作・バックアップ ✅
│
├─ data/ # 実行時に生成／同梱する固定データ
│ ├─ faces.db # デフォルト SQLite（最初は空）
│ ├─ samples/ # サンプル画像
│ ├─ temp/ # 一時ファイル
│ └─ backup/ # バックアップファイル
│
├─ tests/ # pytest テスト ✅ 基本実装完了
│ ├─ **init**.py ✅
│ ├─ test_config.py # 設定テスト ✅
│ ├─ test_utils.py # ユーティリティテスト ✅
│ ├─ core/ # コアロジックテスト（追加予定）
│ ├─ cli/ # CLI テスト（追加予定）
│ └─ ui/ # GUI テスト（追加予定）
│
├─ docs/ # ドキュメント
│ ├─ README.md # プロジェクト概要 ✅
│ └─ architecture.md # アーキ図・仕様書（追加予定）
│
├─ scripts/ # 補助スクリプト ✅ 実装完了
│ ├─ setup_env.py # 環境セットアップ自動化 ✅
│ └─ build_docker.sh # Docker イメージ化（追加予定）
│
├─ .github/
│ └─ workflows/
│ └─ ci.yml # テスト + Lint CI（追加予定）
│
├─ pyproject.toml # ビルド設定（PEP 621 / poetry など）✅
├─ requirements.txt # 依存リスト（必要に応じて）✅
├─ .gitignore # Git 除外設定 ✅
├─ directorystructure.md # ★ このファイル ✅
└─ technologystack.md # 技術スタック一覧 ✅

## 実装状況

### ✅ 完了済み

- **コアロジック**: データベース管理・顔認識・リネーム処理
- **CLI**: Click ベースのコマンドライン インターフェース
- **GUI**: Streamlit ベースのウェブ インターフェース
- **ユーティリティ**: 画像処理・パス操作・検証機能
- **設定管理**: 共通設定・環境変数・パフォーマンス調整
- **ドキュメント**: README・技術スタック・ディレクトリ構成
- **セットアップ**: 自動環境構築スクリプト
- **基本テスト**: 設定・ユーティリティのテスト

### 🔄 追加予定

- **詳細テスト**: コアロジック・CLI・GUI の包括的テスト
- **CI/CD**: GitHub Actions による自動テスト・リント
- **Docker**: コンテナ化・配布用イメージ
- **アーキテクチャ文書**: 詳細設計・API 仕様書

### 📊 開発進捗

- **基本機能**: 100% 完了
- **GUI**: 100% 完了
- **CLI**: 100% 完了
- **テスト**: 30% 完了
- **ドキュメント**: 80% 完了
- **配布準備**: 60% 完了

---

## 使用可能な機能

### GUI 起動

```bash
streamlit run src/cognirename/ui/app.py
```

### CLI 使用

```bash
# パッケージインストール
pip install -e .

# 顔登録
cognirename register --name "田中太郎" --image-path "./face.jpg"

# 写真リネーム
cognirename rename --input-folder "./photos" --recursive --dry-run
```

### 環境セットアップ

```bash
python scripts/setup_env.py
```

---

**ステータス**: 基本機能実装完了・本格運用可能
