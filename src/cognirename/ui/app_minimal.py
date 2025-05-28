"""
CogniRename Streamlit アプリ（最小版）

dlibエラー回避用のOpenCV Haar Cascade版
"""

import logging
from pathlib import Path

import streamlit as st

# dlib不要版をインポート
from ..core.face_service_minimal import FaceServiceMinimal
from ..core.rename_service_minimal import RenameServiceMinimal
from ..config import LOG_CONFIG

# ログ設定
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)
logger = logging.getLogger(__name__)


def init_session_state():
    """セッション状態の初期化（最小版）"""
    if 'face_service' not in st.session_state:
        st.session_state.face_service = FaceServiceMinimal()
    
    if 'rename_service' not in st.session_state:
        st.session_state.rename_service = RenameServiceMinimal(st.session_state.face_service)


def main():
    """メインアプリケーション（最小版）"""
    
    # ページ設定
    st.set_page_config(
        page_title="CogniRename (最小版)",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # セッション状態初期化
    init_session_state()
    
    # メインヘッダー
    st.title("🔍 CogniRename (最小版)")
    st.markdown("**顔認識による写真自動リネームツール - OpenCV版**")
    
    # 警告表示
    st.warning("""
    ⚠️ **最小版について**
    
    この版では以下の制限があります：
    - OpenCV Haar Cascadeによる顔検出のみ（顔認識機能は制限付き）
    - dlib/face_recognitionライブラリは使用していません
    - 実際の顔認識精度は限定的です
    
    完全版をご利用の場合は、dlib依存関係の解決が必要です。
    """)
    
    # サイドバー
    with st.sidebar:
        st.header("📊 システム情報")
        try:
            stats = st.session_state.face_service.get_recognition_stats()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("登録人数", f"{stats['person_count']}人")
            with col2:
                st.metric("顔データ", f"{stats['encoding_count']}件")
            
            st.text(f"検出モデル: {stats['model']}")
            st.text(f"DBサイズ: {stats['db_size_mb']}MB")
            
        except Exception as e:
            st.error(f"システム情報取得エラー: {str(e)}")
        
        st.markdown("---")
        st.markdown("**技術情報:**")
        st.text("顔検出: OpenCV Haar Cascade")
        st.text("認識精度: 基本レベル")
    
    # メインコンテンツ
    tab1, tab2, tab3 = st.tabs(["👤 顔登録", "🏷️ 写真リネーム", "📋 人物管理"])
    
    with tab1:
        display_face_registration_tab()
    
    with tab2:
        display_rename_tab()
    
    with tab3:
        display_person_management_tab()


def display_face_registration_tab():
    """顔登録タブ（複数枚対応）"""
    st.subheader("👤 顔登録 (複数枚対応)")
    
    st.info("""
    **注意**: この版では顔検出のみ可能です。実際の顔認識精度は限定的です。
    **新機能**: 1人につき複数枚の画像を同時に登録できます。
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 人物名入力（先に配置）
        person_name = st.text_input(
            "人物名",
            placeholder="例: 田中太郎",
            help="複数枚の画像を登録する人物の名前を入力してください"
        )
        
        # 複数画像アップロード
        uploaded_files = st.file_uploader(
            "顔画像をアップロード（複数選択可能）",
            type=['jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help="同じ人物の顔が写っている画像を複数選択してください"
        )
        
        # 処理オプション
        st.markdown("**処理オプション:**")
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            continue_on_error = st.checkbox(
                "エラー時も継続",
                value=True,
                help="顔検出に失敗した画像があっても他の画像の処理を続行"
            )
        with col_opt2:
            show_preview = st.checkbox(
                "プレビュー表示",
                value=True,
                help="アップロード画像のプレビューを表示"
            )
        
        # 登録ボタン
        register_button = st.button(
            f"🔹 顔を登録 ({len(uploaded_files) if uploaded_files else 0}枚)",
            type="primary",
            disabled=not uploaded_files or not person_name.strip()
        )
    
    with col2:
        # アップロード画像のプレビュー
        if uploaded_files and show_preview:
            st.markdown("**プレビュー:**")
            for i, uploaded_file in enumerate(uploaded_files[:5]):  # 最大5枚まで表示
                try:
                    from PIL import Image
                    image = Image.open(uploaded_file)
                    st.image(
                        image, 
                        caption=f"{i+1}. {uploaded_file.name}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"画像{i+1}表示エラー: {str(e)}")
            
            if len(uploaded_files) > 5:
                st.info(f"他 {len(uploaded_files) - 5} 枚...")
    
    # 登録処理
    if register_button:
        if not uploaded_files:
            st.error("画像をアップロードしてください")
        elif not person_name.strip():
            st.error("人物名を入力してください")
        else:
            # バッチ処理開始
            st.markdown("---")
            st.subheader("📊 登録処理結果")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = {
                "successful": 0,
                "failed": 0,
                "details": []
            }
            
            for i, uploaded_file in enumerate(uploaded_files):
                # プログレス更新
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"処理中: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
                
                try:
                    # 一時ファイル保存
                    import tempfile
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{uploaded_file.name.split('.')[-1]}", 
                        delete=False
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        temp_path = Path(tmp_file.name)
                    
                    try:
                        # 顔登録処理
                        success = st.session_state.face_service.register_face_from_image(
                            temp_path, 
                            person_name.strip()
                        )
                        
                        if success:
                            results["successful"] += 1
                            results["details"].append({
                                "filename": uploaded_file.name,
                                "status": "success",
                                "message": "登録成功"
                            })
                        else:
                            results["failed"] += 1
                            results["details"].append({
                                "filename": uploaded_file.name,
                                "status": "no_face",
                                "message": "顔が検出されませんでした"
                            })
                            
                            # エラー時継続設定確認
                            if not continue_on_error:
                                st.error(f"❌ {uploaded_file.name}: 顔検出失敗のため処理を中断")
                                break
                                
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "filename": uploaded_file.name,
                            "status": "error",
                            "message": str(e)
                        })
                        
                        if not continue_on_error:
                            st.error(f"❌ {uploaded_file.name}: エラーのため処理を中断")
                            break
                            
                    finally:
                        # 一時ファイル削除
                        if temp_path.exists():
                            temp_path.unlink()
                            
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "filename": uploaded_file.name,
                        "status": "error",
                        "message": f"ファイル処理エラー: {str(e)}"
                    })
                    
                    if not continue_on_error:
                        st.error(f"❌ ファイル処理エラーのため処理を中断")
                        break
            
            # 最終結果表示
            progress_bar.progress(1.0)
            status_text.text("処理完了")
            
            st.markdown("### 📈 処理サマリー")
            col_res1, col_res2, col_res3 = st.columns(3)
            
            with col_res1:
                st.metric("✅ 成功", results["successful"])
            with col_res2:
                st.metric("❌ 失敗", results["failed"])
            with col_res3:
                st.metric("📊 処理率", f"{results['successful']/(len(uploaded_files))*100:.1f}%")
            
            # 詳細結果
            st.markdown("### 📋 詳細結果")
            for detail in results["details"]:
                if detail["status"] == "success":
                    st.success(f"✅ {detail['filename']}: {detail['message']}")
                elif detail["status"] == "no_face":
                    st.warning(f"⚠️ {detail['filename']}: {detail['message']}")
                else:
                    st.error(f"❌ {detail['filename']}: {detail['message']}")
            
            # 完了時の処理
            if results["successful"] > 0:
                st.balloons()
                st.success(f"🎉 {person_name} の顔登録が完了しました！（{results['successful']}枚成功）")
                
                # セッション更新を促す
                if st.button("🔄 画面を更新", type="secondary"):
                    st.rerun()


def display_rename_tab():
    """リネームタブ（簡易版）"""
    st.subheader("🏷️ 写真リネーム (簡易版)")
    
    st.info("""
    **注意**: この版では顔検出のみ行い、実際の認識はランダムな登録人物名を返します。
    """)
    
    # ファイルアップロード
    uploaded_files = st.file_uploader(
        "リネームする画像をアップロード",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write(f"📁 アップロード済み: {len(uploaded_files)}件")
        
        # 処理ボタン
        if st.button("🚀 テスト処理実行", type="primary"):
            with st.spinner("画像を処理中..."):
                results = {"successful": 0, "no_faces": 0, "failed": 0, "details": []}
                
                for uploaded_file in uploaded_files:
                    try:
                        # 一時ファイル保存
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=f".{uploaded_file.name.split('.')[-1]}", delete=False) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            temp_path = Path(tmp_file.name)
                        
                        try:
                            # 顔検出テスト
                            identified_names = st.session_state.face_service.process_image_for_rename(temp_path)
                            
                            if identified_names:
                                new_filename = "_".join(identified_names) + temp_path.suffix
                                results["successful"] += 1
                                status = "success"
                            else:
                                new_filename = uploaded_file.name
                                results["no_faces"] += 1
                                status = "no_faces"
                            
                            results["details"].append({
                                "original_name": uploaded_file.name,
                                "new_name": new_filename,
                                "identified_names": identified_names,
                                "status": status
                            })
                            
                        finally:
                            if temp_path.exists():
                                temp_path.unlink()
                                
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "original_name": uploaded_file.name,
                            "error": str(e),
                            "status": "error"
                        })
                
                # 結果表示
                st.subheader("📊 処理結果")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("成功", results["successful"])
                with col2:
                    st.metric("顔検出なし", results["no_faces"])
                with col3:
                    st.metric("失敗", results["failed"])
                
                # 詳細結果
                for detail in results["details"]:
                    if detail["status"] == "success":
                        names = ", ".join(detail["identified_names"])
                        st.success(f"✅ {detail['original_name']} → {detail['new_name']} ({names})")
                    elif detail["status"] == "no_faces":
                        st.warning(f"⚠️ {detail['original_name']}: 顔検出なし")
                    else:
                        st.error(f"❌ {detail['original_name']}: エラー")


def display_person_management_tab():
    """人物管理タブ"""
    st.subheader("📋 人物管理")
    
    try:
        persons = st.session_state.face_service.db.get_all_persons()
        
        if not persons:
            st.info("まだ人物が登録されていません")
            return
        
        # 人物一覧表示
        for person_id, name in persons:
            encodings = st.session_state.face_service.db.get_face_encodings_by_person(person_id)
            st.write(f"**{name}** (ID: {person_id}, データ数: {len(encodings)})")
        
    except Exception as e:
        st.error(f"人物一覧取得エラー: {str(e)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"アプリケーションエラー: {str(e)}")
        st.error(f"アプリケーションエラーが発生しました: {str(e)}")
        st.info("ページを再読み込みしてください") 