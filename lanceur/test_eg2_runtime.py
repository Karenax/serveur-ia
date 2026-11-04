"""Explicit P2200 binding, memory policy and CPU retry without real GPU use."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from eg2_runtime import configuration,ModelRuntime


class CudaOOM(RuntimeError):pass


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.model=Mock();self.model.encode.return_value=[[1.0]+[0.0]*767]
        self.cuda=SimpleNamespace(is_available=Mock(return_value=True),
            get_device_properties=Mock(return_value=SimpleNamespace(total_memory=5*2**30)),
            set_per_process_memory_fraction=Mock(),get_device_name=Mock(return_value='Quadro P2200'),
            empty_cache=Mock(),OutOfMemoryError=CudaOOM)
        self.torch=SimpleNamespace(cuda=self.cuda)

    def gpu(self):return ModelRuntime(self.model,self.torch,'cuda','GPU-test',2200,1024,True)

    def test_gpu_selected_and_actual_device_reported(self):
        with patch('eg2_runtime.gpu_free_mib',return_value=3853):runtime=self.gpu()
        self.model.to.assert_called_once_with('cuda:0')
        self.assertEqual(runtime.status()['gpu_name'],'Quadro P2200')
        self.assertEqual(runtime.status()['device'],'cuda:0')
        self.cuda.set_per_process_memory_fraction.assert_called_once()

    def test_low_startup_memory_uses_cpu_without_attempting_gpu_load(self):
        with patch('eg2_runtime.gpu_free_mib',return_value=1800):runtime=self.gpu()
        self.model.to.assert_called_once_with('cpu')
        self.assertEqual(runtime.status()['device'],'cpu');self.assertTrue(runtime.status()['fallback_reason'])

    def test_unavailable_cuda_falls_back_and_does_not_query_other_cards(self):
        self.cuda.is_available.return_value=False
        with patch('eg2_runtime.gpu_free_mib') as query:runtime=self.gpu()
        query.assert_not_called();self.assertEqual(runtime.device,'cpu')

    def test_memory_pressure_before_inference_moves_to_cpu(self):
        with patch('eg2_runtime.gpu_free_mib',side_effect=[3853,500]) as query:
            runtime=self.gpu();result=runtime.encode(['test'])
        self.assertEqual(runtime.device,'cpu');self.assertEqual(len(result[0]),768)
        self.assertTrue(all(call.args==('GPU-test',) for call in query.call_args_list))

    def test_oom_retries_once_on_cpu_and_reports_recovery(self):
        self.model.encode.side_effect=[CudaOOM('full'),[[1.0]+[0.0]*767]]
        with patch('eg2_runtime.gpu_free_mib',return_value=3853):
            runtime=self.gpu();result=runtime.encode(['test'])
        self.assertEqual(self.model.encode.call_count,2);self.assertEqual(runtime.device,'cpu')
        self.assertEqual(len(result[0]),768);self.assertIn('repris',runtime.fallback_reason)

    def test_configuration_requires_uuid_and_scoped_python(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'runtime.json'
            base={'device':'cuda','batch_size':4,'cpu_fallback':True,'gpu_uuid':'GPU-12345678-1234-1234-1234-123456789abc',
                'python':'../outside/python.exe','memory_limit_mib':2200,'minimum_free_mib':1024}
            path.write_text(json.dumps(base),encoding='utf-8')
            with self.assertRaises(ValueError):configuration(path)
            base['python']='toolchain/eg2-cuda-python/Scripts/python.exe';base['gpu_uuid']='cuda:0'
            path.write_text(json.dumps(base),encoding='utf-8')
            with self.assertRaises(ValueError):configuration(path)


if __name__=='__main__':unittest.main()
