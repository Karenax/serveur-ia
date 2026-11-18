"""A verified scan never records a guessed port or destroys an existing choice."""
from pathlib import Path
import tempfile
import unittest

from portal_origin_session import OriginInventorySession, OriginSessionError, recovery_offer, resolve_origin, transfer_offer
from portal_origin_state import OriginStateError, read_origin, record_origin


class FakeBroker:
    def __init__(self, ports, destination, assets, *, inventory_plan):
        self.token = 'fictif'
        self.plan = inventory_plan
        self.complete = None
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def wait_complete(self, timeout):
        return self.complete

    def close(self):
        self.closed = True


class OriginInventorySessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.marker = Path(self.directory.name) / 'origin.json'
        self.session = OriginInventorySession(self.marker, {}, broker_factory=FakeBroker)
        self.addCleanup(self.session.close)

    def scan(self, occupied=()):
        for port in self.session.ports:
            self.session.plan.submit(port, {'localEntries': int(port in occupied), 'audioChunks': 0})

    def test_recovery_offer_has_a_bounded_unambiguous_protocol(self):
        self.assertEqual(recovery_offer('a'*20,'b'*64), 'KIARA_RELAY_ORIGIN_SCAN '+'a'*20+' '+'b'*64)
        for identity,token in (('a'*19,'b'*64),('a'*20,'b'*63),('A'*20,'b'*64),('a'*20,'b'*64+'\n'),('../'+'a'*17,'b'*64)):
            with self.subTest(identity=identity,token=token):
                with self.assertRaises(ValueError):recovery_offer(identity,token)

    def test_transfer_offer_requires_known_ports_and_engine(self):
        value=transfer_offer('a'*20,'b'*64,17842,17841,'tauri')
        self.assertEqual(value,'KIARA_RELAY_ORIGIN_TRANSFER '+'a'*20+' '+'b'*64+' 17842 17841 tauri transfer')
        self.assertTrue(transfer_offer('a'*20,'b'*64,17841,17841,'qt','snapshot').endswith('17841 17841 qt snapshot'))
        self.assertTrue(transfer_offer('a'*20,'b'*64,17841,17841,'tauri','manifest').endswith('17841 17841 tauri manifest'))
        with self.assertRaises(ValueError):transfer_offer('a'*20,'b'*64,17841,17842,'tauri','manifest')
        with self.assertRaises(ValueError):transfer_offer('a'*20,'b'*64,17841,17841,'qt','manifest')
        for source,dest,engine in ((17840,17841,'qt'),(17841,17851,'qt'),(17841,17841,'tauri'),
                                   (True,17841,'qt'),(17841,17842,'other')):
            with self.subTest(source=source,dest=dest,engine=engine),self.assertRaises(ValueError):
                transfer_offer('a'*20,'b'*64,source,dest,engine)
        with self.assertRaises(ValueError):transfer_offer('a'*20,'b'*64,17842,17841,'tauri','other')

    def test_only_acknowledged_complete_scan_records_selected_origin(self):
        descriptor = self.session.start()
        broker = self.session.broker
        self.assertEqual(descriptor['ports'], tuple(range(17841, 17851)))
        self.scan((17844,))
        self.assertIsNone(self.session.finish())
        self.assertFalse(self.marker.exists())
        broker.complete = 17844
        self.assertEqual(self.session.finish(), 17844)
        self.assertEqual(read_origin(self.marker), 17844)
        self.assertTrue(broker.closed)

    def test_ambiguous_or_incomplete_scan_never_commits_even_with_false_ack(self):
        self.session.start()
        self.session.broker.complete = 17841
        with self.assertRaises(OriginSessionError):self.session.finish()
        self.scan((17842, 17845))
        with self.assertRaises(OriginSessionError):self.session.finish()
        self.assertFalse(self.marker.exists())

    def test_other_acknowledged_port_is_refused(self):
        self.session.start();self.scan((17844,));self.session.broker.complete = 17845
        with self.assertRaises(OriginSessionError):self.session.finish()
        self.assertFalse(self.marker.exists())

    def test_existing_choice_is_not_overwritten_or_scanned(self):
        record_origin(self.marker, 17848)
        before = self.marker.read_bytes()
        with self.assertRaises(OriginSessionError):self.session.start()
        self.assertEqual(self.marker.read_bytes(), before)
        self.assertIsNone(self.session.broker)

    def test_context_interruption_releases_reservations_without_marker(self):
        with self.assertRaisesRegex(RuntimeError, 'interruption'):
            with self.session:
                broker = self.session.broker
                raise RuntimeError('interruption')
        self.assertTrue(broker.closed)
        self.assertFalse(self.marker.exists())

    def test_fixed_port_rejects_a_different_occupied_origin(self):
        session = OriginInventorySession(self.marker, {}, fixed_port=17842, broker_factory=FakeBroker)
        self.addCleanup(session.close);session.start()
        for port in session.ports:
            session.plan.submit(port, {'localEntries': int(port == 17844), 'audioChunks': 0})
        session.broker.complete = 17842
        with self.assertRaises(OriginSessionError):session.finish()
        self.assertFalse(self.marker.exists())

    def test_startup_resolver_reuses_existing_choice_without_opening_window(self):
        record_origin(self.marker, 17844)
        def unexpected(_):raise AssertionError('Une fenêtre ne doit pas être ouverte.')
        self.assertEqual(resolve_origin(self.marker, {}, unexpected, lambda:False),17844)
        with self.assertRaises(OriginSessionError):
            resolve_origin(self.marker, {}, unexpected, lambda:False, fixed_port=17841)
        self.assertEqual(read_origin(self.marker),17844)

    def test_startup_resolver_closes_broker_on_cancellation(self):
        sessions=[]
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
            sessions.append(session);return session
        descriptors=[]
        with self.assertRaises(OriginSessionError):
            resolve_origin(self.marker, {}, descriptors.append, lambda:True, session_factory=factory)
        self.assertEqual(len(descriptors),1)
        self.assertTrue(sessions[0].finished)
        self.assertFalse(self.marker.exists())

    def test_startup_resolver_records_only_the_acknowledged_origin(self):
        sessions=[]
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
            sessions.append(session);return session
        def announce(descriptor):
            self.assertEqual(descriptor['token'],'fictif')
            session=sessions[0]
            for port in session.ports:
                session.plan.submit(port,{'localEntries':int(port==17844),'audioChunks':0})
            session.broker.complete=17844
        self.assertEqual(resolve_origin(self.marker,{},announce,lambda:False,session_factory=factory),17844)
        self.assertEqual(read_origin(self.marker),17844)
        self.assertTrue(sessions[0].finished)

    def test_startup_resolver_closes_broker_if_window_fails(self):
        sessions=[]
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
            sessions.append(session);return session
        def failed(_):raise RuntimeError('fenêtre impossible')
        with self.assertRaisesRegex(RuntimeError,'fenêtre impossible'):
            resolve_origin(self.marker, {}, failed, lambda:False, session_factory=factory)
        self.assertTrue(sessions[0].finished)
        self.assertFalse(self.marker.exists())

    def test_startup_timeout_leaves_no_marker(self):
        sessions=[]
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
            sessions.append(session);return session
        with self.assertRaisesRegex(OriginSessionError,'expiré'):
            resolve_origin(self.marker,{},lambda _:None,lambda:False,timeout=.01,session_factory=factory)
        self.assertTrue(sessions[0].finished)
        self.assertFalse(self.marker.exists())

    def test_concurrent_port_choice_is_never_replaced(self):
        sessions=[]
        def factory(*args,**kwargs):
            session=OriginInventorySession(*args,**kwargs,broker_factory=FakeBroker)
            sessions.append(session);return session
        def announce(_):
            session=sessions[0]
            for port in session.ports:
                session.plan.submit(port,{'localEntries':int(port==17844),'audioChunks':0})
            session.broker.complete=17844
            record_origin(self.marker,17849)
        with self.assertRaises(OriginStateError):
            resolve_origin(self.marker,{},announce,lambda:False,session_factory=factory)
        self.assertEqual(read_origin(self.marker),17849)
        self.assertTrue(sessions[0].finished)


if __name__ == '__main__':
    unittest.main()
