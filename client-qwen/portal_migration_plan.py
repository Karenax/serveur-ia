"""Experimental plan for preserving Qt and Tauri origins before selection.

The caller must hold the profile lock, reserve all ports, verify every report,
and run each job with non-destructive copies. This module writes nothing.
"""
import re
from portal_origin_state import FIRST_PORT, LAST_PORT


class MigrationPlanError(ValueError):
    pass


def _reports(name, entries, ports, allow_audio_archives=False, require_audio_ids=False):
    if not isinstance(entries, list) or len(entries) != len(ports):
        raise MigrationPlanError(f'Inventaire {name} incomplet.')
    result=[]
    for expected, entry in zip(ports, entries):
        if not isinstance(entry, dict) or entry.get('port') != expected or type(entry.get('port')) is not int:
            raise MigrationPlanError(f'Inventaire {name} incohérent.')
        if set(entry)=={'port','unavailable'} and entry['unavailable'] is True:
            raise MigrationPlanError(f'Inventaire {name} inaccessible.')
        fields=('localEntries','audioChunks','audioArchives') if allow_audio_archives else ('localEntries','audioChunks')
        if set(entry)!=({'port',*fields}|({'audioArchiveIds'} if require_audio_ids else set())):
            raise MigrationPlanError(f'Inventaire {name} inconnu.')
        if any(type(entry[field]) is not int or not 0 <= entry[field] <= 9007199254740991
               for field in fields) or (allow_audio_archives and entry['audioArchives']>3000):
            raise MigrationPlanError(f'Inventaire {name} invalide.')
        value={'port':expected,**{field:entry[field] for field in fields}}
        if require_audio_ids:
            ids=entry['audioArchiveIds']
            if (not isinstance(ids,list) or len(ids)!=entry['audioArchives']
                    or any(not isinstance(item,str) or not re.fullmatch(r'[0-9a-f]{64}',item) for item in ids)
                    or len(set(ids))!=len(ids)):
                raise MigrationPlanError(f'Empreintes {name} invalides.')
            value['audioArchiveIds']=sorted(ids)
        result.append(value)
    return result


def migration_plan(tauri_reports, qt_reports, *, fixed_port=None, allow_audio_archives=False,
                   copy_audio_archives=False, require_audio_ids=False):
    """Plan all nonempty sources, including Qt on the destination origin.

    ``qt_reports`` may be None only after absence of Qt storage was established.
    A plan is not a confirmation and never authorizes overwriting or deletion.
    """
    ports=tuple(range(FIRST_PORT,LAST_PORT+1))
    if (type(allow_audio_archives) is not bool or type(copy_audio_archives) is not bool or type(require_audio_ids) is not bool
            or ((copy_audio_archives or require_audio_ids) and not allow_audio_archives)):
        raise MigrationPlanError('Inventaire audio invalide.')
    if fixed_port is not None and (type(fixed_port) is not int or fixed_port not in ports):
        raise MigrationPlanError('Port imposé invalide.')
    tauri=_reports('Tauri',tauri_reports,ports,allow_audio_archives,require_audio_ids)
    qt=[] if qt_reports is None else _reports('Qt',qt_reports,ports,allow_audio_archives,require_audio_ids)
    occupied=lambda report:bool(report['localEntries'] or report['audioChunks'] or report.get('audioArchives',0))
    tauri_used=[report for report in tauri if occupied(report)]
    qt_used=[report for report in qt if occupied(report)]
    archive_ports=[report['port'] for report in tauri if report.get('audioArchives',0)]
    if not copy_audio_archives and (len(archive_ports)>1 or any(report.get('audioArchives',0) for report in qt)):
        raise MigrationPlanError('Plusieurs emplacements de copies audio nécessitent une récupération vérifiée.')
    if not copy_audio_archives and archive_ports and fixed_port is not None and fixed_port!=archive_ports[0]:
        raise MigrationPlanError('Le port imposé ne contient pas les copies audio conservées.')
    destination=fixed_port if fixed_port is not None else (
        archive_ports[0] if archive_ports else tauri_used[0]['port'] if tauri_used else qt_used[0]['port'] if qt_used else ports[0])
    # The archive-aware job schema is explicitly opt-in and must be handled by
    # a runner that verifies and copies every archive before confirming a job.
    job=lambda engine,report:{'engine':engine,'port':report['port'],
                              'localEntries':report['localEntries'],'audioChunks':report['audioChunks'],
                              **({'audioArchives':report['audioArchives']} if copy_audio_archives else {})}
    jobs=([job('tauri',report) for report in tauri_used if report['port']!=destination]
          + [job('qt',report) for report in qt_used])
    return {'destination':destination,'jobs':jobs}


def execute_migration(tauri_reports, qt_reports, run_job, cancelled, *, fixed_port=None,
                      allow_audio_archives=False, copy_audio_archives=False, require_audio_ids=False):
    """Copy all planned sources, then replay each to verify identical results.

    No marker is written here. ``run_job`` must preserve the source and return
    only counts after its source has been checked for changes. A previously
    verified source may report a preserved divergent local value; audio and
    newly changed sources still conflict. Cancellation, incomplete counts or
    a new write during verification fails.
    """
    if not callable(run_job) or not callable(cancelled):
        raise MigrationPlanError('Contrôle de migration invalide.')
    plan=migration_plan(tauri_reports,qt_reports,fixed_port=fixed_port,allow_audio_archives=allow_audio_archives,
                        copy_audio_archives=copy_audio_archives,require_audio_ids=require_audio_ids)
    jobs=plan['jobs']
    totals={'copied':0,'identical':0}
    for phase in ('copy','verify'):
        for job in jobs:
            if cancelled():raise MigrationPlanError('Migration interrompue ; les sources sont conservées.')
            result=run_job(dict(job),plan['destination'],phase)
            if (not isinstance(result,dict) or not {'copied','identical'} <= set(result) <= {'copied','identical','preserved','archived','archive_ids'}
                    or any(type(result[name]) is not int or result[name]<0 for name in ('copied','identical'))
                    or ('preserved' in result and (type(result['preserved']) is not int or result['preserved']<0))
                    or ('archived' in result and (type(result['archived']) is not int or result['archived']<0))
                    or (bool(result.get('archived')) != ('archive_ids' in result))
                    or ('archive_ids' in result and (not isinstance(result['archive_ids'],list)
                        or len(result['archive_ids'])!=result.get('archived',0)
                        or any(not isinstance(item,str) or not re.fullmatch(r'(?:audio-)?[0-9a-f]{64}',item) for item in result['archive_ids'])
                        or len(set(result['archive_ids']))!=len(result['archive_ids'])))
                    or result['copied']+result['identical']+result.get('preserved',0)+result.get('archived',0)
                        !=job['localEntries']+job['audioChunks']+job.get('audioArchives',0)):
                raise MigrationPlanError('Copie incomplète ; les sources sont conservées.')
            if phase=='verify' and result['copied']:
                raise MigrationPlanError('Les données ont changé pendant la vérification ; les sources sont conservées.')
            if phase=='copy':
                totals['copied']+=result['copied'];totals['identical']+=result['identical']
                if result.get('preserved'):totals['preserved']=totals.get('preserved',0)+result['preserved']
                if result.get('archived'):totals['archived']=totals.get('archived',0)+result['archived']
    if cancelled():raise MigrationPlanError('Migration interrompue ; les sources sont conservées.')
    return {'destination':plan['destination'],'jobs':len(jobs),**totals}
