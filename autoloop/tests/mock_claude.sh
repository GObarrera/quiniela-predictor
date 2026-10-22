#!/usr/bin/env bash
# Doble de prueba de `claude -p`: no usa red, no gasta, no envía nada.
# Comportamiento por tarea con MOCK_BEHAVIOR_<ID> (guiones -> _) o global con MOCK_BEHAVIOR:
#   success | partial | fail | noop | blocked | breaktests | faketest | ratelimit | crash | slow
set -u
task="${AUTOLOOP_TASK_ID:?falta AUTOLOOP_TASK_ID}"
var="MOCK_BEHAVIOR_$(printf '%s' "$task" | tr -c 'A-Za-z0-9' '_')"
behavior="${!var:-${MOCK_BEHAVIOR:-success}}"
PY="${PYTHON:-python3}"
echo "$task $behavior" >> autoloop/state/mock_calls.log
printf '%s\n' "${@:3}" > autoloop/state/mock_args.log   # argumentos (sin el prompt) para verificarlos

result() { printf '{"tarea":"%s","estado":"%s","archivos":[],"pruebas":["mock"],"errores":[%s],"siguiente":"-"}\n' "$task" "$1" "${2:-}" > autoloop/state/last_result.json; }
set_row() {  # set_row <estado> <prueba>
  "$PY" - "$task" "$1" "$2" <<'PYEOF'
import re, sys
t, estado, prueba = sys.argv[1:4]
p = "REQUIREMENTS.md"
out = []
for l in open(p, encoding="utf-8").read().splitlines():
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    if l.lstrip().startswith("|") and c and c[0] == t:
        c[3], c[5] = estado, prueba
        l = "| " + " | ".join(c) + " |"
    out.append(l)
open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
PYEOF
}
ok_json() { printf '{"type":"result","subtype":"success","is_error":false,"result":"mock: %s","total_cost_usd":0.01}\n' "$1"; }
mk_test() {  # mk_test <pasa:1|0>
  mkdir -p tests; : > tests/__init__.py
  local id; id="$(printf '%s' "$task" | tr -c 'A-Za-z0-9' '_' | tr 'A-Z' 'a-z')"
  if [ "$1" = 1 ]; then body="self.assertTrue(True)"; else body="self.fail('mock')"; fi
  printf 'import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        %s\n' "$body" > "tests/test_$id.py"
}

case "$behavior" in
  success)    mk_test 1; set_row probado '`python3 -m unittest discover -s tests -q`'; result done; ok_json "$task listo" ;;
  partial)    echo "wip" > "wip_$task.txt"; set_row en_progreso -; result partial; ok_json "$task parcial" ;;
  fail)       echo "intento" > "intento_$task.txt"; result failed '"no compila (mock)"'; ok_json "$task falló" ;;
  noop)       result done; ok_json "$task sin cambios" ;;
  blocked)    set_row bloqueado -; printf '\n### B-MOCK-%s\n- Falta credencial (mock)\n' "$task" >> BLOCKERS.md; result blocked; ok_json "$task bloqueado" ;;
  breaktests) mk_test 1; touch BROKEN; set_row probado '`python3 -m unittest discover -s tests -q`'; result done; ok_json "$task" ;;
  faketest)   mk_test 0; set_row probado '`python3 -m unittest discover -s tests -q`'; result done; ok_json "$task" ;;
  secret)     mk_test 1; set_row probado '`python3 -m unittest discover -s tests -q`'; result done '"API_KEY=sk-ant-abcdefghijklmnop contacto juan.perez@example.com +54 9 11 5555-1234"'
              printf '{"type":"result","is_error":false,"result":"token ghp_abcdefghijklmnopqrstuvwxyz123456","total_cost_usd":0.01}\n' ;;
  ratelimit)  printf '{"type":"result","subtype":"error","is_error":true,"result":"Claude AI usage limit reached|1760000000","total_cost_usd":0}\n'; exit 1 ;;
  crash)      echo "Segmentation fault (mock)" >&2; exit 2 ;;
  slow)       sleep "${MOCK_SLEEP:-5}"; mk_test 1; set_row probado '`python3 -m unittest discover -s tests -q`'; result done; ok_json "$task lento" ;;
  *)          echo "comportamiento desconocido: $behavior" >&2; exit 2 ;;
esac
