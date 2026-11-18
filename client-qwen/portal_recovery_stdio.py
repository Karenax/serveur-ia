"""Bundled inventory assets and experimental recovery-window adapters.

The normal read-only inventory uses the asset loader. Transfer and recovery
adapters remain explicitly experimental. The caller keeps the profile lock
and retains the control stream until the normal relay has stopped.
"""
from pathlib import Path
import os
import stat
import sys

import client
from portal_origin_session import OriginInventorySession, recovery_offer, resolve_origin


class QtLegacyStoragePresent(RuntimeError):
    """An existing Qt profile has not yet been inventoried by its own engine."""


def qt_storage_path(settings):
    if not sys.platform.startswith('linux'):
        return None
    old = settings.parent / ('webview-' + settings.stem)
    try:
        state = old.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise QtLegacyStoragePresent('Le stockage Qt ne peut pas être vérifié.') from error
    if not stat.S_ISDIR(state.st_mode):
        raise QtLegacyStoragePresent('Le stockage Qt ne peut pas être vérifié.')
    return old


def check_qt_storage(settings):
    if qt_storage_path(settings) is not None:
        raise QtLegacyStoragePresent('Des données locales d’une ancienne version restent à vérifier.')


def recovery_assets(directory, *, audio_archives=False):
    """Load only the fixed, locally bundled recovery resources."""
    if type(audio_archives) is not bool:raise ValueError('Ressources de récupération invalides.')
    directory = Path(directory)
    files = {'/recovery':'portal_origin_scan.html',
             '/recovery/scan':'portal_origin_scan.html',
             '/recovery.js':'portal_origin_scan.js',
             '/portal_origin_scan.js':'portal_origin_scan.js',
             '/portal_origin_inventory.js':'portal_origin_inventory.js',
             '/portal_origin_transfer.js':'portal_origin_transfer.js',
             '/portal_origin_sender.js':'portal_origin_sender.js',
             '/portal_origin_sender_result.js':'portal_origin_sender_result.js',
             '/portal_origin_snapshot.js':'portal_origin_snapshot.js',
             '/portal_origin_receiver.js':'portal_origin_receiver.js',
             '/portal_origin_window.js':'portal_origin_window.js',
             '/portal_conflict_archive.js':'portal_conflict_archive.js',
             '/portal_conflict_review.js':'portal_conflict_review.js',
             '/portal_conflict_review.css':'portal_conflict_review.css',
             '/portal_origin_recovery.js':'portal_origin_recovery.js'}
    if audio_archives:
        files['/portal_audio_conflict_archive.js']='portal_audio_conflict_archive.js'
    assets = {}
    for url, name in files.items():
        with (directory/name).open('rb') as stream:
            data = stream.read(1024 * 1024 + 1)
        if not data or len(data) > 1024 * 1024:
            raise ValueError('Ressource de récupération invalide.')
        assets[url] = data
    if audio_archives:
        marker=b'<script src="/portal_origin_inventory.js"></script>'
        prefix=b'<script src="/portal_origin_recovery.js"></script><script src="/portal_audio_conflict_archive.js"></script>'
        for url in ('/recovery','/recovery/scan'):
            if assets[url].count(marker)!=1:raise ValueError('Ressource de récupération invalide.')
            assets[url]=assets[url].replace(marker,prefix+marker)
    return assets


def transfer_assets(directory, *, audio_archives=False):
    """Use the same bounded resources for temporary transfer windows."""
    directory = Path(directory)
    assets = recovery_assets(directory,audio_archives=audio_archives)
    with (directory/'portal_origin_transfer.html').open('rb') as stream:
        html = stream.read(1024 * 1024 + 1)
    if not html or len(html) > 1024 * 1024:
        raise ValueError('Ressource de transfert invalide.')
    if audio_archives:
        with (directory/'portal_audio_conflict_review.js').open('rb') as stream:
            review=stream.read(1024*1024+1)
        if not review or len(review)>1024*1024:raise ValueError('Ressource de transfert invalide.')
        assets['/portal_audio_conflict_review.js']=review
        with (directory/'portal_origin_manifest.js').open('rb') as stream:
            manifest=stream.read(1024*1024+1)
        if not manifest or len(manifest)>1024*1024:raise ValueError('Ressource de transfert invalide.')
        assets['/portal_origin_manifest.js']=manifest
        marker=b'<script src="/portal_origin_inventory.js"></script>'
        prefix=b'<script src="/portal_audio_conflict_archive.js"></script><script src="/portal_audio_conflict_review.js"></script>'
        if html.count(marker)!=1:raise ValueError('Ressource de transfert invalide.')
        html=html.replace(marker,prefix+marker)
    assets['/recovery'] = html
    assets['/recovery/transfer'] = html
    return assets


def resolve_port(profile, control, output, assets, *, session_factory=OriginInventorySession):
    """Announce a protected inventory, or reuse a verified recorded port."""
    settings = client.settings_path(profile)
    fixed = client.portal_recovery_fixed_port(profile)
    check_qt_storage(settings)
    # A newly imported Windows profile may not have a QwenClient folder yet.
    settings.parent.mkdir(parents=True, exist_ok=True)
    def announce(descriptor):
        output.write(recovery_offer(settings.stem, descriptor['token']) + '\n')
        output.flush()
    return resolve_origin(settings.with_suffix('.tauri-origin.json'), assets, announce,
                          control.cancelled, fixed_port=fixed, session_factory=session_factory)


def resolve_port_full(profile, control, output, directory, *, coordinator=None):
    """Experimental end-to-end migration; the caller holds the profile lock."""
    from portal_migration_coordinator import resolve_migration
    from portal_migration_windows import RecoveryWindows
    settings=client.settings_path(profile)
    fixed=client.portal_recovery_fixed_port(profile)
    storage=qt_storage_path(settings)
    if storage is not None:
        raise QtLegacyStoragePresent('Des données locales d’une ancienne version restent à vérifier.')
    settings.parent.mkdir(parents=True,exist_ok=True)
    directory=Path(directory).resolve()
    audio_archives=os.environ.get('KIARA_TEST_AUDIO_ARCHIVES')=='1'
    if audio_archives and os.environ.get('KIARA_TEST_CONFLICT_REVIEW')!='1':
        raise ValueError('La recette audio nécessite la comparaison interactive.')
    script=directory/'recovery_init.js'
    if not script.is_file():
        script=(directory.parent/'client-tauri'/'src'/'recovery_init.js').resolve()
    scan_assets=recovery_assets(directory,**({'audio_archives':True} if audio_archives else {}))
    copy_assets=transfer_assets(directory,**({'audio_archives':True} if audio_archives else {}))
    windows=RecoveryWindows(settings.stem,output,control,storage,script)
    def announce(descriptor):
        output.write(recovery_offer(settings.stem,descriptor['token'])+'\n');output.flush()
    def qt_inventory(cancelled):
        return None
    runner=resolve_migration if coordinator is None else coordinator
    return runner(settings.with_suffix('.tauri-origin.json'),scan_assets,copy_assets,announce,qt_inventory,
                  windows.open,control.cancelled,state_path=settings.with_suffix('.tauri-migration'),profile=settings.stem,
                  encrypt=lambda value:client.protect(value),decrypt=lambda value:client.protect(value,decrypt=True),fixed_port=fixed,
                  **({'interactive_review':True,'timeout':600} if os.environ.get('KIARA_TEST_CONFLICT_REVIEW')=='1' else {}),
                  **({'audio_archives':True} if audio_archives else {}))
