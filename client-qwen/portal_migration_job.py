"""Experimental bounded transfer job; the caller retains the profile lock.

The window factory is a trusted adapter that opens the required isolated
engine windows and closes them on context exit. This module receives counts
only, never reads the transferred records and never writes the origin marker.
"""
from math import isfinite
import re
from time import monotonic

from portal_recovery_broker import PortalRecoveryBroker


class MigrationJobError(RuntimeError):
    pass


class MigrationConflict(MigrationJobError):
    pass


class MigrationRestart(MigrationJobError):
    pass


class MigrationArchiveUnavailable(MigrationJobError):
    pass


class MigrationReceiverUnavailable(MigrationJobError):
    pass


def execute_job(job, destination, ports, assets, window_factory, cancelled, *, timeout=120,
                broker_factory=PortalRecoveryBroker, preserve_conflicts=False, interactive_review=False,
                required_archives=(), audio_review=False, copy_audio_archives=False):
    """Run one copy or verification pass with a private result channel."""
    ports=tuple(ports)
    if (len(ports)!=10 or len(set(ports))!=10 or any(type(port) is not int or not 1024<=port<=65535 for port in ports)
            or type(destination) is not int or destination not in ports
            or type(copy_audio_archives) is not bool or (copy_audio_archives and not audio_review)
            or not isinstance(job,dict) or set(job)!=({'engine','port','localEntries','audioChunks','audioArchives'}
                                                       if copy_audio_archives else {'engine','port','localEntries','audioChunks'})
            or job['engine'] not in ('qt','tauri') or type(job['port']) is not int or job['port'] not in ports
            or (job['engine']=='tauri' and job['port']==destination)
            or any(type(job[name]) is not int or not 0<=job[name]<=9007199254740991
                   for name in (('localEntries','audioChunks','audioArchives') if copy_audio_archives else ('localEntries','audioChunks')))
            or (copy_audio_archives and job['audioArchives']>3000)
            or not callable(window_factory) or not callable(cancelled) or type(preserve_conflicts) is not bool
            or type(interactive_review) is not bool
            or type(audio_review) is not bool or (audio_review and not interactive_review)
            or not isinstance(required_archives,(tuple,list)) or len(required_archives)>1024
            or any(not isinstance(item,str) or not re.fullmatch(
                r'(?:audio-)?[0-9a-f]{64}' if audio_review else r'[0-9a-f]{64}',item) for item in required_archives)
            or len(set(required_archives))!=len(required_archives) or (required_archives and not interactive_review)
            or not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not isfinite(timeout) or not 0<timeout<=600):
        raise ValueError('Paramètres de transfert invalides.')
    if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
    deadline=monotonic()+timeout
    with broker_factory(ports,destination,assets,require_receipt=True,result_source=job['port'],
                        allow_same_origin_transfer=job['engine']=='qt',preserve_conflicts=preserve_conflicts,
                        **({'allow_review':True,'required_archives':tuple(required_archives)} if interactive_review else {}),
                        **({'allow_audio_review':True} if audio_review else {})) as broker:
        if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
        # The factory is responsible for honoring cancellation during startup.
        with window_factory(broker,dict(job),destination,cancelled) as windows:
            startup_timeout=getattr(windows,'startup_timeout',45)
            if (not callable(getattr(windows,'is_running',None)) or not callable(getattr(broker,'receiver_started',None))
                    or type(startup_timeout) not in (int,float) or not isfinite(startup_timeout) or not 0<startup_timeout<=60):
                raise MigrationJobError('Fenêtres de récupération indisponibles.')
            startup_deadline=monotonic()+startup_timeout
            receiver_started=False
            if interactive_review and (not callable(getattr(windows,'show_review',None))
                                       or not callable(getattr(broker,'take_review_request',None))):
                raise MigrationJobError('Comparaison des versions indisponible.')
            while True:
                if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
                remaining=deadline-monotonic()
                if remaining<=0:raise MigrationJobError('La récupération a expiré ; les sources sont conservées.')
                if interactive_review and broker.take_review_request():
                    if not windows.is_running() or not windows.show_review():
                        raise MigrationJobError('Comparaison des versions indisponible ; les sources sont conservées.')
                result=broker.wait_result(min(.2,remaining))
                if result is not None:
                    if cancelled():raise MigrationJobError('Migration interrompue ; les sources sont conservées.')
                    if not windows.is_running():raise MigrationJobError('La fenêtre de récupération s’est arrêtée sans confirmation.')
                    if result=={'status':'conflict'}:raise MigrationConflict('Des données différentes existent sur les deux origines.')
                    if result=={'status':'restart'}:
                        if not interactive_review:raise MigrationJobError('Reprise de récupération invalide.')
                        raise MigrationRestart('Les copies sont conservées ; relancez Kiara pour les vérifier.')
                    if result=={'status':'archive-unavailable'}:
                        if not required_archives:raise MigrationJobError('Vérification de copie invalide.')
                        raise MigrationArchiveUnavailable('Une version conservée est introuvable ou illisible.')
                    if result=={'status':'unavailable'}:raise MigrationJobError('Les données n’ont pas pu être vérifiées.')
                    if (not isinstance(result,dict) or not {'status','copied','identical'} <= set(result) <= {'status','copied','identical','preserved','archived'} or result['status']!='ok'
                            or any(type(result[name]) is not int or result[name]<0 for name in ('copied','identical'))
                            or ('preserved' in result and (type(result['preserved']) is not int or result['preserved']<0
                                                            or (result['preserved']>0 and not preserve_conflicts)))
                            or ('archived' in result and (type(result['archived']) is not int or result['archived']<0
                                                           or (result['archived']>0 and not interactive_review)))
                            or result['copied']+result['identical']+result.get('preserved',0)+result.get('archived',0)
                                !=job['localEntries']+job['audioChunks']+job.get('audioArchives',0)):
                        raise MigrationJobError('Copie incomplète ; les sources sont conservées.')
                    archive_ids=broker.verified_archive_ids() if result.get('archived') else ()
                    if (not isinstance(archive_ids,(tuple,list)) or len(archive_ids)!=result.get('archived',0)
                            or any(not isinstance(item,str) or not re.fullmatch(
                                r'(?:audio-)?[0-9a-f]{64}' if audio_review else r'[0-9a-f]{64}',item) for item in archive_ids)
                            or len(set(archive_ids))!=len(archive_ids)):
                        raise MigrationJobError('Les copies locales ne peuvent pas être vérifiées.')
                    return {'copied':result['copied'],'identical':result['identical'],
                            **({'preserved':result['preserved']} if result.get('preserved') else {}),
                            **({'archived':result['archived'],'archive_ids':list(archive_ids)} if result.get('archived') else {})}
                if not receiver_started:
                    receiver_started=broker.receiver_started()
                    if not receiver_started and monotonic()>=startup_deadline:
                        raise MigrationReceiverUnavailable('La réception locale ne démarre pas ; les sources sont conservées.')
                if not windows.is_running():raise MigrationJobError('La fenêtre de récupération s’est arrêtée sans confirmation.')


