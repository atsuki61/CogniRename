"""
CogniRename CLI コマンド（最小版）

dlibエラー回避用のOpenCV Haar Cascade版
"""

import logging
from pathlib import Path
from typing import Optional

import click
from tqdm import tqdm

from ..core.face_service_minimal import FaceServiceMinimal
from ..core.rename_service_minimal import RenameServiceMinimal
from ..utils.path_helpers import find_images_recursive
from ..config import LOG_CONFIG

# ログ設定
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='詳細ログを有効化')
def main(verbose):
    """CogniRename - 顔認識による写真自動リネームツール（最小版）"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo("🔍 CogniRename (最小版) - OpenCV Haar Cascade使用")
    click.echo("⚠️  注意: この版では顔検出のみ可能です。実際の顔認識精度は限定的です。")


@main.command()
@click.option('--name', '-n', required=True, help='人物名')
@click.option('--image-path', '-i', required=True, help='顔画像ファイルパス')
def register(name: str, image_path: str):
    """顔画像から人物を登録"""
    try:
        image_file = Path(image_path)
        if not image_file.exists():
            click.echo(f"❌ ファイルが見つかりません: {image_path}", err=True)
            return
        
        face_service = FaceServiceMinimal()
        
        click.echo(f"顔を登録中: {name}")
        success = face_service.register_face_from_image(image_file, name)
        
        if success:
            click.echo(f"✅ {name} の顔を登録しました！")
        else:
            click.echo(f"❌ 顔登録に失敗しました（顔が検出されませんでした）", err=True)
            
    except Exception as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        logger.error(f"顔登録エラー: {str(e)}")


@main.command()
@click.option('--name', '-n', required=True, help='人物名')
@click.option('--image-folder', '-f', required=True, help='顔画像が保存されたフォルダパス')
@click.option('--recursive', '-r', is_flag=True, help='サブフォルダも検索')
@click.option('--continue-on-error', '-c', is_flag=True, default=True, help='エラー時も継続')
@click.option('--max-files', '-m', default=None, type=int, help='処理最大ファイル数')
def register_batch(name: str, image_folder: str, recursive: bool, continue_on_error: bool, max_files: Optional[int]):
    """フォルダ内の複数画像から人物を一括登録"""
    try:
        folder = Path(image_folder)
        if not folder.exists():
            click.echo(f"❌ フォルダが見つかりません: {image_folder}", err=True)
            return
        
        # 画像ファイル検索
        click.echo("画像ファイルを検索中...")
        if recursive:
            image_files = list(find_images_recursive(folder))
        else:
            image_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.jfif', '.webp'}]
        
        if not image_files:
            click.echo("❌ 画像ファイルが見つかりませんでした", err=True)
            return
        
        if max_files:
            image_files = image_files[:max_files]
        
        click.echo(f"対象ファイル数: {len(image_files)}")
        
        # 一括登録実行
        face_service = FaceServiceMinimal()
        
        click.echo(f"\n🔄 {name} の顔を一括登録中...")
        results = face_service.register_multiple_faces_from_images(image_files, name)
        
        # 進捗表示
        click.echo("\n📊 登録結果:")
        click.echo(f"   ✅ 成功: {results['successful']}件")
        click.echo(f"   ❌ 失敗: {results['failed']}件")
        click.echo(f"   📈 成功率: {results['successful']/(len(image_files))*100:.1f}%")
        
        # 詳細結果表示
        if results['details']:
            click.echo("\n📋 詳細結果:")
            for detail in results['details']:
                filename = Path(detail['image_path']).name
                if detail['status'] == 'success':
                    click.echo(f"   ✅ {filename}: {detail['message']}")
                elif detail['status'] == 'no_face':
                    click.echo(f"   ⚠️  {filename}: {detail['message']}")
                else:
                    click.echo(f"   ❌ {filename}: {detail['message']}")
        
        if results['successful'] > 0:
            click.echo(f"\n🎉 {name} の顔登録が完了しました！（{results['successful']}枚成功）")
        else:
            click.echo(f"\n😢 {name} の顔登録に失敗しました。画像を確認してください。")
            
    except Exception as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        logger.error(f"一括顔登録エラー: {str(e)}")


@main.command()
@click.option('--input-folder', '-i', required=True, help='入力フォルダパス')
@click.option('--recursive', '-r', is_flag=True, help='サブフォルダも処理')
@click.option('--dry-run', '-d', is_flag=True, help='実際のリネームは行わない')
@click.option('--max-files', '-m', default=None, type=int, help='処理最大ファイル数')
def rename(input_folder: str, recursive: bool, dry_run: bool, max_files: Optional[int]):
    """写真ファイルの一括リネーム（最小版）"""
    try:
        folder = Path(input_folder)
        if not folder.exists():
            click.echo(f"❌ フォルダが見つかりません: {input_folder}", err=True)
            return
        
        face_service = FaceServiceMinimal()
        rename_service = RenameServiceMinimal(face_service)
        
        # 画像ファイル検索
        click.echo("画像ファイルを検索中...")
        if recursive:
            image_files = list(find_images_recursive(folder))
        else:
            image_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
        
        if not image_files:
            click.echo("❌ 画像ファイルが見つかりませんでした", err=True)
            return
        
        if max_files:
            image_files = image_files[:max_files]
        
        click.echo(f"対象ファイル数: {len(image_files)}")
        
        if dry_run:
            click.echo("🔍 ドライラン - 実際のリネームは行いません")
        
        # 処理実行
        successful = 0
        no_faces = 0
        failed = 0
        
        with tqdm(image_files, desc="処理中") as pbar:
            for image_file in pbar:
                try:
                    pbar.set_description(f"処理中: {image_file.name}")
                    
                    # 顔検出テスト
                    identified_names = face_service.process_image_for_rename(image_file)
                    
                    if identified_names:
                        new_filename = rename_service.generate_new_filename(identified_names, image_file)
                        
                        if not dry_run:
                            # 実際のリネーム（未実装 - ドライランのみ）
                            pass
                        
                        click.echo(f"✅ {image_file.name} → {new_filename} ({', '.join(identified_names)})")
                        successful += 1
                    else:
                        click.echo(f"⚠️  {image_file.name}: 顔検出なし")
                        no_faces += 1
                        
                except Exception as e:
                    click.echo(f"❌ {image_file.name}: {str(e)}")
                    failed += 1
                    logger.error(f"ファイル処理エラー: {image_file.name} - {str(e)}")
        
        # 結果表示
        click.echo("\n📊 処理結果:")
        click.echo(f"   成功: {successful}件")
        click.echo(f"   顔検出なし: {no_faces}件")
        click.echo(f"   失敗: {failed}件")
        
        if dry_run:
            click.echo("\n💡 実際のリネームを行うには --dry-run オプションを外してください")
        
    except Exception as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        logger.error(f"リネーム処理エラー: {str(e)}")


@main.command()
def list_persons():
    """登録人物の一覧表示"""
    try:
        face_service = FaceServiceMinimal()
        persons = face_service.db.get_all_persons()
        
        if not persons:
            click.echo("まだ人物が登録されていません")
            return
        
        click.echo("📋 登録人物一覧:")
        for person_id, name in persons:
            encodings = face_service.db.get_face_encodings_by_person(person_id)
            click.echo(f"  {person_id:3d}: {name} (データ数: {len(encodings)})")
        
        click.echo(f"\n合計: {len(persons)}人")
        
    except Exception as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        logger.error(f"人物一覧エラー: {str(e)}")


@main.command()
@click.option('--input-folder', '-i', required=True, help='入力フォルダパス')
@click.option('--max-preview', '-m', default=5, help='プレビュー最大件数')
def preview(input_folder: str, max_preview: int):
    """リネーム結果のプレビュー表示"""
    try:
        folder = Path(input_folder)
        if not folder.exists():
            click.echo(f"❌ フォルダが見つかりません: {input_folder}", err=True)
            return
        
        face_service = FaceServiceMinimal()
        
        # 画像ファイル検索
        image_files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
        
        if not image_files:
            click.echo("❌ 画像ファイルが見つかりませんでした", err=True)
            return
        
        preview_files = image_files[:max_preview]
        
        click.echo(f"🔍 プレビュー ({len(preview_files)}件):")
        
        for i, image_file in enumerate(preview_files, 1):
            try:
                identified_names = face_service.process_image_for_rename(image_file)
                
                if identified_names:
                    new_filename = "_".join(identified_names) + image_file.suffix
                    click.echo(f"  {i:2d}. {image_file.name} → {new_filename}")
                    click.echo(f"      認識: {', '.join(identified_names)}")
                else:
                    click.echo(f"  {i:2d}. {image_file.name} → (変更なし)")
                    click.echo(f"      顔検出なし")
                
            except Exception as e:
                click.echo(f"  {i:2d}. {image_file.name} → エラー: {str(e)}")
        
        if len(image_files) > max_preview:
            click.echo(f"\n... 他 {len(image_files) - max_preview} 件")
        
    except Exception as e:
        click.echo(f"❌ エラー: {str(e)}", err=True)
        logger.error(f"プレビューエラー: {str(e)}")


if __name__ == '__main__':
    main() 