"""Only fictional counts; no browser storage is accessed by this runner."""
from contextlib import contextmanager
from time import sleep
import unittest
from unittest.mock import Mock

from portal_migration_job import execute_job,execute_snapshot,execute_destination_manifest,MigrationConflict,MigrationRestart,MigrationArchiveUnavailable,MigrationReceiverUnavailable,MigrationJobError

PORTS=tuple(range(17841,17851))
JOB={'engine':'tauri','port':17842,'localEntries':1,'audioChunks':1}


class FakeBroker:
    def __init__(self,ports,destination,assets,**options):
        self.options=options;self.result=None;self.closed=False
    def __enter__(self):return self
    def __exit__(self,*_):self.closed=True
    def wait_result(self,_timeout):return self.result
    def receiver_started(self):return True


class MigrationJobTests(unittest.TestCase):
    def test_real_broker_keeps_staged_record_when_receiver_never_starts(self):
        from portal_recovery_broker import PortalRecoveryBroker
        from test_portal_recovery_broker import ASSETS, available_ports, request
        ports=tuple(available_ports(10));body=b'{"type":"local","key":"draft","value":"fiction"}'
        job={**JOB,'port':ports[1],'audioChunks':0};observed=[];instances=[]
        def factory(*args,**kwargs):
            broker=PortalRecoveryBroker(*args,**kwargs);instances.append(broker);return broker
        @contextmanager
        def windows(broker,*_):
            headers=lambda port:{'Origin':f'http://127.0.0.1:{port}','X-Kiara-Recovery':broker.token}
            self.assertEqual(request(ports[1],'POST','/recovery/stage',body,headers(ports[1]))[0],200)
            class Window:
                startup_timeout=.05
                def is_running(self):return True
            try:yield Window()
            finally:observed.append(request(ports[0],'POST','/recovery/read',b'',headers(ports[0]))[2])
        with self.assertRaisesRegex(MigrationReceiverUnavailable,'réception locale'):
            execute_job(job,ports[0],ports,ASSETS,windows,lambda:False,timeout=2,broker_factory=factory)
        self.assertEqual(observed,[body]);self.assertFalse(instances[0]._servers)

    def test_missing_receiver_times_out_and_closes_broker_and_window(self):
        instances=[];closed=[]
        class Broker(FakeBroker):
            def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);instances.append(self)
            def receiver_started(self):return False
            def wait_result(self,_timeout):sleep(.005);return None
        @contextmanager
        def windows(*_):
            class Window:
                startup_timeout=.02
                def is_running(self):return True
            try:yield Window()
            finally:closed.append(True)
        with self.assertRaisesRegex(MigrationReceiverUnavailable,'réception locale'):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,broker_factory=Broker)
        self.assertTrue(instances[0].closed);self.assertEqual(closed,[True])

    def test_receiver_start_timeout_does_not_limit_later_transfer_or_review(self):
        class Broker(FakeBroker):
            def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.calls=0
            def wait_result(self,_timeout):
                sleep(.01);self.calls+=1
                return {'status':'ok','copied':1,'identical':1} if self.calls>=5 else None
            def take_review_request(self):return False
        @contextmanager
        def windows(*_):
            class Window:
                startup_timeout=.02
                def is_running(self):return True
                def show_review(self):return True
            yield Window()
        result=execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,
                           broker_factory=Broker,interactive_review=True)
        self.assertEqual(result,{'copied':1,'identical':1})

    def run_job(self,result,*,running=True,cancelled=lambda:False,job=JOB,timeout=1):
        brokers=[];closed=[]
        def broker(*args,**kwargs):
            value=FakeBroker(*args,**kwargs);value.result=result;brokers.append(value);return value
        @contextmanager
        def windows(instance,selected,destination,check):
            self.assertEqual(selected,job);self.assertEqual(destination,PORTS[0])
            class Window:
                def is_running(self):return running
            try:yield Window()
            finally:closed.append(True)
        try:
            return execute_job(job,PORTS[0],PORTS,{},windows,cancelled,timeout=timeout,broker_factory=broker)
        finally:
            if brokers:
                self.assertTrue(brokers[0].closed)
                if closed:self.assertEqual(closed,[True])
                self.assertTrue(brokers[0].options['require_receipt'])
                self.assertEqual(brokers[0].options['result_source'],job['port'])

    def test_returns_only_verified_counts(self):
        self.assertEqual(self.run_job({'status':'ok','copied':1,'identical':1}),{'copied':1,'identical':1})

    def test_review_window_is_shown_only_for_an_explicit_authenticated_request(self):
        displayed=[];brokers=[]
        class ReviewBroker(FakeBroker):
            def take_review_request(self):return True
        def broker(*args,**kwargs):
            value=ReviewBroker(*args,**kwargs);value.result={'status':'ok','copied':1,'identical':1};brokers.append(value);return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
                def show_review(self):displayed.append(True);return True
            yield Window()
        self.assertEqual(execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,
                         broker_factory=broker,interactive_review=True),{'copied':1,'identical':1})
        self.assertEqual(displayed,[True]);self.assertTrue(brokers[0].options['allow_review'])

    def test_review_requires_an_available_window(self):
        class ReviewBroker(FakeBroker):
            def take_review_request(self):return True
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
                def show_review(self):return False
            yield Window()
        with self.assertRaisesRegex(MigrationJobError,'Comparaison'):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,
                        broker_factory=ReviewBroker,interactive_review=True)

    def test_archived_counts_and_restart_require_interactive_mode(self):
        class ReviewBroker(FakeBroker):
            def take_review_request(self):return False
            def verified_archive_ids(self):return ('a'*64,)
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
                def show_review(self):return True
            yield Window()
        def make(result):
            def broker(*args,**kwargs):
                value=ReviewBroker(*args,**kwargs);value.result=result;return value
            return broker
        archived={'status':'ok','copied':1,'identical':0,'archived':1}
        with self.assertRaises(MigrationJobError):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,broker_factory=make(archived))
        self.assertEqual(execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,
                         broker_factory=make(archived),interactive_review=True),
                         {'copied':1,'identical':0,'archived':1,'archive_ids':['a'*64]})
        with self.assertRaises(MigrationRestart):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,
                        broker_factory=make({'status':'restart'}),interactive_review=True)
        with self.assertRaises(MigrationJobError):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,broker_factory=make({'status':'restart'}))
        with self.assertRaises(MigrationArchiveUnavailable):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,broker_factory=make({'status':'archive-unavailable'}),
                        interactive_review=True,required_archives=('a'*64,))
        with self.assertRaises(MigrationJobError):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,timeout=1,broker_factory=make({'status':'archive-unavailable'}),
                        interactive_review=True)

    def test_audio_archive_requires_its_own_explicit_review_option(self):
        seen=[];fingerprint='audio-'+'b'*64
        class ReviewBroker(FakeBroker):
            def take_review_request(self):return False
            def verified_archive_ids(self):return (fingerprint,)
        def broker(*args,**kwargs):
            seen.append(kwargs);value=ReviewBroker(*args,**kwargs)
            value.result={'status':'ok','copied':1,'identical':0,'archived':1};return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
                def show_review(self):return True
            yield Window()
        with self.assertRaises(MigrationJobError):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,interactive_review=True)
        with self.assertRaises(ValueError):
            execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,audio_review=True)
        value=execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,
                          interactive_review=True,audio_review=True,required_archives=(fingerprint,))
        self.assertEqual(value['archive_ids'],[fingerprint]);self.assertTrue(seen[-1]['allow_audio_review'])
        self.assertEqual(seen[-1]['required_archives'],(fingerprint,))

    def test_audio_archive_sources_count_as_independent_verified_items(self):
        job={**JOB,'audioArchives':2};brokers=[]
        class ReviewBroker(FakeBroker):
            def take_review_request(self):return False
        def broker(*args,**kwargs):
            value=ReviewBroker(*args,**kwargs);value.result={'status':'ok','copied':2,'identical':2};brokers.append(value);return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
                def show_review(self):return True
            yield Window()
        result=execute_job(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,
                           interactive_review=True,audio_review=True,copy_audio_archives=True)
        self.assertEqual(result,{'copied':2,'identical':2});self.assertTrue(brokers[0].options['allow_audio_review'])
        with self.assertRaises(ValueError):
            execute_job(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,interactive_review=True)
        def incomplete(*args,**kwargs):
            value=broker(*args,**kwargs);value.result={'status':'ok','copied':1,'identical':1};return value
        with self.assertRaises(MigrationJobError):
            execute_job(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=incomplete,
                        interactive_review=True,audio_review=True,copy_audio_archives=True)

    def test_conflict_unavailable_and_incomplete_never_succeed(self):
        for value,error in [({'status':'conflict'},MigrationConflict),({'status':'unavailable'},MigrationJobError),
                            ({'status':'ok','copied':1,'identical':0},MigrationJobError),
                            ({'status':'ok','copied':True,'identical':1},MigrationJobError),
                            ({'status':'ok','copied':1,'identical':1,'value':'private'},MigrationJobError)]:
            with self.subTest(value=value),self.assertRaises(error):self.run_job(value)

    def test_crashed_window_and_cancellation_fail_closed(self):
        with self.assertRaises(MigrationJobError):self.run_job(None,running=False)
        with self.assertRaises(MigrationJobError):self.run_job(None,cancelled=lambda:True)
        with self.assertRaisesRegex(MigrationJobError,'expiré'):self.run_job(None,timeout=.01)
        cancellation=Mock(side_effect=[False,False,False,True])
        with self.assertRaisesRegex(MigrationJobError,'interrompue'):
            self.run_job({'status':'ok','copied':2,'identical':0},cancelled=cancellation)

    def test_invalid_jobs_and_timeout_are_rejected(self):
        for job in ({**JOB,'port':PORTS[0]},{**JOB,'localEntries':True},{**JOB,'engine':'unknown'},
                    {**JOB,'extra':'private'}):
            with self.subTest(job=job),self.assertRaises(ValueError):self.run_job(None,job=job)
        with self.assertRaises(ValueError):self.run_job(None,timeout=float('nan'))

    def test_snapshot_checks_counts_and_never_returns_source_values(self):
        brokers=[]
        def broker(*args,**kwargs):
            value=FakeBroker(*args,**kwargs);value.result={'status':'snapshot','localEntries':1,'audioChunks':1,'digest':'a'*64};brokers.append(value);return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
            yield Window()
        result=execute_snapshot(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker)
        self.assertEqual(result,{**JOB,'digest':'a'*64})
        self.assertEqual(brokers[0].options['result_mode'],'snapshot');self.assertTrue(brokers[0].closed)
        def malformed(*args,**kwargs):
            value=broker(*args,**kwargs);value.result['localEntries']=2;return value
        with self.assertRaises(MigrationJobError):execute_snapshot(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=malformed)

    def test_extended_snapshot_checks_every_audio_archive_count(self):
        job={**JOB,'audioArchives':2};brokers=[]
        def broker(*args,**kwargs):
            value=FakeBroker(*args,**kwargs);value.result={'status':'snapshot','localEntries':1,'audioChunks':1,
                                                         'audioArchives':2,'digest':'a'*64}
            brokers.append(value);return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
            yield Window()
        result=execute_snapshot(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,audio_archives=True)
        self.assertEqual(result,{**job,'digest':'a'*64});self.assertTrue(brokers[0].options['snapshot_audio_archives'])
        with self.assertRaises(ValueError):execute_snapshot(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker)
        def bad(*args,**kwargs):
            value=broker(*args,**kwargs);value.result['audioArchives']=True;return value
        with self.assertRaises(MigrationJobError):
            execute_snapshot(job,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=bad,audio_archives=True)

    def test_destination_manifest_is_verified_and_fails_closed(self):
        brokers=[];ids=['b'*64,'a'*64]
        def broker(*args,**kwargs):
            value=FakeBroker(*args,**kwargs);value.result={'status':'manifest','audioArchiveIds':ids};brokers.append(value);return value
        @contextmanager
        def windows(_broker,job,destination,_cancelled):
            self.assertEqual(job,{'engine':'tauri','port':destination})
            class Window:
                def is_running(self):return True
            yield Window()
        self.assertEqual(execute_destination_manifest(PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker),tuple(sorted(ids)))
        self.assertEqual(brokers[0].options['result_mode'],'manifest');self.assertTrue(brokers[0].options['allow_same_origin_transfer'])
        def bad(*args,**kwargs):
            value=broker(*args,**kwargs);value.result={'status':'manifest','audioArchiveIds':['bad']};return value
        with self.assertRaises(MigrationArchiveUnavailable):
            execute_destination_manifest(PORTS[0],PORTS,{},windows,lambda:False,broker_factory=bad)

    def test_preserved_versions_require_explicit_authorization(self):
        result={'status':'ok','copied':0,'identical':1,'preserved':1}
        def broker(*args,**kwargs):
            value=FakeBroker(*args,**kwargs);value.result=result;return value
        @contextmanager
        def windows(*_):
            class Window:
                def is_running(self):return True
            yield Window()
        with self.assertRaises(MigrationJobError):execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker)
        self.assertEqual(execute_job(JOB,PORTS[0],PORTS,{},windows,lambda:False,broker_factory=broker,preserve_conflicts=True),
                         {'copied':0,'identical':1,'preserved':1})


if __name__=='__main__':unittest.main()
