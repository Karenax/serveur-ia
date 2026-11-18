"""The recovery phase and updater share one reader without losing commands."""
import os
import time
import unittest

from relay_control_stream import RelayControlStream


class RelayControlStreamTests(unittest.TestCase):
    def pipe(self, capacity=16, buffering=0):
        reader, writer = os.pipe()
        stream = os.fdopen(reader, 'rb', buffering=buffering)
        self.addCleanup(stream.close)
        return RelayControlStream(stream, capacity=capacity), writer

    def test_commands_remain_available_to_updater_after_recovery(self):
        control,writer=self.pipe()
        try:
            os.write(writer,b'cu')
            self.assertEqual(control.read(1),b'c')
            self.assertEqual(control.read(1),b'u')
            self.assertFalse(control.cancelled())
        finally:os.close(writer)
        self.assertEqual(control.read(1),b'')
        self.assertTrue(control.cancelled())

    def test_buffered_pipe_preserves_ack_update_and_eof(self):
        control,writer=self.pipe(buffering=4096)
        try:
            os.write(writer,b'Kcu')
            self.assertTrue(control.wait_recovery_ack(2))
            self.assertEqual(control.read(),b'c')
            self.assertEqual(control.read(),b'u')
        finally:os.close(writer)
        self.assertEqual(control.read(),b'')
        self.assertTrue(control.cancelled())

    def test_closed_desktop_is_observed_without_waiting_for_a_command(self):
        control,writer=self.pipe();os.close(writer)
        deadline=time.monotonic()+3
        while not control.cancelled() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(control.cancelled())
        self.assertEqual(control.read(),b'')

    def test_overflow_stops_the_channel_instead_of_growing_without_bound(self):
        control,writer=self.pipe(capacity=1)
        try:
            os.write(writer,b'cu')
            deadline=time.monotonic()+3
            while not control.cancelled() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(control.cancelled())
            self.assertEqual(control.read(),b'c')
            self.assertEqual(control.read(),b'')
        finally:os.close(writer)

    def test_invalid_read_size_is_rejected(self):
        control,writer=self.pipe()
        try:
            with self.assertRaises(ValueError):control.read(2)
        finally:os.close(writer)

    def test_recovery_ack_is_bounded_and_preserves_later_updates(self):
        control,writer=self.pipe()
        try:
            self.assertFalse(control.wait_recovery_ack(.01))
            os.write(writer,b'Kc')
            self.assertTrue(control.wait_recovery_ack(2))
            self.assertEqual(control.read(),b'c')
            for value in (0,True,float('nan')):
                with self.assertRaises(ValueError):control.wait_recovery_ack(value)
        finally:os.close(writer)

    def test_wrong_ack_and_closed_pipe_fail_closed(self):
        control,writer=self.pipe()
        try:
            os.write(writer,b'X')
            with self.assertRaises(ValueError):control.wait_recovery_ack(2)
        finally:os.close(writer)
        deadline=time.monotonic()+3
        while not control.cancelled() and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(control.wait_recovery_ack(1))


if __name__ == '__main__':unittest.main()
