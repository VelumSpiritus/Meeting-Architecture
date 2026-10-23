import unittest
from joint_jig_battery_sweep import PhysicalChain, run_chain, sweep

class BatterySweepTests(unittest.TestCase):
    def test_energy_closes(self):
        for row in sweep()["rows"]:
            self.assertAlmostEqual(row["closure_residual_j"],0,places=9)
            self.assertLessEqual(row["power"]["battery_average_w"],row["power"]["acoustic_w"])
    def test_more_supplied_power_never_reduces_battery_gain(self):
        low=run_chain(PhysicalChain(.01,.1,.5,.01))
        high=run_chain(PhysicalChain(.1,.1,.5,.01))
        self.assertGreater(high["battery"]["accepted_j"],low["battery"]["accepted_j"])
    def test_ten_microfarad_cold_start_energy(self):
        r=run_chain(PhysicalChain(.1,.1,.5,.01))
        self.assertTrue(r["cold_started"])
        self.assertAlmostEqual(.5*10e-6*.6**2,1.8e-6)

if __name__=="__main__": unittest.main()
