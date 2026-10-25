"""GPU selection must not confuse estimated free memory with compatibility."""
import unittest
from max_native import GPUCompatibilityError, select_gpu, gpu_id


class MaxDeviceSelectionTests(unittest.TestCase):
    def hybrid(self):
        integrated={'name':'Vulkan0','description':'AMD Radeon Graphics','kind':'integrated','pci_id':'0000:00:01.0','free_bytes':48*1024**3,'total_bytes':64*1024**3}
        dedicated={'name':'Vulkan1','description':'AMD Radeon RX 7800 XT','kind':'dedicated','pci_id':'0000:03:00.0','free_bytes':2*1024**3,'total_bytes':16*1024**3}
        for item in (integrated,dedicated):item['id']=gpu_id(item)
        return integrated,dedicated

    def test_dedicated_7800xt_beats_integrated_gpu_with_more_shared_memory(self):
        integrated,dedicated=self.hybrid()
        for devices in ([integrated,dedicated],[dedicated,integrated]):self.assertEqual(select_gpu(devices),dedicated)

    def test_manual_choice_survives_backend_reordering_and_never_silently_falls_back(self):
        integrated,dedicated=self.hybrid();chosen=dedicated['id']
        dedicated={**dedicated,'name':'Vulkan0'};integrated={**integrated,'name':'Vulkan1'}
        self.assertEqual(gpu_id(dedicated),chosen)
        self.assertEqual(select_gpu([integrated,dedicated],chosen),dedicated)
        self.assertEqual(select_gpu([integrated,dedicated],integrated['id']),integrated)
        with self.assertRaisesRegex(GPUCompatibilityError,'Aucune autre carte'):select_gpu([integrated],chosen)

    def test_ambiguous_manual_identity_is_rejected(self):
        _,card=self.hybrid()
        with self.assertRaises(GPUCompatibilityError):select_gpu([card,{**card,'name':'Vulkan2'}],card['id'])

    def test_7800xt_16gb_is_accepted_even_with_an_unreliable_free_memory_estimate(self):
        for free in (0,2*1024**3,16*1024**3):
            card={'name':'Vulkan0','description':'AMD Radeon RX 7800 XT','free_bytes':free,'total_bytes':16*1024**3}
            self.assertEqual(select_gpu([card]),card)

    def test_nvidia_is_not_excluded_by_the_old_four_gb_cutoff(self):
        card={'name':'Vulkan0','description':'NVIDIA GeForce RTX fixture','free_bytes':1024**3,'total_bytes':8*1024**3}
        self.assertEqual(select_gpu([card]),card)

    def test_unavailable_vulkan_is_a_compatibility_error_not_a_speed_verdict(self):
        for devices in ([],[{'name':'CPU','description':'AMD Ryzen'}],[{'name':'Vulkan0','description':'Intel Arc'}]):
            with self.assertRaises(GPUCompatibilityError) as error:select_gpu(devices)
            self.assertEqual(error.exception.code,'gpu_unavailable')
            self.assertIn('Vulkan',str(error.exception))
            self.assertNotIn('insuffisant',str(error.exception))


if __name__=='__main__':unittest.main()
