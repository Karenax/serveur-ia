"""Native Hermes projects are per-access and survive rename, archive and restore."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import HIDDEN
from hermes_projects import HermesProjects
from hermes_service import child_environment, installation
from workspace import Workspace, Denied

OWNER = 'a'*16
OTHER = 'b'*16


class ProjectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the user's installed library, with every write confined to a temporary Fred root.
        try: cls.runtime = installation()
        except (OSError, ValueError): raise unittest.SkipTest('Hermes runtime not installed')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fred-hermes-projects-')
        self.home = Path(self.tmp.name); self.root = self.home / 'hermes-fred'
        for owner in (OWNER, OTHER):
            profile = self.root / 'profiles' / ('fred-'+owner); profile.mkdir(parents=True)
            (profile / 'profile.yaml').write_text('description: Fred integration test\n', encoding='utf-8')
        self.workspace = Workspace(self.home)
        self.accounts = SimpleNamespace(root=self.root, enabled=lambda owner: owner in (OWNER, OTHER))
        self.projects = HermesProjects(self.accounts, self.workspace, SimpleNamespace(runtime=self.runtime))
        self.project = self.workspace.action(OWNER, {'action': 'project_create', 'title': 'Même nom'})['id']
        self.other = self.workspace.action(OTHER, {'action': 'project_create', 'title': 'Même nom'})['id']

    def tearDown(self):
        self.workspace.shutdown(); self.tmp.cleanup()

    def native(self, owner, operation, **values):
        return self.projects._native(self.projects._profile(owner), operation, **values)

    def test_real_native_registry_isolated_idempotent_and_keeps_active_project(self):
        first = self.projects.ensure(OWNER, self.project)
        second = self.projects.ensure(OWNER, self.project)
        foreign = self.projects.ensure(OTHER, self.other)
        self.assertEqual(first['id'], second['id'])
        self.assertNotEqual(first['id'], foreign['id'])
        self.assertEqual(first['slug'], 'fred-'+self.project)
        listing = self.native(OWNER, 'list')
        self.assertEqual(len(listing['projects']), 1)
        self.assertIsNone(listing['active_id'])
        with self.assertRaises(Denied): self.projects.ensure(OWNER, self.other)
        self.workspace.action(OWNER, {'action': 'project_save', 'id': self.project, 'revision': 1,
                                     'title': 'Renommé', 'instructions': 'Répondre en français', 'archived': True})
        renamed = self.projects.ensure(OWNER, self.project)
        self.assertEqual(renamed['id'], first['id'])
        self.assertEqual(renamed['name'], 'Renommé')
        self.assertTrue(renamed['archived'])
        self.workspace.action(OWNER, {'action': 'project_save', 'id': self.project, 'revision': 2,
                                     'title': 'Renommé', 'instructions': 'Répondre en français', 'archived': False})
        self.assertFalse(self.projects.ensure(OWNER, self.project)['archived'])

    def test_metadata_documents_and_real_session_cwd(self):
        document = self.workspace.action(OWNER, {'action': 'document_create', 'project': self.project,
                                                'title': 'Budget', 'text': 'Ne pas copier ce contenu privé dans un fichier.'})['id']
        self.projects.ensure(OWNER, self.project)
        profile = self.projects._profile(OWNER)
        folder = profile / 'workspace/projects' / self.project
        metadata = json.loads((folder / 'fred-project.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['documents'][0]['id'], document)
        self.assertNotIn('Ne pas copier', (folder / 'fred-project.json').read_text(encoding='utf-8'))
        script = "from hermes_state import SessionDB; from hermes_constants import get_hermes_home; " \
                 "\nwith SessionDB(get_hermes_home()/'state.db') as db: db.create_session('test-fred-session','api')"
        process = subprocess.run([str(self.runtime['python']), '-c', script], cwd=self.runtime['source'],
                                 capture_output=True, env=child_environment(profile, self.runtime),
                                 timeout=30, creationflags=HIDDEN)
        self.assertEqual(process.returncode, 0, process.stderr.decode('utf-8', errors='replace')[-1000:])
        bound = self.projects.bind_session(OWNER, self.project, 'test-fred-session')
        self.assertEqual(Path(bound['cwd']), folder.resolve())
        self.assertIsNone(self.native(OWNER, 'list')['active_id'])
        created = self.projects.bind_session(OWNER, self.project, 'new-fred-generated-session', create=True)
        self.assertEqual(Path(created['cwd']), folder.resolve())
        with self.assertRaises(ValueError): self.projects.bind_session(OWNER, self.project, '../bad')
        with self.assertRaises(ValueError): self.projects.bind_session(OTHER, self.other, 'test-fred-session')

    def test_reconcile_removed_project_archives_native_entry(self):
        self.projects.synchronize(OWNER)
        with self.workspace.db() as db: db.execute('DELETE FROM projects WHERE id=?', (self.project,))
        self.projects.synchronize(OWNER)
        self.assertTrue(self.native(OWNER, 'list')['projects'][0]['archived'])


if __name__ == '__main__': unittest.main()
