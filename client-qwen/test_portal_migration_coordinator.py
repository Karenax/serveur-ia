"""Full orchestration over fictitious count reports and temporary markers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from portal_migration_coordinator import resolve_migration
from portal_migration_job import MigrationConflict,MigrationJobError,MigrationArchiveUnavailable
from portal_origin_state import record_origin,read_origin
from portal_migration_state import read_state,write_state,MigrationStateError

PROFILE='a'*20
def encrypt(value):return b'fake:'+value
def decrypt(value):
    if not value.startswith(b'fake:'):raise ValueError('invalid')
    return value[5:]


class FakeBroker:
    token='b'*64
    def __init__(self,ports,destination,assets,**kwargs):
        self.ports=ports;self.destination=destination;self.plan=kwargs.get('inventory_plan');self.closed=False
    def __enter__(self):return self
    def __exit__(self,*_):self.closed=True
    def wait_complete(self,_):
        status=self.plan.status()
        return status.get('port') if status['state']=='ready' else None


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.marker=Path(self.tmp.name)/'origin.json';self.state=Path(self.tmp.name)/'state';self.brokers=[]
        snapshot=patch('portal_migration_coordinator.execute_snapshot',side_effect=lambda job,*a,**k:{**job,'digest':'a'*64})
        self.snapshot=snapshot.start();self.addCleanup(snapshot.stop)
    def factory(self,*args,**kwargs):
        broker=FakeBroker(*args,**kwargs);self.brokers.append(broker);return broker
    def announce(self,occupied):
        def emit(_descriptor):
            plan=self.brokers[-1].plan
            for port in plan.ports:plan.submit(port,{'localEntries':int(port in occupied),'audioChunks':0})
        return emit
    def resolve(self,occupied,qt=None,**kwargs):
        try:
            return resolve_migration(self.marker,{}, {},self.announce(occupied),lambda _cancelled:qt,
                                     lambda *_:None,lambda:False,state_path=self.state,profile=PROFILE,encrypt=encrypt,decrypt=decrypt,
                                     broker_factory=self.factory,**kwargs)
        finally:self.assertTrue(all(b.closed for b in self.brokers))
    def test_empty_inventory_records_default_only_after_second_reservation(self):
        self.assertEqual(self.resolve(()),17841)
        self.assertEqual(read_origin(self.marker),17841);self.assertEqual(len(self.brokers),2)

    def test_multiple_origins_are_copied_then_replayed_before_marker(self):
        calls=[]
        def copy(job,dest,*args,**kwargs):
            self.assertFalse(self.marker.exists());calls.append((job['port'],dest))
            return {'copied':int(len(calls)==1),'identical':int(len(calls)>1)}
        with patch('portal_migration_coordinator.execute_job',side_effect=copy):
            self.assertEqual(self.resolve((17842,17844)),17842)
        self.assertEqual(calls,[(17844,17842),(17844,17842)]);self.assertEqual(read_origin(self.marker),17842)

    def test_conflict_never_records_or_replaces_marker(self):
        with patch('portal_migration_coordinator.execute_job',side_effect=MigrationConflict('fictif')):
            with self.assertRaises(MigrationConflict):self.resolve((17842,17844))
        self.assertFalse(self.marker.exists())
        record_origin(self.marker,17842);before=self.marker.read_bytes()
        with patch('portal_migration_coordinator.execute_job',side_effect=MigrationConflict('fictif')):
            with self.assertRaises(MigrationConflict):self.resolve((17842,17844))
        self.assertEqual(self.marker.read_bytes(),before)

    def test_existing_marker_and_fixed_pairing_must_agree(self):
        record_origin(self.marker,17842)
        with self.assertRaises(MigrationJobError):self.resolve((),fixed_port=17843)
        self.assertEqual(read_origin(self.marker),17842);self.assertEqual(self.brokers,[])

    def test_audio_checkpoint_is_refused_until_audio_verification_is_connected(self):
        source={'engine':'tauri','port':17844,'localEntries':0,'audioChunks':1,'digest':'a'*64}
        write_state(self.state,PROFILE,17842,[source],encrypt,decrypt,
                    archives={('tauri',17844):{'audio-'+'b'*64}})
        before=self.state.read_bytes()
        with self.assertRaisesRegex(MigrationStateError,'copies audio'):
            self.resolve((17842,17844),interactive_review=True)
        self.assertEqual(self.brokers,[]);self.assertFalse(self.marker.exists())
        self.assertEqual(self.state.read_bytes(),before)

    def test_extended_migration_checks_destination_archives_before_and_after_all_sources(self):
        a,b,c=('a'*64,'b'*64,'c'*64);sources=[]
        def report(port,identifier=None):
            return {'port':port,'localEntries':0,'audioChunks':0,'audioArchives':int(identifier is not None),
                    'audioArchiveIds':[identifier] if identifier else []}
        tauri=[report(port,b if port==17842 else a if port==17844 else None) for port in range(17841,17851)]
        qt=[report(port,c if port==17846 else None) for port in range(17841,17851)]
        def announce(_):
            plan=self.brokers[-1].plan
            for row in tauri:plan.submit(row['port'],{key:value for key,value in row.items() if key!='port'})
        def copy(job,_dest,*_args,**kwargs):
            self.assertTrue(kwargs['audio_review'] and kwargs['copy_audio_archives'])
            sources.append((job['engine'],job['port']))
            return {'copied':1,'identical':0} if len(sources)<=2 else {'copied':0,'identical':1}
        assets={'/recovery':b'x','/recovery.js':b'x','/portal_origin_recovery.js':b'x'}
        with patch('portal_migration_coordinator.execute_destination_manifest',side_effect=[(b,),(a,b,c)]), \
             patch('portal_migration_coordinator.execute_job',side_effect=copy):
            result=resolve_migration(self.marker,assets,assets,announce,lambda _:qt,lambda *_:None,lambda:False,
                state_path=self.state,profile=PROFILE,encrypt=encrypt,decrypt=decrypt,broker_factory=self.factory,
                fixed_port=17842,interactive_review=True,audio_archives=True)
        self.assertEqual(result,17842);self.assertEqual(sources,[('tauri',17844),('qt',17846)]*2)
        saved=read_state(self.state,PROFILE,decrypt)
        self.assertEqual(saved['format'],6);self.assertEqual(saved['destinationArchives'],[a,b,c]);before=self.state.read_bytes()
        tauri[1]=report(17842,a)
        with patch('portal_migration_coordinator.execute_destination_manifest',return_value=(a,)), \
             patch('portal_migration_coordinator.execute_job') as copy_job:
            with self.assertRaises(MigrationArchiveUnavailable):
                resolve_migration(self.marker,assets,assets,announce,lambda _:qt,lambda *_:None,lambda:False,
                    state_path=self.state,profile=PROFILE,encrypt=encrypt,decrypt=decrypt,broker_factory=self.factory,
                    fixed_port=17842,interactive_review=True,audio_archives=True)
            copy_job.assert_not_called()
        self.assertEqual(self.state.read_bytes(),before);self.assertEqual(read_origin(self.marker),17842)

    def test_extended_migration_does_not_commit_an_incomplete_destination(self):
        a,b='a'*64,'b'*64
        def announce(_):
            for port in self.brokers[-1].plan.ports:
                ids=[b] if port==17842 else [a] if port==17844 else []
                self.brokers[-1].plan.submit(port,{'localEntries':0,'audioChunks':0,'audioArchives':len(ids),'audioArchiveIds':ids})
        count=[]
        def copy(*_args,**_kwargs):
            count.append(1);return {'copied':1,'identical':0} if len(count)==1 else {'copied':0,'identical':1}
        assets={'/recovery':b'x','/recovery.js':b'x','/portal_origin_recovery.js':b'x'}
        with patch('portal_migration_coordinator.execute_destination_manifest',side_effect=[(b,),(b,)]), \
             patch('portal_migration_coordinator.execute_job',side_effect=copy):
            with self.assertRaises(MigrationArchiveUnavailable):
                resolve_migration(self.marker,assets,assets,announce,lambda _:None,lambda *_:None,lambda:False,
                    state_path=self.state,profile=PROFILE,encrypt=encrypt,decrypt=decrypt,broker_factory=self.factory,
                    fixed_port=17842,interactive_review=True,audio_archives=True)
        self.assertFalse(self.marker.exists());self.assertFalse(self.state.exists())

    def test_unavailable_qt_report_does_not_become_empty(self):
        invalid=[{'port':port,'unavailable':True} for port in range(17841,17851)]
        with self.assertRaises(ValueError):self.resolve((),qt=invalid)
        self.assertFalse(self.marker.exists())

    def test_occupied_ports_at_commit_do_not_create_marker(self):
        def factory(*args,**kwargs):
            if not kwargs:raise OSError('fictif')
            return self.factory(*args,**kwargs)
        with self.assertRaises(OSError):
            resolve_migration(self.marker,{}, {},self.announce(()),lambda _:None,lambda *_:None,lambda:False,
                              state_path=self.state,profile=PROFILE,encrypt=encrypt,decrypt=decrypt,broker_factory=factory)
        self.assertFalse(self.marker.exists());self.assertTrue(all(b.closed for b in self.brokers))

    def test_unchanged_source_preserves_new_destination_and_repairs_missing_entries(self):
        def initial(job,dest,*args,**kwargs):
            return {'copied':1,'identical':0} if initial.calls%2==0 else {'copied':0,'identical':1}
        initial.calls=0
        def first(*args,**kwargs):
            result=initial(*args,**kwargs);initial.calls+=1;return result
        with patch('portal_migration_coordinator.execute_job',side_effect=first):self.resolve((17842,17844))
        state_before=self.state.read_bytes();calls=[]
        def retained(job,dest,*args,**kwargs):
            calls.append(kwargs['preserve_conflicts']);return {'copied':0,'identical':0,'preserved':1}
        with patch('portal_migration_coordinator.execute_job',side_effect=retained):self.resolve((17842,17844))
        self.assertEqual(calls,[True,True]);self.assertEqual(self.state.read_bytes(),state_before)
        calls=[]
        def repair(job,dest,*args,**kwargs):
            calls.append(kwargs['preserve_conflicts']);return {'copied':1,'identical':0} if len(calls)==1 else {'copied':0,'identical':1}
        with patch('portal_migration_coordinator.execute_job',side_effect=repair):self.resolve((17842,17844))
        self.assertEqual(calls,[True,True]);self.assertEqual(read_origin(self.marker),17842)

    def test_changed_source_is_not_trusted_and_checkpoint_stays_unchanged(self):
        calls=[]
        def initial(job,dest,*args,**kwargs):
            calls.append(1);return {'copied':1,'identical':0} if len(calls)==1 else {'copied':0,'identical':1}
        with patch('portal_migration_coordinator.execute_job',side_effect=initial):self.resolve((17842,17844))
        before=self.state.read_bytes();self.snapshot.side_effect=lambda job,*a,**k:{**job,'digest':'b'*64}
        def conflict(job,dest,*args,**kwargs):
            self.assertFalse(kwargs['preserve_conflicts']);raise MigrationConflict('fictif')
        with patch('portal_migration_coordinator.execute_job',side_effect=conflict):
            with self.assertRaises(MigrationConflict):self.resolve((17842,17844))
        self.assertEqual(self.state.read_bytes(),before);self.assertEqual(read_origin(self.marker),17842)

    def test_source_changing_during_migration_never_commits_checkpoint(self):
        self.snapshot.side_effect=[{'engine':'tauri','port':17844,'localEntries':1,'audioChunks':0,'digest':'a'*64},
                                   {'engine':'tauri','port':17844,'localEntries':1,'audioChunks':0,'digest':'b'*64}]
        count=[]
        def copy(*args,**kwargs):
            count.append(1);return {'copied':1,'identical':0} if len(count)==1 else {'copied':0,'identical':1}
        with patch('portal_migration_coordinator.execute_job',side_effect=copy):
            with self.assertRaises(MigrationJobError):self.resolve((17842,17844))
        self.assertFalse(self.marker.exists());self.assertFalse(self.state.exists())

    def test_source_with_archived_conflict_is_never_silently_preserved_afterward(self):
        calls=[]
        def archived(job,dest,*args,**kwargs):
            calls.append(kwargs['preserve_conflicts'])
            self.assertTrue(kwargs['interactive_review'])
            return {'copied':0,'identical':0,'archived':1,'archive_ids':['b'*64]}
        with patch('portal_migration_coordinator.execute_job',side_effect=archived):
            self.resolve((17842,17844),interactive_review=True)
        self.assertEqual(calls,[False,False])
        self.assertEqual(read_state(self.state,PROFILE,decrypt)['protected'],[{'engine':'tauri','port':17844,'ids':['b'*64]}])
        previous=self.state.read_bytes()
        def missing(job,dest,*args,**kwargs):
            self.assertFalse(kwargs['preserve_conflicts'])
            self.assertEqual(kwargs['required_archives'],('b'*64,))
            raise MigrationConflict('Copie fictive absente')
        with patch('portal_migration_coordinator.execute_job',side_effect=missing):
            with self.assertRaises(MigrationConflict):self.resolve((17842,17844),interactive_review=True)
        self.assertEqual(self.state.read_bytes(),previous)
        with self.assertRaisesRegex(MigrationJobError,'interactive'):self.resolve((17842,17844))
        with self.assertRaisesRegex(MigrationJobError,'source protégée'):self.resolve((17842,),interactive_review=True)
        self.assertEqual(self.state.read_bytes(),previous)

    def test_old_experimental_protection_without_archive_ids_is_not_treated_as_verified(self):
        entry={'engine':'tauri','port':17844,'localEntries':1,'audioChunks':0,'digest':'a'*64}
        write_state(self.state,PROFILE,17842,[entry],encrypt,decrypt,protected={('tauri',17844)})
        record_origin(self.marker,17842);before=self.state.read_bytes()
        with self.assertRaisesRegex(MigrationStateError,'empreintes nécessaires'):
            self.resolve((17842,17844),interactive_review=True)
        self.assertEqual(self.state.read_bytes(),before);self.assertEqual(read_origin(self.marker),17842)


if __name__=='__main__':unittest.main()
