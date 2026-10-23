import unittest

from passive_jig_circuit import JigCircuitParameters, run_jig_circuit


class PassiveJigCircuitTests(unittest.TestCase):
    def test_energy_ledger_closes(self):
        for drop in (0.0, 0.02, 0.2):
            result = run_jig_circuit(100, JigCircuitParameters(diode_drop=drop))
            self.assertLess(abs(result["energy"]["closure_residual"]), 1e-10)

    def test_alternating_pressure_still_charges_through_full_wave_paths(self):
        result = run_jig_circuit(20)
        self.assertGreater(result["reservoir"]["voltage"], 0.0)
        self.assertGreater(result["conduction_events"], 0)

    def test_diode_drop_reduces_held_energy(self):
        ideal = run_jig_circuit(100, JigCircuitParameters(diode_drop=0.0))
        lossy = run_jig_circuit(100, JigCircuitParameters(diode_drop=0.2))
        self.assertGreater(ideal["reservoir"]["energy"], lossy["reservoir"]["energy"])

    def test_no_pressure_events_means_no_charge(self):
        result = run_jig_circuit(0)
        self.assertEqual(result["reservoir"]["energy"], 0.0)
        self.assertEqual(result["energy"]["mechanical_input"], 0.0)


if __name__ == "__main__":
    unittest.main()
