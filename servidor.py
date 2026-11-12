#!/usr/bin/env python3
"""Acelerador da memória do Mac (CEO 09/11): serve index.html e /dados (JSON) a cada leitura.
Só lê o sistema (vm_stat, sysctl, ps). Porta 4747; nome legível via portless: memoria.localhost."""
import http.server, json, os, re, subprocess, time
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PORTA = int(os.environ.get('PORTA', '4747'))

def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout

def grupo(cmd, cwd_hint=''):
    c = cmd.lower(); base = os.path.basename(cmd)
    if base == 'claude': return 'Agentes Claude'
    if 'docker' in c or 'com.apple.virtualization' in c or 'qemu' in c: return 'Docker'
    if 'simulator' in c or 'coresimulator' in c or 'springboard' in c: return 'Simulador iOS'
    if 'google chrome' in c or 'chrome helper' in c: return 'Chrome'
    if 'safari' in c or 'webkit' in c: return 'Safari/WebKit'
    if 'maestri' in c: return 'Maestri'
    if 'electron' in c or 'tsa cowork' in c or 'marvee' in c: return 'Apps Electron'
    if 'cursor' in c or 'code helper' in c or 'visual studio code' in c: return 'Editor'
    if base in ('node', 'bun', 'deno'): return 'Node/Bun (servidores)'
    if 'postgres' in c: return 'Postgres'
    if 'python' in c: return 'Python'
    if 'kernel_task' in c or 'windowserver' in c: return 'Sistema'
    return 'Outros'

TETO_SWAP_GB = 50    # CEO 09/11: teto combinado de swap = 50 GB (metade do disco livre)
ESCALA_SWAP_GB = 60  # mostrador vai até 60 para o teto de 50 aparecer como marca
def _livre():
    v = os.statvfs('/System/Volumes/VM'); return v.f_bavail * v.f_frsize

ESTADO_TERMICO = {0: 'normal', 1: 'morno', 2: 'quente', 3: 'crítico'}
def temperatura():
    try:
        t = json.loads(sh(os.path.join(AQUI, 'temperatura')))
        t['estado_txt'] = ESTADO_TERMICO.get(t.get('estado'), '?')
        # Escala do mostrador: 30 °C = 0%, 105 °C = 100%.
        t['pct'] = max(0, min(100, (t['chip'] - 30) * 100 / 75))
        return t
    except Exception:
        return None

def bateria():
    """pmset -g batt: carga, fonte e tempo. Bateria baixa SEM tomada = o macOS entra em
    economia de energia e o Mac fica lento (CEO 11/11: "com a bateria baixa o mac começou a chorar")."""
    try:
        out = sh('pmset', '-g', 'batt')
        pct = int(re.search(r'(\d+)%', out).group(1))
        tomada = 'AC Power' in out
        carregando = 'charging' in out and 'discharging' not in out and 'not charging' not in out
        m = re.search(r'(\d+:\d+) remaining', out)
        restante = m.group(1) if m else None
        if tomada: estado = 'carregando' if carregando and pct < 100 else 'na tomada'
        elif pct <= 10: estado = 'crítica'
        elif pct <= 20: estado = 'baixa'
        else: estado = 'na bateria'
        return {'pct': pct, 'tomada': tomada, 'carregando': carregando, 'restante': restante, 'estado': estado}
    except Exception:
        return None

def cooler():
    try: return json.loads(sh(os.path.join(AQUI, 'cooler'))).get('fans', [])
    except Exception: return []

def dados():
    vm = sh('vm_stat')
    ps_ = int(re.search(r'page size of (\d+)', vm).group(1))
    def p(n):
        m = re.search(n + r':\s+(\d+)', vm); return int(m.group(1)) * ps_ if m else 0
    total = int(sh('sysctl', '-n', 'hw.memsize'))
    wired, ativa, comp = p('Pages wired down'), p('Pages active'), p('Pages occupied by compressor')
    usada = min(total, wired + ativa + comp)
    sw = sh('sysctl', '-n', 'vm.swapusage')
    num = lambda k: float(re.search(k + r' = ([\d.]+)M', sw).group(1)) * 1024 * 1024
    sw_total, sw_usado = num('total'), num('used')
    m = re.search(r'free percentage: (\d+)%', sh('memory_pressure', '-Q'))
    livre_pct = int(m.group(1)) if m else None
    nivel = int(sh('sysctl', '-n', 'kern.memorystatus_vm_pressure_level').strip() or 1)
    grupos = defaultdict(lambda: {'mb': 0, 'n': 0})
    agentes = 0
    for linha in sh('ps', '-axo', 'rss=,comm=').splitlines():
        partes = linha.strip().split(None, 1)
        if len(partes) < 2: continue
        rss, cmd = int(partes[0]) * 1024, partes[1]
        g = grupo(cmd); grupos[g]['mb'] += rss / 1048576; grupos[g]['n'] += 1
        if g == 'Agentes Claude': agentes += 1
    top = sorted(({'nome': k, 'mb': round(v['mb']), 'n': v['n']} for k, v in grupos.items()), key=lambda x: -x['mb'])[:9]
    carga = os.getloadavg()
    return {
        'em': time.strftime('%H:%M:%S'),
        'total_gb': total / 2**30, 'usada_gb': usada / 2**30, 'usada_pct': usada * 100 / total,
        'comprimida_gb': comp / 2**30,
        'swap_total_gb': sw_total / 2**30, 'swap_usado_gb': sw_usado / 2**30,
        # O macOS NÃO tem teto de swap: cria arquivos de 1 GB conforme precisa,
        # até onde o disco deixar. "total" do sysctl é só o que já foi criado.
        # Mostrador em escala de 50 GB (teto combinado com o CEO; o macOS não deixa travar).
        'swap_pct': sw_usado * 100 / (ESCALA_SWAP_GB * 2**30),
        'disco_livre_gb': round(_livre() / 2**30, 1),
        'temp': temperatura(),
        'cooler': cooler(),
        'bateria': bateria(),
        'pressao_pct': (100 - livre_pct) if livre_pct is not None else None,
        'nivel': {1: 'normal', 2: 'alerta', 4: 'crítica'}.get(nivel, 'normal'),
        'agentes': agentes, 'carga': [round(x, 1) for x in carga], 'nucleos': os.cpu_count(),
        'grupos': top,
    }


