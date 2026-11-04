"""FIFO admission, exact queue bound and timed-out waiter removal."""
from concurrent.futures import ThreadPoolExecutor
import unittest
from gateway_embeddings import EmbeddingQueue


class EmbeddingQueueTests(unittest.TestCase):
    def test_one_active_16_waiting_fifo_and_overflow(self):
        queue=EmbeddingQueue();order=[]
        self.assertTrue(queue.acquire())
        def run(index):
            if not queue.acquire(timeout=5):raise TimeoutError('admission')
            try:order.append(index)
            finally:queue.release()
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures=[]
            try:
                for index in range(16):
                    futures.append(pool.submit(run,index))
                    with queue.condition:
                        self.assertTrue(queue.condition.wait_for(lambda:len(queue.waiters)==index+1,2))
                self.assertFalse(queue.acquire(timeout=0))
                self.assertEqual(order,[])
            finally:queue.release()
            for result in futures:result.result(3)
        self.assertEqual(order,list(range(16)))
        self.assertFalse(queue.active);self.assertFalse(queue.waiters)

    def test_timeout_frees_capacity_and_does_not_block_next_request(self):
        queue=EmbeddingQueue(capacity=1)
        self.assertTrue(queue.acquire())
        with ThreadPoolExecutor(max_workers=1) as pool:
            result=pool.submit(queue.acquire,.02)
            self.assertFalse(result.result(1))
        self.assertFalse(queue.waiters)
        queue.release()
        self.assertTrue(queue.acquire(timeout=0));queue.release()


if __name__=='__main__':unittest.main()
