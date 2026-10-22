import unittest

import pandas as pd

from src.terminaciones import dataframe_terminaciones


class TestDataframeTerminaciones(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "fecha": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            "numero": [1234, 9999, 100, 7],
        })

    def test_ultimos_dos_digitos(self):
        out = dataframe_terminaciones(self.df)
        self.assertEqual(out["numero"].tolist(), [34, 99, 0, 7])

    def test_rango_0_99(self):
        out = dataframe_terminaciones(self.df)
        self.assertTrue(out["numero"].between(0, 99).all())

    def test_no_modifica_el_original(self):
        original = self.df.copy()
        out = dataframe_terminaciones(self.df)
        pd.testing.assert_frame_equal(self.df, original)
        self.assertIsNot(out, self.df)

    def test_conserva_otras_columnas(self):
        out = dataframe_terminaciones(self.df)
        self.assertEqual(out["fecha"].tolist(), self.df["fecha"].tolist())


if __name__ == "__main__":
    unittest.main()