# ── Alarme (CEO 09/11): "pode deixar na aceleração máxima, mas tem que ter
# controle" + "tem que manter um determinado tempo no limite". RAM cheia NÃO
# alarma. Swap também não: o macOS cresce o swap sozinho. LIMITE = pressão do
# macOS em alerta/crítica, chip quente/crítico (thermalState do macOS), swap >= 50 GB (teto do CEO) ou disco livre < 15 GB (aí o swap não tem pra onde crescer).
# RISCO (som + ping) só se ficar no limite SEM PARAR por 5 min (crítica: 1 min).
# Saiu do limite: vermelho e som param NA HORA (CEO 09/11 "estabilizou, o sinal
# vermelho tem que sair"); o alarme só zera de vez após 30 s fora (evita re-ping). Pico rápido = só "No limite" na tela.
LIVRE_MIN_PCT = 20
BATERIA_MIN_PCT = 10
DISCO_MIN_GB, SUSTENTA, SUSTENTA_CRITICA, DESARMA, REPETE_SOM = 15, 300, 60, 30, 120
ESTADO = os.path.join(AQUI, 'alerta.json')
ALARME = {'risco': False, 'no_limite_s': 0, 'desde': None, 'motivo': []}
import threading
def motivo_do(d):
    m = []
    if d['swap_usado_gb'] >= TETO_SWAP_GB: m.append(f"swap {d['swap_usado_gb']:.0f} GB (teto 50)")
    if d.get('temp') and (d['temp']['estado'] >= 2 or d['temp']['chip'] >= 95): m.append(f"chip {d['temp']['estado_txt']} ({d['temp']['chip']:.0f} °C)")
    if d['disco_livre_gb'] < DISCO_MIN_GB: m.append(f"disco livre {d['disco_livre_gb']:.0f} GB")
    # CEO 11/11 23:1x: bateria baixa sem tomada = macOS em economia de energia, Mac lento.
    b = d.get('bateria')
    if b and not b['tomada'] and b['pct'] <= BATERIA_MIN_PCT: m.append(f"bateria {b['pct']}% sem tomada")
    # CEO 09/11 15:58 "ajusta esses sinais se dá pra esticar": "alerta" do macOS
    # sozinho NÃO é risco (com 41% livre ele ainda comprime). Alerta só conta se a
    # memória livre do memory_pressure cair abaixo de LIVRE_MIN_PCT; crítica conta sempre.
    livre = None if d.get('pressao_pct') is None else 100 - d['pressao_pct']
    if d['nivel'] == 'crítica': m.append("pressão crítica")
    elif d['nivel'] == 'alerta' and livre is not None and livre < LIVRE_MIN_PCT: m.append(f"pressão alerta com {livre}% livre")
    return m
def vigia():
    risco, inicio, fora_desde, desde, ultimo_som = False, None, None, None, 0
    while True:
        try:
            d = dados(); m = motivo_do(d); agora = time.time()
            if m:
                inicio = inicio or agora; fora_desde = None
                precisa = SUSTENTA_CRITICA if d['nivel'] == 'crítica' else SUSTENTA
                if not risco and agora - inicio >= precisa:
                    risco, desde = True, time.strftime('%H:%M:%S', time.localtime(inicio))
            else:
                inicio = None; fora_desde = fora_desde or agora
                if risco and agora - fora_desde >= DESARMA:
                    risco, desde = False, None
            if risco and m and agora - ultimo_som >= REPETE_SOM:
                subprocess.Popen(['afplay', '/System/Library/Sounds/Sosumi.aiff']); ultimo_som = agora
            if not risco: ultimo_som = 0
            ALARME.update(risco=risco, no_limite_s=int(agora - inicio) if inicio else 0, desde=desde, motivo=m)
            json.dump({'risco': risco, 'desde': desde, 'no_limite_s': ALARME['no_limite_s'], 'motivo': m or ['fora do limite'], 'em': d['em'],
                       'usada_pct': round(d['usada_pct']), 'swap_gb': round(d['swap_usado_gb'], 1), 'disco_livre_gb': d['disco_livre_gb'], 'nivel': d['nivel'],
                       'agentes': d['agentes'], 'grupos': d['grupos'][:5]}, open(ESTADO + '.tmp', 'w'), ensure_ascii=False)
            os.replace(ESTADO + '.tmp', ESTADO)
        except Exception: pass
        time.sleep(5)

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith('/dados'):
            corpo, tipo = json.dumps({**dados(), 'alarme': ALARME}).encode(), 'application/json'
        elif self.path.startswith('/logo.svg'):
            corpo, tipo = open(os.path.join(AQUI, 'logo.svg'), 'rb').read(), 'image/svg+xml'
        else:
            corpo, tipo = open(os.path.join(AQUI, 'mini.html' if self.path.startswith('/mini') else 'index.html'), 'rb').read(), 'text/html; charset=utf-8'
        self.send_response(200); self.send_header('Content-Type', tipo)
        self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(corpo)

if __name__ == '__main__':
    threading.Thread(target=vigia, daemon=True).start()
    http.server.ThreadingHTTPServer(('127.0.0.1', PORTA), H).serve_forever()
