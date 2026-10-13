"""Mirror Fred projects through the installed Hermes native Project API.

Fred remains authoritative for documents and permissions. Native project folders
contain a metadata manifest, while document contents are read through Fred MCP.
No profile-wide active project is changed by a conversation.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading

from core import HIDDEN, write_json
from hermes_service import child_environment, installation, prepare_runtime
from workspace import Denied, identifier


_NATIVE = r'''
import json, sys
from pathlib import Path
from hermes_cli import projects_db as native
data=json.load(sys.stdin)
home=Path(data['home']).resolve()
with native.connect_closing(home/'projects.db') as db:
    operation=data['operation']
    if operation=='ensure':
        source=data['project']; slug='fred-'+source['id']; folder=str(Path(data['folder']).resolve())
        project=native.get_project(db,slug)
        if project is None:
            pid=native.create_project(db,name=source['title'],slug=slug,description=source['instructions'],
                                      folders=[folder],primary_path=folder)
        else:
            pid=project.id
            native.update_project(db,pid,name=source['title'],description=source['instructions'])
            native.add_folder(db,pid,folder,is_primary=True)
            for previous in project.folders:
                if Path(previous.path).resolve()!=Path(folder).resolve():
                    native.remove_folder(db,pid,previous.path)
        if source['archived']: native.archive_project(db,pid)
        else: native.restore_project(db,pid)
        result=native.get_project(db,pid).to_dict()
    elif operation=='synchronize':
        retained=set(data['retained'])
        changed=0
        for project in native.list_projects(db,include_archived=True):
            if project.slug.startswith('fred-') and project.slug[5:] not in retained and not project.archived:
                native.archive_project(db,project.id); changed+=1
        result={'archived_missing':changed}
    elif operation=='list':
        result={'projects':[p.to_dict() for p in native.list_projects(db,include_archived=True)],
                'active_id':native.get_active_id(db)}
    elif operation=='bind':
        project=native.get_project(db,'fred-'+data['project_id'])
        if project is None or project.archived: raise ValueError('project unavailable')
        from hermes_state import SessionDB
        with SessionDB(home/'state.db') as sessions:
            session=sessions.get_session(data['session_id'])
            if session is None and data.get('create'):
                sessions.ensure_session(data['session_id'],'api',cwd=data['folder'],profile_name=home.name)
                session=sessions.get_session(data['session_id'])
            if session is None: raise ValueError('session unavailable')
            profile=session.get('profile_name')
            if profile and profile!=home.name: raise ValueError('session profile mismatch')
            generation=sessions.update_session_cwd(data['session_id'],data['folder'])
            if generation is None: raise ValueError('session unavailable')
        result={'project_id':project.id,'session_id':data['session_id'],'cwd':data['folder']}
    else: raise ValueError('unknown project operation')
print(json.dumps(result,ensure_ascii=False))
'''


def _linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


class HermesProjects:
    def __init__(self, accounts, workspace, service=None, *, source=None, runner=None):
        self.accounts, self.workspace, self.service = accounts, workspace, service
        self.source, self.runner = source, runner
        self.lock = threading.RLock()

    def _profile(self, owner):
        if not isinstance(owner, str) or not re.fullmatch('[a-f0-9]{16}', owner):
            raise Denied('Identité de projet Hermes invalide.')
        if not self.accounts.enabled(owner):
            raise Denied('Profil Hermes non autorisé ou non prêt.')
        profile = 'fred-' + owner
        home = self.accounts.root / 'profiles' / profile
        if _linked(home) or not home.is_dir() or not home.resolve().is_relative_to(self.accounts.root.resolve()):
            raise Denied('Espace du projet Hermes indisponible.')
        return home

    def _folder(self, home, identity):
        path = home
        for component in ('workspace', 'projects', identifier(identity)):
            path /= component
            if _linked(path): raise Denied('Lien interdit dans un projet Hermes Fred.')
        path.mkdir(parents=True, exist_ok=True)
        if not path.resolve().is_relative_to(home.resolve()): raise Denied('Projet hors du profil Hermes Fred.')
        return path

    def _native(self, home, operation, **values):
        payload = {'home': str(home.resolve()), 'operation': operation, **values}
        if self.runner: return self.runner(payload)
        runtime = getattr(self.service, 'runtime', None) or installation(self.source)
        prepare_runtime(self.accounts.root, runtime)
        result = subprocess.run([str(runtime['python']), '-c', _NATIVE], input=json.dumps(payload).encode('utf-8'),
                                capture_output=True, cwd=runtime['source'], env=child_environment(home, runtime),
                                timeout=30, creationflags=HIDDEN)
        if result.returncode or len(result.stdout) > 1024 * 1024:
            raise ValueError('Synchronisation du projet Hermes indisponible.')
        try: return json.loads(result.stdout)
        except (ValueError, UnicodeError): raise ValueError('Réponse du registre de projets Hermes invalide.') from None

    def ensure(self, owner, project_id):
        """Create/refresh one owned native project; renames retain its native id."""
        with self.lock:
            home = self._profile(owner)
            with self.workspace.db() as db:
                p = self.workspace.own(db, 'projects', project_id, owner)
                documents = [dict(r) for r in db.execute('SELECT id,title,kind,revision FROM documents '
                            'WHERE owner=? AND project=? ORDER BY id', (owner, p['id']))]
            folder = self._folder(home, p['id'])
            result = self._native(home, 'ensure', project=p, folder=str(folder.resolve()))
            # Content remains in the access-controlled Workspace; references travel in backups.
            write_json(folder / 'fred-project.json', {'version': 1, 'fred_project_id': p['id'],
                       'hermes_project_id': result['id'], 'title': p['title'], 'instructions': p['instructions'],
                       'revision': p['revision'], 'archived': bool(p['archived']), 'documents': documents,
                       'document_access': 'fred-mcp'})
            return result

    def synchronize(self, owner):
        """Reconcile all projects of an access, archiving removed native entries."""
        with self.lock:
            home = self._profile(owner)
            with self.workspace.db() as db:
                identities = [r[0] for r in db.execute('SELECT id FROM projects WHERE owner=? ORDER BY id', (owner,))]
            results = [self.ensure(owner, identity) for identity in identities]
            self._native(home, 'synchronize', retained=identities)
            return {'projects': results}

    def bind_session(self, owner, project_id, session_id, *, create=False):
        """Native association is the session cwd matching the native project folder."""
        if not isinstance(session_id, str) or not re.fullmatch('[a-zA-Z0-9_-]{1,200}', session_id):
            raise ValueError('Session Hermes invalide.')
        with self.lock:
            project = self.ensure(owner, project_id)
            if project['archived']: raise Denied('Projet archivé ; session refusée.')
            home = self._profile(owner); folder = self._folder(home, project_id)
            return self._native(home, 'bind', project_id=project_id, session_id=session_id,
                                folder=str(folder.resolve()), create=bool(create))
