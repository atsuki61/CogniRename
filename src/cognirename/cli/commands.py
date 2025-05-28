"""
CogniRename CLI コマンド

Click を使用したコマンドライン インターフェースの実装
- register: 顔登録
- rename: 写真リネーム  
- list-persons: 登録人物一覧
"""

import logging
from pathlib import Path
from typing import Optional

import click
from tqdm import tqdm

from ..core.face_service import FaceService
from ..core.rename_service import RenameService
from ..config import LOG_CONFIG

# ログ設定
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='詳細ログを表示')
def main(verbose: bool):
    """CogniRename - 顔認識による写真自動リネームツール
    
    200人・7000枚規模の写真管理に対応した顔認識リネームツールです。
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("詳細ログモードを有効にしました")


@main.command()
@click.option('--name', '-n', required=True, help='人物名')
@click.option('--image-path', '-i', required=True, type=click.Path(exists=True, path_type=Path), help='顔画像ファイルパス')
def register(name: str, image_path: Path):
    """顔登録 - 指定された画像から顔を登録します
    
    例: cognirename register --name "田中太郎" --image-path "./photos/tanaka.jpg"
    """
    click.echo(f"顔登録開始: {name} - {image_path.name}")
    
    try:
        face_service = FaceService()
        success = face_service.register_face_from_image(image_path, name)
        
        if success:
            click.echo(f"✅ 顔登録完了: {name}")
            
            # 統計表示
            stats = face_service.get_recognition_stats()
            click.echo(f"   登録人数: {stats['person_count']}人")
            click.echo(f"   顔特徴量: {stats['encoding_count']}件")
        else:
            click.echo(f"❌ 顔登録失敗: {name}")
            
    except ValueError as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        click.echo(f"❌ 予期しないエラーが発生しました: {str(e)}", err=True)
        raise click.Abort()


@main.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path), help='入力フォルダパス')
@click.option('--recursive', '-r', is_flag=True, help='サブフォルダも処理')
@click.option('--dry-run', '-d', is_flag=True, help='実際のリネームを行わずプレビューのみ')
def rename(input_folder: Path, recursive: bool, dry_run: bool):
    """写真リネーム - フォルダ内の写真を顔認識でリネームします
    
    例: cognirename rename --input-folder "./photos" --recursive --dry-run
    """
    click.echo(f"リネーム処理開始: {input_folder}")
    click.echo(f"  サブフォルダ処理: {'有効' if recursive else '無効'}")
    click.echo(f"  モード: {'ドライラン' if dry_run else '実行'}")
    
    try:
        rename_service = RenameService()
        
        # 画像ファイル検索
        image_files = rename_service.find_image_files(input_folder, recursive)
        
        if not image_files:
            click.echo("⚠️  処理対象の画像ファイルが見つかりませんでした")
            return
        
        click.echo(f"対象ファイル: {len(image_files)}件")
        
        # 進捗表示用コールバック
        progress_bar = None
        def progress_callback(processed: int, total: int):
            nonlocal progress_bar
            if progress_bar is None:
                progress_bar = tqdm(total=total, desc="処理中", unit="files")
            progress_bar.update(1)
        
        # リネーム実行
        result = rename_service.rename_batch(image_files, dry_run, progress_callback)
        
        if progress_bar:
            progress_bar.close()
        
        # 結果表示
        click.echo(f"\n📊 処理結果:")
        click.echo(f"  総ファイル数: {result['total_files']}")
        click.echo(f"  成功: {result['successful']}")
        click.echo(f"  失敗: {result['failed']}")
        click.echo(f"  顔認識なし: {result['no_faces']}")
        click.echo(f"  処理時間: {result['total_time']:.1f}秒")
        click.echo(f"  平均時間/ファイル: {result['avg_time_per_file']:.2f}秒")
        
        if dry_run and result['successful'] > 0:
            click.echo(f"\n💡 --dry-run を外して実際のリネームを実行してください")
        
    except Exception as e:
        logger.error(f"リネーム処理エラー: {str(e)}")
        click.echo(f"❌ エラー: {str(e)}", err=True)
        raise click.Abort()


@main.command('list-persons')
def list_persons():
    """登録人物一覧 - 登録されている人物の一覧を表示します"""
    try:
        face_service = FaceService()
        persons = face_service.db.get_all_persons()
        
        if not persons:
            click.echo("登録されている人物はいません")
            return
        
        click.echo(f"📋 登録人物一覧 ({len(persons)}人):")
        for person_id, name in persons:
            # 各人物の顔特徴量数を取得
            encodings = face_service.db.get_face_encodings_by_person(person_id)
            click.echo(f"  {person_id:3d}: {name} ({len(encodings)}件の顔データ)")
        
        # 統計情報
        stats = face_service.get_recognition_stats()
        click.echo(f"\n📊 データベース統計:")
        click.echo(f"  人物数: {stats['person_count']}")
        click.echo(f"  顔特徴量: {stats['encoding_count']}")
        click.echo(f"  平均特徴量/人: {stats['avg_encodings_per_person']}")
        click.echo(f"  DB サイズ: {stats['db_size_mb']}MB")
        
    except Exception as e:
        logger.error(f"人物一覧取得エラー: {str(e)}")
        click.echo(f"❌ エラー: {str(e)}", err=True)
        raise click.Abort()


@main.command()
@click.option('--input-folder', '-i', required=True, type=click.Path(exists=True, file_okay=False, path_type=Path), help='入力フォルダパス')
@click.option('--recursive', '-r', is_flag=True, help='サブフォルダも処理')
@click.option('--max-preview', '-m', default=10, help='プレビュー件数上限')
def preview(input_folder: Path, recursive: bool, max_preview: int):
    """リネームプレビュー - 実際のリネームを行わずに結果をプレビュー表示します"""
    click.echo(f"プレビュー表示: {input_folder}")
    
    try:
        rename_service = RenameService()
        image_files = rename_service.find_image_files(input_folder, recursive)
        
        if not image_files:
            click.echo("⚠️  処理対象の画像ファイルが見つかりませんでした")
            return
        
        click.echo(f"対象ファイル: {len(image_files)}件 (プレビュー: {min(max_preview, len(image_files))}件)")
        
        previews = rename_service.get_rename_preview(image_files, max_preview)
        
        click.echo(f"\n📋 リネームプレビュー:")
        for i, preview in enumerate(previews, 1):
            if preview.get('error'):
                click.echo(f"  {i:2d}: ❌ {preview['original_name']} - {preview['error']}")
            elif preview['has_faces']:
                names = ', '.join(preview['identified_names'])
                click.echo(f"  {i:2d}: ✅ {preview['original_name']} → {preview['new_name']} ({names})")
            else:
                click.echo(f"  {i:2d}: ⚠️  {preview['original_name']} - 顔を認識できませんでした")
        
        if len(image_files) > max_preview:
            click.echo(f"\n... 他 {len(image_files) - max_preview} 件")
        
    except Exception as e:
        logger.error(f"プレビューエラー: {str(e)}")
        click.echo(f"❌ エラー: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main() 