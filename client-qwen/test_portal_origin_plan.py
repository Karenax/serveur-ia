import unittest
from concurrent.futures import ThreadPoolExecutor
from portal_origin_plan import InventoryPlanError, OriginInventoryPlan

PORTS = tuple(range(17841,17851))
EMPTY = {'localEntries':0,'audioChunks':0}

class OriginInventoryPlanTests(unittest.TestCase):
    def plan(self, fixed=None):
        return OriginInventoryPlan(PORTS,default_port=PORTS[0],fixed_port=fixed)

    def test_all_ports_must_be_inventoried_before_selecting_empty_origin(self):
        p=self.plan()
        for index,port in enumerate(PORTS):
            state=p.status();self.assertEqual(state['state'],'scanning');self.assertEqual(state['nextPort'],port)
            result=p.submit(port,EMPTY)
            if index<9:self.assertNotIn('port',result)
        self.assertEqual(p.status(),{'state':'ready','checked':10,'total':10,'port':17841})

    def test_only_existing_origin_is_selected_without_moving_data(self):
        p=self.plan()
        for port in PORTS:p.submit(port,{'localEntries':2,'audioChunks':1} if port==17846 else EMPTY)
        self.assertEqual(p.status()['port'],17846)

    def test_multiple_origins_and_fixed_port_require_recovery(self):
        p=self.plan()
        for port in PORTS:p.submit(port,{'localEntries':1,'audioChunks':0} if port in (17841,17848) else EMPTY)
        status=p.status();self.assertEqual(status['state'],'needsRecovery');self.assertEqual([o['port'] for o in status['origins']],[17841,17848]);self.assertNotIn('port',status)
        q=self.plan(fixed=17841)
        for port in PORTS:q.submit(port,{'localEntries':0,'audioChunks':1} if port==17842 else EMPTY)
        self.assertEqual(q.status()['state'],'needsRecovery')

    def test_unavailable_or_out_of_order_never_proves_an_origin_empty(self):
        p=self.plan()
        with self.assertRaises(InventoryPlanError):p.submit(17842,EMPTY)
        p.submit(17841,{'unavailable':True})
        self.assertEqual(p.status()['state'],'unavailable')
        self.assertNotIn('port',p.status())
        with self.assertRaises(InventoryPlanError):p.submit(17842,EMPTY)
        with self.assertRaises(InventoryPlanError):p.submit(17841,EMPTY)

    def test_duplicate_report_is_idempotent_but_changed_report_is_rejected(self):
        p=self.plan();result=p.submit(17841,EMPTY)
        self.assertEqual(p.submit(17841,EMPTY),result)
        with self.assertRaises(InventoryPlanError):p.submit(17841,{'localEntries':1,'audioChunks':0})
        self.assertEqual(p.status(),result)

    def test_invalid_counts_and_unknown_fields_are_rejected(self):
        for report in ({'localEntries':True,'audioChunks':0},{'localEntries':-1,'audioChunks':0},
                       {'localEntries':9007199254740992,'audioChunks':0}, {'unavailable':1},
                       {'localEntries':0,'audioChunks':0,'extra':'secret'}):
            p=self.plan()
            with self.assertRaises(InventoryPlanError):p.submit(17841,report)
            self.assertEqual(p.status()['checked'],0)

    def test_archive_only_origin_is_not_treated_as_empty_and_requires_explicit_schema(self):
        empty={**EMPTY,'audioArchives':0};p=OriginInventoryPlan(PORTS,default_port=PORTS[0],allow_audio_archives=True)
        with self.assertRaises(InventoryPlanError):p.submit(PORTS[0],EMPTY)
        for port in PORTS:p.submit(port,{**empty,'audioArchives':1} if port==17846 else empty)
        self.assertEqual(p.status()['state'],'ready');self.assertEqual(p.status()['port'],17846)
        self.assertEqual(p.reports()[5]['audioArchives'],1)
        with self.assertRaises(InventoryPlanError):self.plan().submit(PORTS[0],empty)
        q=OriginInventoryPlan(PORTS,default_port=PORTS[0],allow_audio_archives=True)
        with self.assertRaises(InventoryPlanError):q.submit(PORTS[0],{**empty,'audioArchives':3001})

    def test_archive_manifest_is_verified_and_returned_as_independent_copies(self):
        p=OriginInventoryPlan(PORTS,default_port=PORTS[0],allow_audio_archives=True,require_audio_ids=True)
        for invalid in ({**EMPTY,'audioArchives':1,'audioArchiveIds':[]},
                        {**EMPTY,'audioArchives':1,'audioArchiveIds':['A'*64]},
                        {**EMPTY,'audioArchives':2,'audioArchiveIds':['a'*64,'a'*64]}):
            with self.subTest(invalid=invalid),self.assertRaises(InventoryPlanError):p.submit(PORTS[0],invalid)
        ids=['b'*64,'a'*64];p.submit(PORTS[0],{**EMPTY,'audioArchives':2,'audioArchiveIds':ids});ids.clear()
        empty={**EMPTY,'audioArchives':0,'audioArchiveIds':[]}
        for port in PORTS[1:]:p.submit(port,empty)
        reports=p.reports();self.assertEqual(reports[0]['audioArchiveIds'],['a'*64,'b'*64])
        reports[0]['audioArchiveIds'].clear();self.assertEqual(p.reports()[0]['audioArchiveIds'],['a'*64,'b'*64])
        with self.assertRaises(InventoryPlanError):
            OriginInventoryPlan(PORTS,default_port=PORTS[0],require_audio_ids=True)

    def test_concurrent_conflicting_reports_cannot_both_be_accepted(self):
        p=self.plan()
        def submit(report):
            try:return p.submit(17841,report)
            except InventoryPlanError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(submit,[EMPTY,{'localEntries':1,'audioChunks':0}]))
        self.assertEqual(sum(value is None for value in values),1)
        self.assertEqual(p.status()['checked'],1)

if __name__ == '__main__':unittest.main()