def execute_snapshot(job, destination, ports, assets, window_factory, cancelled, *, timeout=120,
                     broker_factory=PortalRecoveryBroker, audio_archives=False):
    """Verify a source's content fingerprint without transferring its values."""
    ports=tuple(ports)
    if (type(audio_archives) is not bool
            or len(ports)!=10 or len(set(ports))!=10 or any(type(port) is not int or not 1024<=port<=65535 for port in ports)
            or type(destination) is not int or destination not in ports
            or not isinstance(job,dict) or set(job)!=({'engine','port','localEntries','audioChunks','audioArchives'}
                                                       if audio_archives else {'engine','port','localEntries','audioChunks'})
            or job['engine'] not in ('qt','tauri') or type(job['port']) is not int or job['port'] not in ports
            or (job['engine']=='tauri' and job['port']==destination)
            or any(type(job[name]) is not int or not 0<=job[name]<=9007199254740991
                   for name in (('localEntries','audioChunks','audioArchives') if audio_archives else ('localEntries','audioChunks')))
            or (audio_archives and job['audioArchives']>3000)
            or not callable(window_factory) or not callable(cancelled)
            or not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not isfinite(timeout) or not 0<timeout<=600):
        raise ValueError('Paramètres de vérification invalides.')
    if cancelled():raise MigrationJobError('Vérification interrompue ; les sources sont conservées.')
    deadline=monotonic()+timeout
    with broker_factory(ports,destination,assets,require_receipt=True,result_source=job['port'],result_mode='snapshot',
                        allow_same_origin_transfer=job['engine']=='qt',
                        **({'snapshot_audio_archives':True} if audio_archives else {})) as broker:
        if cancelled():raise MigrationJobError('Vérification interrompue ; les sources sont conservées.')
        with window_factory(broker,dict(job),destination,cancelled) as windows:
            if not callable(getattr(windows,'is_running',None)):
                raise MigrationJobError('Fenêtres de vérification indisponibles.')
            while True:
                if cancelled():raise MigrationJobError('Vérification interrompue ; les sources sont conservées.')
                remaining=deadline-monotonic()
                if remaining<=0:raise MigrationJobError('La vérification a expiré ; les sources sont conservées.')
                result=broker.wait_result(min(.2,remaining))
                if result is not None:
                    if cancelled():raise MigrationJobError('Vérification interrompue ; les sources sont conservées.')
                    if not windows.is_running():raise MigrationJobError('La fenêtre de vérification s’est arrêtée sans confirmation.')
                    if (not isinstance(result,dict) or set(result)!=({'status','localEntries','audioChunks','audioArchives','digest'}
                                                                     if audio_archives else {'status','localEntries','audioChunks','digest'})
                            or result['status']!='snapshot' or result['localEntries']!=job['localEntries']
                            or result['audioChunks']!=job['audioChunks']
                            or (audio_archives and (type(result['audioArchives']) is not int or result['audioArchives']!=job['audioArchives']))
                            or type(result['localEntries']) is not int or type(result['audioChunks']) is not int
                            or not isinstance(result['digest'],str) or not re.fullmatch(r'[0-9a-f]{64}',result['digest'])):
                        raise MigrationJobError('La source a changé ou ne peut pas être vérifiée.')
                    return {'engine':job['engine'],'port':job['port'],
                            'localEntries':result['localEntries'],'audioChunks':result['audioChunks'],
                            **({'audioArchives':result['audioArchives']} if audio_archives else {}),'digest':result['digest']}
                if not windows.is_running():raise MigrationJobError('La fenêtre de vérification s’est arrêtée sans confirmation.')


