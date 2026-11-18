"""All engines and origins are accounted for before any port is chosen."""
import unittest
from portal_migration_plan import MigrationPlanError,migration_plan,execute_migration

PORTS=tuple(range(17841,17851))
def reports(occupied=()):
    return [{'port':port,'localEntries':int(port in occupied),'audioChunks':int(port in occupied)} for port in PORTS]


class MigrationPlanTests(unittest.TestCase):
    def test_empty_new_profile_chooses_default_without_jobs(self):
        self.assertEqual(migration_plan(reports(),None),{'destination':17841,'jobs':[]})

    def test_qt_data_on_destination_still_requires_cross_engine_copy(self):
        plan=migration_plan(reports(),reports((17844,)))
        self.assertEqual(plan['destination'],17844)
        self.assertEqual(plan['jobs'],[{'engine':'qt','port':17844,'localEntries':1,'audioChunks':1}])

    def test_all_nonempty_origins_become_jobs_without_overwriting(self):
        plan=migration_plan(reports((17843,17848)),reports((17843,17846)))
        self.assertEqual(plan['destination'],17843)
        self.assertEqual([(job['engine'],job['port']) for job in plan['jobs']],
                         [('tauri',17848),('qt',17843),('qt',17846)])

    def test_fixed_thunderbird_port_wins_and_all_sources_are_retained(self):
        plan=migration_plan(reports((17844,)),reports((17845,)),fixed_port=17841)
        self.assertEqual(plan['destination'],17841)
        self.assertEqual([(job['engine'],job['port']) for job in plan['jobs']],[('tauri',17844),('qt',17845)])

    def test_unknown_unavailable_or_incomplete_inventory_never_selects(self):
        for kind in ('missing','unknown','unavailable','duplicate','invalid_count'):
            data=reports()
            if kind=='missing':data.pop()
            if kind=='unknown':data[2]['future']=True
            if kind=='unavailable':data[2]={'port':PORTS[2],'unavailable':True}
            if kind=='duplicate':data[2]['port']=PORTS[1]
            if kind=='invalid_count':data[2]['audioChunks']=True
            with self.subTest(kind=kind),self.assertRaises(MigrationPlanError):migration_plan(data,None)
        with self.assertRaises(MigrationPlanError):migration_plan(reports(),reports()[:-1])

    def test_report_inputs_are_not_reused_or_mutated(self):
        original=reports((17844,));plan=migration_plan(original,None,fixed_port=17841)
        original[3]['localEntries']=99
        self.assertEqual(plan['jobs'][0]['localEntries'],1)
        with self.assertRaises(MigrationPlanError):migration_plan(reports(),None,fixed_port=True)

    def test_audio_archives_select_their_existing_origin_and_preserve_other_sources(self):
        data=[{**item,'audioArchives':int(item['port']==17848)} for item in reports((17843,))]
        plan=migration_plan(data,None,allow_audio_archives=True)
        self.assertEqual(plan['destination'],17848)
        self.assertEqual(plan['jobs'],[{'engine':'tauri','port':17843,'localEntries':1,'audioChunks':1}])
        with self.assertRaises(MigrationPlanError):migration_plan(data,None)
        with self.assertRaises(MigrationPlanError):migration_plan(data,None,fixed_port=17843,allow_audio_archives=True)

    def test_multiple_archive_locations_and_qt_archives_block_until_they_can_be_copied(self):
        data=[{**item,'audioArchives':int(item['port'] in (17843,17848))} for item in reports()]
        with self.assertRaisesRegex(MigrationPlanError,'copies audio'):migration_plan(data,None,allow_audio_archives=True)
        data=[{**item,'audioArchives':0} for item in reports()]
        qt=[{**item,'audioArchives':int(item['port']==17846)} for item in reports()]
        with self.assertRaisesRegex(MigrationPlanError,'copies audio'):migration_plan(data,qt,allow_audio_archives=True)
        data[0]['audioArchives']=3001
        with self.assertRaises(MigrationPlanError):migration_plan(data,None,allow_audio_archives=True)

    def test_explicit_archive_transfer_plans_multiple_origins_qt_and_fixed_port(self):
        tauri=[{**item,'audioArchives':int(item['port'] in (17843,17848))} for item in reports()]
        qt=[{**item,'audioArchives':int(item['port']==17846)} for item in reports()]
        plan=migration_plan(tauri,qt,fixed_port=17841,allow_audio_archives=True,copy_audio_archives=True)
        self.assertEqual(plan['destination'],17841)
        self.assertEqual([(item['engine'],item['port'],item['audioArchives']) for item in plan['jobs']],
                         [('tauri',17843,1),('tauri',17848,1),('qt',17846,1)])
        calls=[]
        def run(job,dest,phase):
            calls.append((job['engine'],job['port'],phase))
            return {'copied':1 if phase=='copy' else 0,'identical':1 if phase=='verify' else 0}
        result=execute_migration(tauri,qt,run,lambda:False,fixed_port=17841,allow_audio_archives=True,copy_audio_archives=True)
        self.assertEqual(result,{'destination':17841,'jobs':3,'copied':3,'identical':0})
        self.assertEqual(len(calls),6)
        with self.assertRaises(MigrationPlanError):migration_plan(tauri,qt,copy_audio_archives=True)
        with self.assertRaises(MigrationPlanError):
            execute_migration(tauri,qt,lambda *_:{'copied':0,'identical':0},lambda:False,
                              fixed_port=17841,allow_audio_archives=True,copy_audio_archives=True)

    def test_extended_plan_requires_complete_valid_archive_manifests(self):
        data=[{**item,'audioArchives':int(item['port']==17848),
               'audioArchiveIds':['a'*64] if item['port']==17848 else []} for item in reports((17843,))]
        plan=migration_plan(data,None,allow_audio_archives=True,copy_audio_archives=True,require_audio_ids=True)
        self.assertEqual(plan['destination'],17848);self.assertEqual(plan['jobs'][0]['audioArchives'],0)
        bad=[dict(item) for item in data];bad[7]['audioArchiveIds']=[]
        with self.assertRaises(MigrationPlanError):
            migration_plan(bad,None,allow_audio_archives=True,copy_audio_archives=True,require_audio_ids=True)
        with self.assertRaises(MigrationPlanError):migration_plan(data,None,require_audio_ids=True)

    def test_every_source_is_copied_then_replayed_without_writing_a_marker(self):
        calls=[]
        def run(job,destination,phase):
            calls.append((job['engine'],job['port'],destination,phase))
            return {'copied':2 if phase=='copy' else 0,'identical':0 if phase=='copy' else 2}
        result=execute_migration(reports((17843,17848)),reports((17843,)),run,lambda:False)
        self.assertEqual(result,{'destination':17843,'jobs':2,'copied':4,'identical':0})
        self.assertEqual(calls,[('tauri',17848,17843,'copy'),('qt',17843,17843,'copy'),
                                ('tauri',17848,17843,'verify'),('qt',17843,17843,'verify')])

    def test_incomplete_or_changed_job_never_finishes(self):
        qt=reports((17844,))
        with self.assertRaises(MigrationPlanError):
            execute_migration(reports(),qt,lambda *_:{'copied':1,'identical':0},lambda:False)
        def changed(_job,_destination,phase):
            return {'copied':2 if phase=='copy' else 1,'identical':0 if phase=='copy' else 1}
        with self.assertRaisesRegex(MigrationPlanError,'changé'):
            execute_migration(reports(),qt,changed,lambda:False)

    def test_cancellation_between_jobs_stops_before_verification(self):
        calls=[]
        def run(job,destination,phase):calls.append(job);return {'copied':2,'identical':0}
        def cancelled():return len(calls)>0
        with self.assertRaisesRegex(MigrationPlanError,'interrompue'):
            execute_migration(reports((17843,17848)),reports((17843,)),run,cancelled)
        self.assertEqual(len(calls),1)

    def test_previous_version_can_be_preserved_without_being_called_identical(self):
        result=execute_migration(reports(),reports((17844,)),lambda *_:{'copied':0,'identical':1,'preserved':1},lambda:False)
        self.assertEqual(result,{'destination':17844,'jobs':1,'copied':0,'identical':1,'preserved':1})



if __name__=='__main__':unittest.main()
