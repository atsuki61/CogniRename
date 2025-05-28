"""
CogniRename Streamlit アプリ

顔認識による写真自動リネームツールの GUI アプリケーション
streamlit run で起動
"""

import logging
from pathlib import Path

import streamlit as st

from .components import (
    init_session_state,
    display_system_info,
    display_face_registration_form,
    display_person_list,
    display_rename_interface,
    create_download_results
)
from ..config import LOG_CONFIG

# ログ設定
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)
logger = logging.getLogger(__name__)


def main():
    """メインアプリケーション"""
    
    # ページ設定
    st.set_page_config(
        page_title="CogniRename",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': "CogniRename - 顔認識による写真自動リネームツール"
        }
    )
    
    # カスタム CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 2rem;
            background: linear-gradient(90deg, #1f77b4, #ff7f0e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section-header {
            font-size: 1.5rem;
            font-weight: bold;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
        }
        .info-box {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # セッション状態初期化
    init_session_state()
    
    # メインヘッダー
    st.markdown('<h1 class="main-header">🔍 CogniRename</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">顔認識による写真自動リネームツール</p>', unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.header("📊 システム情報")
        display_system_info()
        
        st.markdown("---")
        
        # データベース設定
        st.header("⚙️ 設定")
        
        # データベースパス表示
        from ..config import DB_PATH
        st.text("データベース:")
        st.code(str(Path(DB_PATH).absolute()), language=None)
        
        # 顔認識設定表示
        from ..config import FACE_RECOGNITION_CONFIG
        st.text("顔認識設定:")
        for key, value in FACE_RECOGNITION_CONFIG.items():
            st.text(f"  {key}: {value}")
        
        st.markdown("---")
        
        # アプリ情報
        st.header("ℹ️ アプリ情報")
        from .. import __version__
        st.text(f"バージョン: {__version__}")
        st.text("対象規模: 200人・7000枚")
        
        # 使い方
        with st.expander("使い方"):
            st.markdown("""
            **顔登録タブ:**
            1. 顔画像をアップロード
            2. 人物名を入力
            3. 「顔を登録」をクリック
            
            **写真リネームタブ:**
            1. リネームする画像をアップロード
            2. プレビューで確認
            3. 「リネーム実行」をクリック
            
            **人物管理タブ:**
            - 登録済み人物の一覧表示
            """)
    
    # メインコンテンツ
    tab1, tab2, tab3 = st.tabs(["👤 顔登録", "🏷️ 写真リネーム", "📋 人物管理"])
    
    with tab1:
        display_face_registration_tab()
    
    with tab2:
        display_rename_tab()
    
    with tab3:
        display_person_management_tab()


def display_face_registration_tab():
    """顔登録タブの表示"""
    st.markdown('<div class="section-header">顔登録</div>', unsafe_allow_html=True)
    
    # 説明
    st.markdown("""
    <div class="info-box">
    <strong>💡 ヒント:</strong>
    <ul>
    <li>1つの顔がはっきりと写っている画像を使用してください</li>
    <li>同じ人物の複数の画像を登録すると認識精度が向上します</li>
    <li>正面、横顔、表情の違いなど、バリエーションを登録することをお勧めします</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 顔登録フォーム
    display_face_registration_form()


def display_rename_tab():
    """写真リネームタブの表示"""
    st.markdown('<div class="section-header">写真リネーム</div>', unsafe_allow_html=True)
    
    # 説明
    st.markdown("""
    <div class="info-box">
    <strong>💡 ヒント:</strong>
    <ul>
    <li>複数の画像を同時にアップロードできます</li>
    <li>認識された人物名でファイルがリネームされます（例: 田中太郎_佐藤花子.jpg）</li>
    <li>最初は「ドライラン」で結果を確認してから実行することをお勧めします</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # リネームインターフェース
    display_rename_interface()


def display_person_management_tab():
    """人物管理タブの表示"""
    st.markdown('<div class="section-header">人物管理</div>', unsafe_allow_html=True)
    
    # 説明
    st.markdown("""
    <div class="info-box">
    <strong>📋 登録人物一覧:</strong>
    現在データベースに登録されている人物と、それぞれの顔データ数を表示します。
    </div>
    """, unsafe_allow_html=True)
    
    # 人物一覧
    display_person_list()
    
    # 統計情報
    try:
        stats = st.session_state.face_service.get_recognition_stats()
        
        st.markdown('<div class="section-header">統計情報</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"""
            **データベース情報:**
            - 登録人数: {stats['person_count']}人
            - 顔特徴量: {stats['encoding_count']}件
            - 平均特徴量/人: {stats['avg_encodings_per_person']}件
            """)
        
        with col2:
            st.info(f"""
            **認識設定:**
            - 類似度閾値: {stats['tolerance']}
            - 検出モデル: {stats['model']}
            - アップサンプル: {stats['upsample']}
            """)
        
        # データベースサイズ
        if stats['db_size_mb'] > 0:
            st.metric("データベースサイズ", f"{stats['db_size_mb']} MB")
        
    except Exception as e:
        st.error(f"統計情報取得エラー: {str(e)}")


def run_app():
    """アプリケーション実行用エントリーポイント"""
    try:
        main()
    except Exception as e:
        logger.error(f"アプリケーションエラー: {str(e)}")
        st.error(f"アプリケーションエラーが発生しました: {str(e)}")
        st.info("ページを再読み込みしてください")


if __name__ == "__main__":
    run_app() 