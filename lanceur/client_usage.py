"""Durable aggregate client presence; never store tokens, prompts or audio."""
from __future__ import annotations
import copy
import datetime as dt
import json
import math
from pathlib import Path
import re
import threading
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from core import write_json

GAP = 300
RETENTION = 180
try:
    TIMEZONE = ZoneInfo('Europe/Paris')
except ZoneInfoNotFoundError:
    TIMEZONE = None


def local(epoch):
    return dt.datetime.fromtimestamp(epoch, TIMEZONE)


class ClientUsage:
    def __init__(self, home):
        self.path = Path(home)/'activite-clients.json'
        self.lock = threading.RLock()
        self.error = ''
        self.saved_at = 0
        self.dirty = False
        self.data = {'format':1,'started_epoch':time.time(),'days':{},'last':{}}
        if self.path.exists():
            try:
                value = json.loads(self.path.read_text(encoding='utf-8-sig'))
                self.validate(value)
                self.data = value
            except (OSError,ValueError,TypeError,KeyError):
                self.data = None
                self.error = 'Historique d’activité illisible. Le fichier original est conservé.'

    @staticmethod
    def validate(value):
        def number(number):
            return type(number) in (int,float) and math.isfinite(number) and number >= 0
        if not isinstance(value,dict) or value.get('format') != 1 or not number(value.get('started_epoch')):
            raise ValueError('Historique invalide.')
        if not isinstance(value.get('days'),dict) or len(value['days']) > RETENTION+2 or not isinstance(value.get('last'),dict):
            raise ValueError('Historique invalide.')
        for day,clients in value['days'].items():
            if dt.date.fromisoformat(day).isoformat() != day:
                raise ValueError('Date d’historique invalide.')
            if not isinstance(clients,dict) or len(clients) > 10000:
                raise ValueError('Historique invalide.')
            for identity,row in clients.items():
                if not re.fullmatch('[0-9a-f]{16}',identity) or not isinstance(row,dict) or type(row.get('sessions')) is not int or row['sessions'] < 0 or not number(row.get('seconds')):
                    raise ValueError('Historique invalide.')
        if len(value['last']) > 10000 or any(not re.fullmatch('[0-9a-f]{16}',key) or not number(epoch) for key,epoch in value['last'].items()):
            raise ValueError('Historique invalide.')

    def _row(self, day, identity):
        return self.data['days'].setdefault(day,{}).setdefault(identity,{'sessions':0,'seconds':0.0})

    def _save(self, now):
        if now-self.saved_at < 30:
            return
        cutoff = (local(now).date()-dt.timedelta(days=RETENTION-1)).isoformat()
        days = {day:rows for day,rows in self.data['days'].items() if day >= cutoff}
        last = {key:epoch for key,epoch in self.data['last'].items() if local(epoch).date().isoformat() >= cutoff}
        self.dirty |= len(days) != len(self.data['days']) or len(last) != len(self.data['last'])
        if not self.dirty:
            return
        self.data['days'],self.data['last'] = days,last
        self.saved_at = now
        try:
            write_json(self.path,self.data)
            self.dirty = False
            self.error = ''
        except OSError:
            self.error = 'L’activité est affichée, mais son enregistrement a échoué. Vérifiez l’espace disque et les droits du dossier serveur.'

    def touch(self, identity, now=None):
        now = time.time() if now is None else now
        if not re.fullmatch('[0-9a-f]{16}',identity):
            return
        with self.lock:
            if self.data is None:
                return
            previous = self.data['last'].get(identity)
            if previous is not None and now-previous < 1:
                return
            self.data['last'][identity] = now
            if previous is None or now-previous > GAP:
                self._row(local(now).date().isoformat(),identity)['sessions'] += 1
            else:
                # Split at local midnight, including clock changes.
                cursor = previous
                while cursor < now:
                    day = local(cursor).date()
                    midnight = dt.datetime.combine(day+dt.timedelta(days=1),dt.time(),tzinfo=TIMEZONE).timestamp()
                    end = min(now,midnight)
                    self._row(day.isoformat(),identity)['seconds'] += end-cursor
                    cursor = end
            self.dirty = True
            self._save(now)

    def summary(self, records, period='day', now=None):
        if period not in ('day','week'):
            raise ValueError('Période attendue : day ou week.')
        with self.lock:
            now = time.time() if now is None else now
            if self.data is None:
                return {'available':False,'error':self.error}
            self._save(now)
            data = copy.deepcopy(self.data)
            warning = self.error
        today = local(now).date()
        start = today-dt.timedelta(days=27) if period == 'day' else today-dt.timedelta(days=today.weekday()+7*7)
        buckets = {}
        count = (today-start).days+1
        for offset in range(count):
            day = start+dt.timedelta(days=offset)
            key = day if period == 'day' else day-dt.timedelta(days=day.weekday())
            buckets.setdefault(key.isoformat(),{'date':key.isoformat(),'sessions':0,'seconds':0.0,'clients':set()})
        totals = {}
        for day,clients in data['days'].items():
            if not start.isoformat() <= day <= today.isoformat():
                continue
            date = dt.date.fromisoformat(day)
            key = date if period == 'day' else date-dt.timedelta(days=date.weekday())
            bucket = buckets[key.isoformat()]
            for identity,row in clients.items():
                total = totals.setdefault(identity,{'sessions':0,'seconds':0.0})
                for field in ('sessions','seconds'):
                    total[field] += row[field]
                    bucket[field] += row[field]
                bucket['clients'].add(identity)
        known = {row['id']:row for row in records}
        rows = []
        for identity in known.keys() | totals.keys():
            record = known.get(identity,{})
            last = data['last'].get(identity)
            enabled = bool(record) and not record.get('revoked') and not record.get('suspended') and not record.get('deleted') and (not record.get('expires_epoch') or record['expires_epoch'] > now)
            rows.append({'id':identity,'name':record.get('name','Client supprimé'),
                         'deleted':not record or bool(record.get('deleted')),
                         'online':enabled and last is not None and 0 <= now-last <= 120,
                         'last_epoch':last,**totals.get(identity,{'sessions':0,'seconds':0.0})})
        rows.sort(key=lambda row:(not row['online'],-row['sessions'],row['name'].casefold()))
        return {'available':True,'warning':warning,'period':period,'start':start.isoformat(),
                'end':today.isoformat(),'started_epoch':data['started_epoch'],'retention_days':RETENTION,
                'timezone':'Europe/Paris' if TIMEZONE else 'Heure locale du serveur',
                'session_gap_seconds':GAP,'online':sum(row['online'] for row in rows),
                'sessions':sum(row['sessions'] for row in totals.values()),
                'seconds':sum(row['seconds'] for row in totals.values()),'active_clients':len(totals),
                'buckets':[{**bucket,'clients':len(bucket['clients'])} for bucket in buckets.values()],
                'clients':rows,'generated_epoch':now}
