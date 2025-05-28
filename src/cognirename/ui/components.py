"""
CogniRename GUI コンポーネント

Streamlit 用の共通 UI コンポーネント・ヘルパー関数を提供します。
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import io

import streamlit as st
from PIL import Image
import pandas as pd

from ..core.face_service import FaceService
from ..core.rename_service import RenameService
from ..utils.image_io import (
    load_image_safely, 
    resize_image_for_display, 
    convert_image_to_bytes,
    get_image_info
)
from ..utils.path_helpers import clean_filename

logger = logging.getLogger(__name__)


def init_session_state():
    """セッション状態の初期化"""
    if 'face_service' not in st.session_state:
        st.session_state.face_service = FaceService()
    
    if 'rename_service' not in st.session_state:
        st.session_state.rename_service = RenameService(st.session_state.face_service)
    
    if 'upload_files' not in st.session_state:
        st.session_state.upload_files = []
    
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []


def display_system_info():
    """システム情報の表示"""
    try:
        stats = st.session_state.face_service.get_recognition_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("登録人数", f"{stats['person_count']}人")
        
        with col2:
            st.metric("顔特徴量", f"{stats['encoding_count']}件")
        
        with col3:
            st.metric("平均特徴量/人", f"{stats['avg_encodings_per_person']}")
        
        with col4:
            st.metric("DB サイズ", f"{stats['db_size_mb']}MB")
            
    except Exception as e:
        st.error(f"システム情報取得エラー: {str(e)}")


def display_face_registration_form():
    """顔登録フォームの表示"""
    st.subheader("👤 顔登録")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 画像アップロード
        uploaded_file = st.file_uploader(
            "顔画像をアップロード",
            type=['jpg', 'jpeg', 'png', 'webp'],
            help="1つの顔が写っている画像を選択してください"
        )
        
        # 人物名入力
        person_name = st.text_input(
            "人物名",
            placeholder="例: 田中太郎",
            help="登録する人物の名前を入力してください"
        )
        
        # 登録ボタン
        register_button = st.button("🔹 顔を登録", type="primary")
    
    with col2:
        # アップロード画像のプレビュー
        if uploaded_file is not None:
            try:
                image = Image.open(uploaded_file)
                image = resize_image_for_display(image, (300, 300))
                st.image(image, caption="アップロード画像", use_column_width=True)
                
                # 画像情報
                with st.expander("画像情報"):
                    st.text(f"ファイル名: {uploaded_file.name}")
                    st.text(f"サイズ: {image.size}")
                    st.text(f"モード: {image.mode}")
                    
            except Exception as e:
                st.error(f"画像表示エラー: {str(e)}")
    
    # 登録処理
    if register_button:
        if not uploaded_file:
            st.error("画像をアップロードしてください")
        elif not person_name.strip():
            st.error("人物名を入力してください")
        else:
            with st.spinner("顔を登録中..."):
                success = register_face_from_upload(uploaded_file, person_name.strip())
                if success:
                    st.success(f"✅ {person_name} の顔を登録しました！")
                    st.rerun()  # ページ再読み込みで統計更新
                else:
                    st.error("❌ 顔登録に失敗しました")


def register_face_from_upload(uploaded_file, person_name: str) -> bool:
    """アップロードファイルから顔登録
    
    Args:
        uploaded_file: Streamlit UploadedFile
        person_name: 人物名
        
    Returns:
        成功時 True
    """
    try:
        # 一時ファイルとして保存
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f".{uploaded_file.name.split('.')[-1]}", delete=False) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = Path(tmp_file.name)
        
        try:
            # 顔登録
            success = st.session_state.face_service.register_face_from_image(temp_path, person_name)
            return success
        finally:
            # 一時ファイル削除
            if temp_path.exists():
                temp_path.unlink()
                
    except Exception as e:
        logger.error(f"顔登録エラー: {str(e)}")
        return False


def display_person_list():
    """登録人物一覧の表示"""
    try:
        persons = st.session_state.face_service.db.get_all_persons()
        
        if not persons:
            st.info("まだ人物が登録されていません")
            return
        
        # データフレーム作成
        data = []
        for person_id, name in persons:
            encodings = st.session_state.face_service.db.get_face_encodings_by_person(person_id)
            data.append({
                "ID": person_id,
                "名前": name,
                "顔データ数": len(encodings)
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"人物一覧取得エラー: {str(e)}")


def display_rename_interface():
    """リネームインターフェースの表示"""
    st.subheader("🏷️ 写真リネーム")
    
    # ファイルアップロード
    uploaded_files = st.file_uploader(
        "リネームする画像をアップロード",
        type=['jpg', 'jpeg', 'png', 'webp'],
        accept_multiple_files=True,
        help="複数の画像を一度に選択できます"
    )
    
    if uploaded_files:
        st.write(f"📁 アップロード済み: {len(uploaded_files)}件")
        
        # プレビュー表示オプション
        show_preview = st.checkbox("プレビュー表示", value=True)
        
        if show_preview:
            display_rename_preview(uploaded_files)
        
        # リネーム実行
        col1, col2 = st.columns(2)
        
        with col1:
            dry_run = st.checkbox("ドライラン（実際のリネームは行わない）", value=True)
        
        with col2:
            process_button = st.button("🚀 リネーム実行", type="primary")
        
        if process_button:
            with st.spinner("画像を処理中..."):
                results = process_uploaded_files(uploaded_files, dry_run)
                display_processing_results(results)


def display_rename_preview(uploaded_files: List) -> None:
    """リネームプレビューの表示
    
    Args:
        uploaded_files: アップロードファイルのリスト
    """
    try:
        # 最大プレビュー数
        max_preview = min(len(uploaded_files), 5)
        preview_files = uploaded_files[:max_preview]
        
        st.write("🔍 リネームプレビュー:")
        
        for i, uploaded_file in enumerate(preview_files):
            with st.expander(f"{i+1}. {uploaded_file.name}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # 画像表示
                    try:
                        image = Image.open(uploaded_file)
                        image = resize_image_for_display(image, (150, 150))
                        st.image(image, use_column_width=True)
                    except Exception as e:
                        st.error(f"画像表示エラー: {str(e)}")
                
                with col2:
                    # 認識結果プレビュー
                    try:
                        # 一時ファイル作成
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=f".{uploaded_file.name.split('.')[-1]}", delete=False) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            temp_path = Path(tmp_file.name)
                        
                        try:
                            # 顔認識
                            identified_names = st.session_state.face_service.process_image_for_rename(temp_path)
                            
                            if identified_names:
                                new_name = st.session_state.rename_service.generate_new_filename(
                                    identified_names, temp_path
                                )
                                st.success(f"認識: {', '.join(identified_names)}")
                                st.info(f"新ファイル名: {new_name}")
                            else:
                                st.warning("顔を認識できませんでした")
                                
                        finally:
                            if temp_path.exists():
                                temp_path.unlink()
                                
                    except Exception as e:
                        st.error(f"認識エラー: {str(e)}")
        
        if len(uploaded_files) > max_preview:
            st.info(f"... 他 {len(uploaded_files) - max_preview} 件")
            
    except Exception as e:
        st.error(f"プレビューエラー: {str(e)}")


def process_uploaded_files(uploaded_files: List, dry_run: bool = True) -> Dict[str, Any]:
    """アップロードファイルの処理
    
    Args:
        uploaded_files: アップロードファイルのリスト
        dry_run: ドライランフラグ
        
    Returns:
        処理結果の辞書
    """
    results = {
        "total_files": len(uploaded_files),
        "successful": 0,
        "failed": 0,
        "no_faces": 0,
        "details": []
    }
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            # 進捗更新
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"処理中: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            # 一時ファイル作成
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=f".{uploaded_file.name.split('.')[-1]}", delete=False) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_path = Path(tmp_file.name)
            
            try:
                # 顔認識・リネーム処理
                identified_names = st.session_state.face_service.process_image_for_rename(temp_path)
                
                if identified_names:
                    new_filename = st.session_state.rename_service.generate_new_filename(
                        identified_names, temp_path
                    )
                    new_filename = clean_filename(new_filename)  # ファイル名クリーニング
                    
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
                "new_name": uploaded_file.name,
                "identified_names": [],
                "status": "error",
                "error": str(e)
            })
            logger.error(f"ファイル処理エラー: {uploaded_file.name} - {str(e)}")
    
    # 進捗バー削除
    progress_bar.empty()
    status_text.empty()
    
    return results


def display_processing_results(results: Dict[str, Any]) -> None:
    """処理結果の表示
    
    Args:
        results: 処理結果の辞書
    """
    st.subheader("📊 処理結果")
    
    # 統計表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総ファイル数", results["total_files"])
    
    with col2:
        st.metric("成功", results["successful"], delta=results["successful"])
    
    with col3:
        st.metric("顔認識なし", results["no_faces"])
    
    with col4:
        st.metric("失敗", results["failed"], delta=results["failed"] if results["failed"] > 0 else None)
    
    # 詳細結果
    if results["details"]:
        st.subheader("詳細結果")
        
        # 成功したファイル
        successful_files = [d for d in results["details"] if d["status"] == "success"]
        if successful_files:
            st.success(f"✅ 成功 ({len(successful_files)}件)")
            for detail in successful_files:
                names = ", ".join(detail["identified_names"])
                st.write(f"• {detail['original_name']} → {detail['new_name']} ({names})")
        
        # 顔認識できなかったファイル
        no_face_files = [d for d in results["details"] if d["status"] == "no_faces"]
        if no_face_files:
            st.warning(f"⚠️ 顔認識なし ({len(no_face_files)}件)")
            for detail in no_face_files:
                st.write(f"• {detail['original_name']}")
        
        # エラーファイル
        error_files = [d for d in results["details"] if d["status"] == "error"]
        if error_files:
            st.error(f"❌ エラー ({len(error_files)}件)")
            for detail in error_files:
                error_msg = detail.get("error", "不明なエラー")
                st.write(f"• {detail['original_name']}: {error_msg}")


def create_download_results(results: Dict[str, Any]) -> bytes:
    """処理結果のダウンロード用データ作成
    
    Args:
        results: 処理結果の辞書
        
    Returns:
        CSV データのバイト列
    """
    try:
        df = pd.DataFrame(results["details"])
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        return csv_buffer.getvalue().encode('utf-8-sig')
    except Exception as e:
        logger.error(f"ダウンロードデータ作成エラー: {str(e)}")
        return b"" 