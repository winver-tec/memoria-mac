#!/bin/zsh
# Pré-script da rotina "Memória em risco": sai 0 (dispara o ping) só se o
# alerta.json diz risco e o último ping tem mais de 10 min. Imprime o resumo.
D=${0:A:h}; A=$D/alerta.json; U=$D/.ultimo_ping
[[ -f $A ]] || exit 1
python3 - "$A" "$U" <<'PY'
import json,sys,time,os
a=json.load(open(sys.argv[1])); u=sys.argv[2]
if not a.get('risco'): sys.exit(1)
if os.path.exists(u) and time.time()-os.path.getmtime(u) < 600: sys.exit(1)
open(u,'w').write(str(time.time()))
g=', '.join(f"{x['nome']} {x['mb']/1024:.1f} GB" for x in a['grupos'])
print(f"desde {a['desde']} — {', '.join(a['motivo'])} (RAM {a['usada_pct']}%, swap {a['swap_gb']} GB, disco livre {a['disco_livre_gb']} GB, pressão {a['nivel']}, {a['agentes']} agentes). Maiores: {g}.")
PY