def execute_destination_manifest(destination, ports, assets, window_factory, cancelled, *, timeout=120,
                                 broker_factory=PortalRecoveryBroker):
    """Read verified archive fingerprints on the destination, without creating data."""
    ports=tuple(ports)
    if (len(ports)!=10 or len(set(ports))!=10 or any(type(port) is not int or not 1024<=port<=65535 for port in ports)
            or type(destination) is not int or destination not in ports or not callable(window_factory) or not callable(cancelled)
            or not isinstance(timeout,(int,float)) or isinstance(timeout,bool) or not isfinite(timeout) or not 0<timeout<=600):
        raise ValueError('Paramètres de vérification invalides.')
    if cancelled():raise MigrationJobError('Vérification interrompue ; les copies sont conservées.')
    deadline=monotonic()+timeout
    with broker_factory(ports,destination,assets,require_receipt=True,result_source=destination,result_mode='manifest',
                        allow_same_origin_transfer=True) as broker:
        with window_factory(broker,{'engine':'tauri','port':destination},destination,cancelled) as windows:
            if not callable(getattr(windows,'is_running',None)):
                raise MigrationJobError('Fenêtre de vérification indisponible.')
            while True:
                if cancelled():raise MigrationJobError('Vérification interrompue ; les copies sont conservées.')
                remaining=deadline-monotonic()
                if remaining<=0:raise MigrationJobError('La vérification des copies a expiré.')
                result=broker.wait_result(min(.2,remaining))
                if result is not None:
                    if cancelled() or not windows.is_running():raise MigrationJobError('Vérification des copies interrompue.')
                    if not isinstance(result,dict) or set(result)!={'status','audioArchiveIds'} or result['status']!='manifest':
                        raise MigrationArchiveUnavailable('Les copies audio ne peuvent pas être vérifiées.')
                    ids=result['audioArchiveIds']
                    if (not isinstance(ids,list) or len(ids)>3000
                            or any(not isinstance(item,str) or not re.fullmatch(r'[0-9a-f]{64}',item) for item in ids)
                            or len(set(ids))!=len(ids)):
                        raise MigrationArchiveUnavailable('Les copies audio ne peuvent pas être vérifiées.')
                    return tuple(sorted(ids))
                if not windows.is_running():raise MigrationJobError('La fenêtre de vérification s’est arrêtée sans confirmation.')
