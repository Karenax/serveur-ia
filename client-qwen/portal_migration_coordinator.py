"""Experimental full inventory and migration under the caller's profile lock.

The caller supplies a trusted desktop window adapter and a Qt inventory that
returns None only after the absence of Qt storage was verified. No user data is
logged or deleted. This module is not enabled in the distributed clients.
"""
from math import isfinite
from pathlib import Path
from time import monotonic

from portal_migration_job import execute_job,execute_snapshot,execute_destination_manifest,MigrationJobError,MigrationArchiveUnavailable
from portal_migration_plan import execute_migration,migration_plan
from portal_migration_state import read_state,write_state,MigrationStateError
from portal_origin_plan import OriginInventoryPlan
from portal_origin_state import FIRST_PORT,LAST_PORT,read_origin,record_origin
from portal_recovery_broker import PortalRecoveryBroker


def resolve_migration(marker,scan_assets,copy_assets,announce_scan,qt_inventory,window_factory,cancelled,
                      *,state_path,profile,encrypt,decrypt,fixed_port=None,timeout=120,broker_factory=PortalRecoveryBroker,
                      interactive_review=False,audio_archives=False):
    """Inventory every origin, replay all copies, then persist a stable port."""
    if (any(not callable(callback) for callback in (announce_scan,qt_inventory,window_factory,cancelled,encrypt,decrypt))
            or type(interactive_review) is not bool or type(audio_archives) is not bool or (audio_archives and not interactive_review)
            or not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not isfinite(timeout) or not 0<timeout<=600):
        raise ValueError('Contrôle de migration invalide.')
    ports=tuple(range(FIRST_PORT,LAST_PORT+1));marker=Path(marker)
    existing=read_origin(marker)
    checkpoint=read_state(state_path,profile,decrypt)
    if checkpoint and checkpoint['format']==2:
        raise MigrationStateError('Le suivi expérimental ancien ne contient pas les empreintes nécessaires ; les sources sont conservées.')
    if checkpoint and (checkpoint['format'] in (4,5) or (checkpoint['format']==6 and not audio_archives)):
        raise MigrationStateError('Les copies audio ne peuvent pas encore être vérifiées ; les sources sont conservées.')
    if fixed_port is not None and (type(fixed_port) is not int or fixed_port not in ports):
        raise ValueError('Port imposé invalide.')
    if existing is not None and fixed_port is not None and existing!=fixed_port:
        raise MigrationJobError('Le port enregistré est incompatible avec la liaison existante.')
    if checkpoint is not None and ((existing is not None and checkpoint['port']!=existing)
                                   or (fixed_port is not None and checkpoint['port']!=fixed_port)):
        raise MigrationStateError('Le suivi de migration concerne un autre port local.')
    fixed=existing if existing is not None else fixed_port if fixed_port is not None else checkpoint['port'] if checkpoint else None
    plan=OriginInventoryPlan(ports,default_port=ports[0],fixed_port=fixed,
                             allow_audio_archives=audio_archives,require_audio_ids=audio_archives)
    deadline=monotonic()+timeout
    with broker_factory(ports,ports[0],scan_assets,inventory_plan=plan) as broker:
        if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
        announce_scan({'ports':ports,'token':broker.token})
        while True:
            if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
            remaining=deadline-monotonic()
            if remaining<=0:raise MigrationJobError('Vérification expirée ; les sources sont conservées.')
            state=plan.status()['state']
            if state=='unavailable':raise MigrationJobError('Une origine locale ne peut pas être vérifiée.')
            if state=='needsRecovery':break
            if state=='ready' and broker.wait_complete(min(.1,remaining)) is not None:break
            if state=='scanning':broker.wait_complete(min(.1,remaining))
        tauri_reports=plan.reports()
    if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
    qt_reports=qt_inventory(cancelled)
    plan=migration_plan(tauri_reports,qt_reports,fixed_port=fixed,allow_audio_archives=audio_archives,
                        copy_audio_archives=audio_archives,require_audio_ids=audio_archives)
    expected_audio=set()
    if audio_archives:
        all_reports=tauri_reports+(qt_reports or [])
        expected_audio={identifier for report in all_reports for identifier in report['audioArchiveIds']}
        if len(expected_audio)>3000:raise MigrationJobError('Trop de copies audio pour cette récupération.')
        scanned_destination=next(report for report in tauri_reports if report['port']==plan['destination'])
        initial=set(execute_destination_manifest(plan['destination'],ports,copy_assets,window_factory,cancelled,
                                                 timeout=timeout,broker_factory=broker_factory))
        if initial!=set(scanned_destination['audioArchiveIds']):
            raise MigrationArchiveUnavailable('Les copies audio de destination ont changé ; elles sont conservées.')
        if checkpoint and checkpoint['format']==6 and not set(checkpoint['destinationArchives']) <= initial:
            raise MigrationArchiveUnavailable('Une copie audio conservée est introuvable ou illisible.')
    def snapshots():
        return [execute_snapshot(job,plan['destination'],ports,copy_assets,window_factory,cancelled,
                                 timeout=timeout,broker_factory=broker_factory,
                                 **({'audio_archives':True} if audio_archives else {})) for job in plan['jobs']]
    before=snapshots()
    archives={(item['engine'],item['port']):set(item['ids']) for item in checkpoint.get('protected',[])} if checkpoint else {}
    protected=set(archives)
    if protected and not interactive_review:
        raise MigrationJobError('Les versions conservées nécessitent une vérification interactive.')
    if not protected <= {(item['engine'],item['port']) for item in before}:
        raise MigrationJobError('Une ancienne source protégée est absente ; ses données sont conservées.')
    trusted={(item['engine'],item['port']):item for item in checkpoint['sources']} if checkpoint and existing is not None else {}
    unchanged={(item['engine'],item['port']) for item in before if trusted.get((item['engine'],item['port']))==item}
    def run_job(job,destination,_phase):
        identity=(job['engine'],job['port'])
        result=execute_job(job,destination,ports,copy_assets,window_factory,cancelled,timeout=timeout,broker_factory=broker_factory,
                           preserve_conflicts=identity in unchanged and identity not in protected,
                           **({'interactive_review':True,'required_archives':tuple(sorted(archives.get(identity,())))} if interactive_review else {}),
                           **({'audio_review':True,'copy_audio_archives':True} if audio_archives else {}))
        if result.get('archived'):
            protected.add(identity)
            archives.setdefault(identity,set()).update(result['archive_ids'])
        return result
    result=execute_migration(tauri_reports,qt_reports,run_job,cancelled,fixed_port=fixed,
                             allow_audio_archives=audio_archives,copy_audio_archives=audio_archives,require_audio_ids=audio_archives)
    if snapshots()!=before:raise MigrationJobError('Une source a changé pendant la migration ; ses données sont conservées.')
    if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
    destination_archives=None
    if audio_archives:
        expected_audio.update(identifier[6:] for values in archives.values() for identifier in values if identifier.startswith('audio-'))
        if len(expected_audio)>3000:raise MigrationJobError('Trop de copies audio pour cette récupération.')
        destination_archives=execute_destination_manifest(result['destination'],ports,copy_assets,window_factory,cancelled,
                                                          timeout=timeout,broker_factory=broker_factory)
        if set(destination_archives)!=expected_audio:
            raise MigrationArchiveUnavailable('Les copies audio de destination sont incomplètes ou ont changé.')
    # Reserve every port again before committing; occupied means unverified.
    reservation_assets=({key:scan_assets[key] for key in ('/recovery','/recovery.js','/portal_origin_recovery.js')}
                        if audio_archives else copy_assets)
    with broker_factory(ports,result['destination'],reservation_assets):
        if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
        write_state(state_path,profile,result['destination'],before,encrypt,decrypt,archives=archives,
                    **({'extended':True,'destination_archives':destination_archives} if audio_archives else {}))
        if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
        return record_origin(marker,result['destination'])
