import unittest
from full_pack_accumulate_charge import FullPack,run_full_pack
class FullPackTests(unittest.TestCase):
 def test_energy_closes(self):
  r=run_full_pack(FullPack(crystals=64,contact_fraction=.5,piezo_fraction=.1,resonance_capture_gain=5))
  self.assertAlmostEqual(r['energy']['closure_j'],0,places=5)
 def test_no_resonance_energy_multiplication(self):
  r=run_full_pack(FullPack(resonance_capture_gain=100))
  self.assertLessEqual(r['power']['harvested_w'],r['power']['acoustic_w'])
 def test_full_pack_is_reached_by_strong_case(self):
  r=run_full_pack(FullPack(crystals=64,contact_fraction=.5,piezo_fraction=.1,resonance_capture_gain=5))
  self.assertTrue(r['completed']); self.assertGreaterEqual(r['energy']['pack_wh'],216)
if __name__=='__main__': unittest.main()
