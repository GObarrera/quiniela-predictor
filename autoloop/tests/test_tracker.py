"""Pruebas unitarias de tracker.py y redact.py (solo biblioteca estándar)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tracker  # noqa: E402
from redact import redactar  # noqa: E402

CABECERA = "| ID | Prioridad | Obligatorio | Estado | Depende de | Prueba | Descripción |\n|---|---|---|---|---|---|---|\n"


def escribir(tmp: Path, filas: str) -> Path:
    p = tmp / "REQUIREMENTS.md"
    p.write_text("# Requisitos\n\nTexto libre | con barra\n\n" + CABECERA + filas, encoding="utf-8")
    return p


class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def analizar(self, filas, intentos=None):
        return tracker.analizar(tracker.leer_requisitos(escribir(self.tmp, filas)), intentos or {}, 3)

    def test_prioridad_y_obligatorio_primero(self):
        r = self.analizar("| X | P0 | No | pendiente | - | - | opcional urgente |\n"
                          "| A | P2 | Sí | pendiente | - | - | a |\n"
                          "| B | P1 | Sí | pendiente | - | - | b |\n")
        self.assertEqual(r["codigo"], tracker.EXIT_TRABAJO)
        self.assertEqual(r["siguiente"]["id"], "B")
        self.assertEqual(r["ejecutables"], ["B", "A", "X"])

    def test_dependencias(self):
        r = self.analizar("| A | P1 | Sí | pendiente | - | - | a |\n| B | P0 | Sí | pendiente | A | - | b |\n")
        self.assertEqual(r["siguiente"]["id"], "A")
        self.assertIn({"id": "B", "motivo": "depende de A", "obligatorio": True}, r["no_ejecutables"])

    def test_probado_sin_prueba_no_cuenta(self):
        r = self.analizar("| A | P0 | Sí | probado | - | - | a |\n")
        self.assertFalse(r["completo"])
        self.assertEqual(r["siguiente"]["id"], "A")

    def test_completo_aunque_queden_opcionales(self):
        r = self.analizar("| A | P0 | Sí | probado | - | `pytest` | a |\n| C | P3 | No | pendiente | - | - | c |\n")
        self.assertTrue(r["completo"])
        self.assertEqual(r["codigo"], tracker.EXIT_COMPLETO)

    def test_bloqueado_e_intentos(self):
        r = self.analizar("| A | P0 | Sí | bloqueado | - | - | a |\n| B | P0 | Sí | pendiente | - | - | b |\n", {"B": 3})
        self.assertEqual(r["codigo"], tracker.EXIT_BLOQUEADO)
        self.assertIsNone(r["siguiente"])
        self.assertEqual({b["id"] for b in r["no_ejecutables"]}, {"A", "B"})

    def test_en_progreso_antes_que_pendiente_misma_prioridad(self):
        r = self.analizar("| A | P1 | Sí | pendiente | - | - | a |\n| B | P1 | Sí | en_progreso | - | - | b |\n")
        self.assertEqual(r["siguiente"]["id"], "B")

    def test_formato_invalido(self):
        for filas in ("| A | P9 | Sí | pendiente | - | - | a |\n", "| A | P0 | Sí | hecho | - | - | a |\n",
                      "| A | P0 | Sí | pendiente | - | - | a |\n| A | P0 | Sí | pendiente | - | - | dup |\n", ""):
            with self.assertRaises(tracker.FormatoInvalido):
                tracker.leer_requisitos(escribir(self.tmp, filas))

    def test_cli_codigos_y_intentos(self):
        escribir(self.tmp, "| A | P0 | Sí | pendiente | - | - | a |\n")
        args = ["--root", str(self.tmp)]
        self.assertEqual(tracker.main(["next"] + args), 10)
        for _ in range(3):
            tracker.main(["attempt", "--tarea", "A"] + args)
        self.assertEqual(json.loads((self.tmp / "autoloop/state/attempts.json").read_text())["A"], 3)
        self.assertEqual(tracker.main(["next"] + args), 20)
        tracker.main(["attempt", "--tarea", "A", "--reset"] + args)
        self.assertEqual(tracker.main(["next"] + args), 10)
        (self.tmp / "REQUIREMENTS.md").unlink()
        self.assertEqual(tracker.main(["check"] + args), 2)

    def test_render_idempotente(self):
        escribir(self.tmp, "| A | P0 | Sí | probado | - | `pytest` | a |\n")
        (self.tmp / "PROJECT_STATUS.md").write_text("# Estado\n\nNotas humanas.\n", encoding="utf-8")
        tracker.main(["render", "--root", str(self.tmp)])
        primero = (self.tmp / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        tracker.main(["render", "--root", str(self.tmp)])
        segundo = (self.tmp / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        self.assertEqual(primero, segundo)
        self.assertIn("Notas humanas.", segundo)
        self.assertEqual(segundo.count(tracker.MARCA_INICIO), 1)

    def test_iteraciones_con_linea_truncada(self):
        d = self.tmp / "h.jsonl"
        d.write_text('{"iteracion": 1}\n{"iteracion": 2, "tar', encoding="utf-8")
        self.assertEqual(len(tracker.leer_iteraciones(d)), 1)


class RedactTest(unittest.TestCase):
    def test_oculta_secretos_y_datos_personales(self):
        txt = ("ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnop token: ghp_abcdefghijklmnopqrstuvwxyz1234 "
               "Authorization: Bearer abc.def.ghijklmnopqr mail ana@example.com tel +54 9 11 5555-1234 "
               'password="hunter22"')
        out = redactar(txt)
        for s in ("sk-ant-", "ghp_", "abc.def", "ana@example.com", "5555-1234", "hunter22"):
            self.assertNotIn(s, out)

    def test_no_toca_fechas_ni_numeros(self):
        txt = "2026-10-22T10:00:00Z costo 0.0360331 sorteo 4565 12893 tarea QP-01"
        self.assertEqual(redactar(txt), txt)


if __name__ == "__main__":
    unittest.main()
