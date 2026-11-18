"""Linux portal integration using a private D-Bus and synthetic images only."""
import asyncio
import base64
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def capture_under_test():
    module_path = os.environ.get('KIARA_TEST_CAPTURE_MODULE')
    if module_path:
        spec = importlib.util.spec_from_file_location('packaged_screen_capture', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.capture
    from linux_screen_capture import capture
    return capture


async def fake_portal():
    from dbus_next import Message, MessageType, Variant
    from dbus_next.aio import MessageBus
    bus = await MessageBus().connect()
    attacker = await MessageBus().connect()
    await bus.request_name('org.freedesktop.portal.Desktop')

    def on_message(message):
        if (message.message_type != MessageType.METHOD_CALL
                or message.interface != 'org.freedesktop.portal.Screenshot'
                or message.member != 'Screenshot'):
            return None
        options = message.body[1]
        if not options['interactive'].value:
            return Message.new_error(message, 'org.test.Error', 'Interactive selection required')
        handle = ('/org/freedesktop/portal/desktop/request/' + message.sender[1:].replace('.', '_')
                  + '/' + options['handle_token'].value)
        outcome = os.environ['KIARA_TEST_OUTCOME']
        results = {} if outcome == 'cancel' else {'uri': Variant('s', os.environ['KIARA_TEST_URI'])}
        signal = Message.new_signal(handle, 'org.freedesktop.portal.Request', 'Response',
                                    'ua{sv}', [1 if outcome == 'cancel' else 0, results])
        if outcome == 'inject':
            forged = Message.new_signal(handle, 'org.freedesktop.portal.Request', 'Response',
                                        'ua{sv}', [0, {'uri': Variant('s', 'https://example.invalid/forged')}])
            forged.destination = message.sender
            attacker.send(forged)
            asyncio.get_running_loop().call_later(.05, bus.send, signal)
        else:
            # Emit before the method reply to exercise the subscription race.
            bus.send(signal)
        return Message.new_method_return(message, 'o', [handle])

    bus.add_message_handler(on_message)
    print('ready', flush=True)
    await asyncio.Event().wait()


@unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux and a private session bus')
class LinuxScreenCaptureTests(unittest.TestCase):
    def setUp(self):
        from PySide6.QtGui import QColor, QImage
        self.temporary = tempfile.TemporaryDirectory()
        self.image = Path(self.temporary.name) / 'capture.png'
        image = QImage(80, 40, QImage.Format.Format_RGB32)
        image.fill(QColor('blue'))
        self.assertTrue(image.save(str(self.image)))
        self.portal = None

    def tearDown(self):
        if self.portal:
            self.portal.terminate()
            self.portal.wait(timeout=5)
            self.portal.stdout.close()
        self.temporary.cleanup()

    def start_portal(self, outcome='ok', uri=None):
        environment = dict(os.environ, KIARA_TEST_OUTCOME=outcome,
                           KIARA_TEST_URI=uri or self.image.as_uri())
        self.portal = subprocess.Popen([sys.executable, __file__, '--fake-portal'], env=environment,
                                       stdout=subprocess.PIPE, text=True)
        self.assertEqual(self.portal.stdout.readline().strip(), 'ready')

    def test_preview_image_and_early_portal_response(self):
        from PySide6.QtGui import QImage
        self.start_portal()
        result = capture_under_test()()
        self.assertFalse(result['cancelled'])
        self.assertTrue(result['image'].startswith('data:image/jpeg;base64,'))
        image = QImage.fromData(base64.b64decode(result['image'].split(',')[1]))
        self.assertEqual((image.width(), image.height()), (80, 40))
        self.assertGreater(image.pixelColor(10, 10).blue(), 200)
        self.assertTrue(self.image.exists(), 'portal-owned files must not be deleted')

    def test_user_cancellation_has_no_image(self):
        self.start_portal('cancel')
        self.assertEqual(capture_under_test()(), {'cancelled': True})

    def test_remote_uri_is_rejected(self):
        self.start_portal(uri='https://example.invalid/capture.png')
        with self.assertRaises(ValueError):
            capture_under_test()()

    def test_directed_signal_from_another_process_is_ignored(self):
        self.start_portal('inject')
        self.assertFalse(capture_under_test()()['cancelled'])


if __name__ == '__main__':
    if '--fake-portal' in sys.argv:
        asyncio.run(fake_portal())
    else:
        unittest.main()
