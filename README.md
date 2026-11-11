# Memória do Mac — medidor para o Maestri

Painel local que mostra, ao vivo, o que está acontecendo com o seu Mac enquanto os
agentes trabalham: memória usada, swap, pressão de memória do macOS, temperatura do
chip, rotação dos coolers e quem está comendo a memória (Chrome, Docker, agentes
Claude, Electron, editores, servidores Node...). Quando a máquina chega no limite,
toca um alarme e pode avisar o seu Maestro pelo Maestri.

Só lê o sistema (`vm_stat`, `sysctl`, `ps`, sensores via IOKit). Não precisa de `sudo`,
não instala nada fora da sua pasta de usuário e não manda dado para lugar nenhum.

| Tela | Endereço | Para quê |
|---|---|---|
| Painel completo | `http://127.0.0.1:4747/` | aba do navegador, com o manual no fim |
| Faixa "placa de vídeo" | `http://127.0.0.1:4747/mini` | portal do Maestri, 980×289 |

> Este repositório é **somente para baixar**. Quem edita é a Winver. Achou um
> problema ou tem uma ideia? Abra uma *issue*.

## Requisitos

- macOS (Apple Silicon ou Intel). Testado no macOS 26 com M3 Pro.
- Xcode Command Line Tools (dá o `clang` e o `python3` do sistema): `xcode-select --install`
- [Maestri](https://maestri.app) só para a faixa no canvas e o aviso ao Maestro. O painel funciona sem ele.

## Instalar

```bash
git clone https://github.com/winver-tec/memoria-mac.git
cd memoria-mac
./instalar.sh
```

O instalador copia os arquivos para `~/.winver/memoria`, compila os dois sensores
(temperatura e coolers), cria o LaunchAgent `com.winver.memoria` e liga o servidor na
porta 4747. Ele sobe sozinho no boot e se reergue se cair. Outra porta:
`PORTA=5000 ./instalar.sh`.

Para atualizar, dê `git pull` e rode `./instalar.sh` de novo.

## Colocar no Maestri

**1. A faixa no canvas** (fica ao lado dos seus terminais, sempre visível):

```bash
maestri portal create http://127.0.0.1:4747/mini "Memória" --size 980x289
```

**2. O aviso ao Maestro** (opcional). Uma rotina do Maestri roda a cada minuto um
pré-script que só dispara quando o alarme está ativo, no máximo um aviso a cada 10
minutos. O texto do aviso traz o motivo e os maiores consumidores. Rode no terminal
do seu Maestro (precisa do modo Maestro ligado nele):

```bash
maestri routine create "Memória em risco" \
  --every 1m --no-notify \
  --pre-run "$HOME/.winver/memoria/ping_maestro.sh" \
  --command "🔥 MEMÓRIA DO MAC EM RISCO {{output}} Veja quem está parado e o que pode fechar ou pausar (nunca os apps do usuário) e avise o usuário do que fez."
```

Para a rotina mirar outro terminal, acrescente `--terminal "Nome"`.

**3. Nome legível** (opcional). Se você usa um proxy local de nomes, como o
[portless](https://github.com/nicolo-ribaudo/portless), aponte `memoria.localhost`
para a porta 4747 e abra `https://memoria.localhost`.

## Como o alarme decide

Pico pode. O alarme só dispara quando a máquina **fica** no limite:

- Limite = pressão de memória do macOS **crítica**, ou em **alerta** com menos de 20 %
  de memória livre, ou chip **quente/crítico** (estado térmico do macOS), ou swap
  **≥ 50 GB**, ou disco livre **< 15 GB** (aí o swap não tem para onde crescer).
- Precisa ficar no limite **5 minutos seguidos** (pressão crítica: 1 minuto).
- Enquanto durar: som *Sosumi* na hora e a cada 2 minutos, faixa vermelha pulsando,
  e o aviso ao Maestro (se a rotina existir).
- Desarma na hora em que sai do limite.

RAM e swap altos, sozinhos, **não** contam: o macOS não tem teto de swap e cria arquivos
de 1 GB em `/System/Volumes/VM` conforme precisa. Os tetos ficam no começo de
`servidor.py` (`TETO_SWAP_GB`, `ESCALA_SWAP_GB`) e na função `limite()`; ajuste ao seu disco.

## Desligar, religar, remover

```bash
launchctl bootout gui/$(id -u)/com.winver.memoria                                   # desliga
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.winver.memoria.plist   # religa
./desinstalar.sh                                                                     # remove tudo
```

O portal e a rotina criados no Maestri você apaga por lá
(`maestri portal close "Memória"` e `maestri routine delete "Memória em risco"`).

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `servidor.py` | servidor HTTP (porta 4747): lê o sistema, serve as telas e `/dados` (JSON), cuida do alarme |
| `index.html` | painel completo, com o manual no fim |
| `mini.html` | faixa estilo placa de vídeo, com os coolers girando na rotação real |
| `temperatura.m` | sensor de temperatura do chip, SSD e bateria (IOKit HID, sem sudo) |
| `cooler.c` | rotação dos coolers (AppleSMC, sem sudo) |
| `ping_maestro.sh` | pré-script da rotina do Maestri: dispara só com alarme ativo, 1 vez a cada 10 min |
| `com.winver.memoria.plist.modelo` | modelo do LaunchAgent (o instalador preenche a pasta e a porta) |
| `instalar.sh` / `desinstalar.sh` | instala e remove |

Licença MIT. Feito pela [Winver](https://www.winver.com.br).
