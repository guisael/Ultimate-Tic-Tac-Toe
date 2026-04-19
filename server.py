import socket
import json
import threading
import urllib.request
import random

# ── Configuração Gemini ───────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyAfSr9k5Dr0xMoPlyHYUkCIrOXLaV8hc3A"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)

clients = {}
ready = {}
game = None
lock = threading.Lock()
GEMINI_CONN = "GEMINI_AI"


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


# ── JOGO ──────────────────────────────────────────────────────────────────────
class UltimateGame:
    def __init__(self):
        self.jogador = "X"
        self.proximo_tabuleiro = None
        self.vencedor_final = None
        self.mini = [
            [[["" for _ in range(3)] for _ in range(3)] for _ in range(3)]
            for _ in range(3)
        ]
        self.principal = [["" for _ in range(3)] for _ in range(3)]

    def verificar_vencedor(self, tab):
        for i in range(3):
            if tab[i][0] == tab[i][1] == tab[i][2] and tab[i][0] in ("X", "O"):
                return tab[i][0]
            if tab[0][i] == tab[1][i] == tab[2][i] and tab[0][i] in ("X", "O"):
                return tab[0][i]
        if tab[0][0] == tab[1][1] == tab[2][2] and tab[0][0] in ("X", "O"):
            return tab[0][0]
        if tab[0][2] == tab[1][1] == tab[2][0] and tab[0][2] in ("X", "O"):
            return tab[0][2]
        return None

    def tabuleiro_cheio(self, tab):
        return all(cel != "" for linha in tab for cel in linha)

    def jogadas_validas(self):
        moves = []
        tabuleiros = (
            [tuple(self.proximo_tabuleiro)]
            if self.proximo_tabuleiro
            else [(r, c) for r in range(3) for c in range(3) if self.principal[r][c] == ""]
        )
        for (tb_l, tb_c) in tabuleiros:
            if self.principal[tb_l][tb_c] != "":
                continue
            for l in range(3):
                for c in range(3):
                    if self.mini[tb_l][tb_c][l][c] == "":
                        moves.append((tb_l, tb_c, l, c))
        return moves


# ── PROTOCOLO ─────────────────────────────────────────────────────────────────
def send_json(conn, data):
    conn.sendall((json.dumps(data) + "\n").encode())


def recv_json(conn, buffer):
    while b"\n" not in buffer:
        data = conn.recv(1024)
        if not data:
            return None, buffer
        buffer += data
    line, buffer = buffer.split(b"\n", 1)
    return json.loads(line.decode()), buffer


# ── BROADCAST ─────────────────────────────────────────────────────────────────
def broadcast_state():
    state = {
        "type": "state",
        "mini": game.mini,
        "principal": game.principal,
        "jogador": game.jogador,
        "proximo_tabuleiro": game.proximo_tabuleiro,
        "vencedor": game.vencedor_final,
    }
    for conn in list(clients):
        if conn == GEMINI_CONN:
            continue
        send_json(conn, state)


# ── GEMINI AI ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é um jogador competente de Ultimate Tic-Tac-Toe jogando como O (adversário = X).

REGRAS:
- Tabuleiro: grade 3x3 de mini-tabuleiros, indexados (tb_l, tb_c) com valores 0-2.
- Cada mini-tabuleiro tem células (l, c), valores 0-2.
- Jogar na célula (l, c) envia o adversário para o mini-tabuleiro (l, c).
- Se o destino já foi conquistado ou está cheio, o adversário joga em qualquer mini livre.
- Vence quem conquistar 3 mini-tabuleiros em linha no tabuleiro principal.

COMO DECIDIR SUA JOGADA — analise nesta ordem:
1. VITÓRIA IMEDIATA: existe alguma célula vazia que completa 3-em-linha para O em algum mini? Jogue lá.
2. BLOQUEIO: X tem 2 peças em linha num mini sem bloqueio? Bloqueie a terceira célula.
3. ESTRATÉGIA MACRO: prefira conquistar mini-tabuleiros que formam linha no principal. Centro (1,1) vale mais, depois cantos.
4. CONTROLE DE DESTINO: onde (l,c) enviará X? Evite enviar X para um mini onde ele já tem vantagem (2 em linha).
5. POSIÇÃO NO MINI: prefira centro (1,1) > cantos > laterais dentro do mini-tabuleiro.

Raciocine brevemente, depois escreva APENAS o JSON final:
{"tb_l": <int>, "tb_c": <int>, "l": <int>, "c": <int>}"""


def _estado_para_prompt():
    lines = []

    if game.proximo_tabuleiro:
        tb_l, tb_c = game.proximo_tabuleiro
        lines.append(f"TURNO: você deve jogar no mini-tabuleiro ({tb_l},{tb_c}).")
    else:
        livres = [(r, c) for r in range(3) for c in range(3) if game.principal[r][c] == ""]
        coords = ", ".join(f"({r},{c})" for r, c in livres)
        lines.append(f"TURNO: escolha um destes mini-tabuleiros livres: {coords}")

    lines.append("\nTABULEIRO PRINCIPAL (. = livre, X/O = conquistado, V = empate):")
    for r in range(3):
        linha = [game.principal[r][c] or "." for c in range(3)]
        lines.append(f"  [{r}]  {' | '.join(linha)}")

    lines.append("\nCONTEÚDO DOS MINI-TABULEIROS LIVRES:")
    for tb_l in range(3):
        for tb_c in range(3):
            if game.principal[tb_l][tb_c] != "":
                continue
            lines.append(f"\n  Mini ({tb_l},{tb_c}) — se jogar aqui, X vai para o mini (l,c) que você escolher:")
            for l in range(3):
                row = [game.mini[tb_l][tb_c][l][c] or "." for c in range(3)]
                lines.append(f"    linha {l}:  {' '.join(row)}   (células c=0,1,2)")

    lines.append("\nEscolha sua jogada analisando as prioridades acima.")
    return "\n".join(lines)


def gemini_move(valid):
    user_text = _estado_para_prompt()

    payload = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 512},
    }).encode()

    req = urllib.request.Request(
        GEMINI_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode())

        text = body["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[Gemini RAW]\n{text}\n{'─'*40}")

        # Extrai o último {...} da resposta (após o raciocínio)
        start = text.rfind("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("JSON não encontrado")

        move = json.loads(text[start:end])
        result = (int(move["tb_l"]), int(move["tb_c"]), int(move["l"]), int(move["c"]))

        if result in valid:
            print(f"[Gemini] Jogada: {result}")
            return result

        print(f"[Gemini] Jogada inválida {result}, usando fallback aleatório.")
        return random.choice(valid)

    except Exception as e:
        print(f"[Gemini] Erro: {e}. Fallback aleatório.")
        return random.choice(valid)


# ── APPLY MOVE ────────────────────────────────────────────────────────────────
def apply_move(player, tb_l, tb_c, l, c):
    if game.vencedor_final:
        return False
    if game.proximo_tabuleiro and (tb_l, tb_c) != tuple(game.proximo_tabuleiro):
        return False
    if game.principal[tb_l][tb_c] != "":
        return False
    if game.mini[tb_l][tb_c][l][c] != "":
        return False

    game.mini[tb_l][tb_c][l][c] = player

    vencedor_mini = game.verificar_vencedor(game.mini[tb_l][tb_c])
    if vencedor_mini:
        game.principal[tb_l][tb_c] = vencedor_mini
        game.mini[tb_l][tb_c] = [[vencedor_mini] * 3 for _ in range(3)]
    elif game.tabuleiro_cheio(game.mini[tb_l][tb_c]):
        game.principal[tb_l][tb_c] = "V"
        game.mini[tb_l][tb_c] = [["V"] * 3 for _ in range(3)]

    vencedor_final = game.verificar_vencedor(game.principal)
    if vencedor_final:
        game.vencedor_final = vencedor_final
    elif game.tabuleiro_cheio(game.principal):
        game.vencedor_final = "V"

    game.proximo_tabuleiro = [l, c] if game.principal[l][c] == "" else None
    game.jogador = "O" if game.jogador == "X" else "X"
    return True


# ── GEMINI TURN ───────────────────────────────────────────────────────────────
def gemini_turn():
    def _play():
        # Captura jogadas válidas antes de soltar o lock
        with lock:
            if game.jogador != "O" or game.vencedor_final:
                return
            valid = game.jogadas_validas()
            if not valid:
                return

        # Chama API fora do lock para não travar o servidor
        result = gemini_move(valid)

        with lock:
            if game.jogador != "O" or game.vencedor_final:
                return
            valid_now = game.jogadas_validas()
            if result not in valid_now:
                result_final = random.choice(valid_now)
            else:
                result_final = result
            apply_move("O", *result_final)
            broadcast_state()

    threading.Thread(target=_play, daemon=True).start()


# ── CLIENT HANDLER ────────────────────────────────────────────────────────────
def handle_client(conn, addr):
    global game
    buffer = b""

    with lock:
        player = "X"
        clients[conn] = player
        ready[conn] = False
        if game is None:
            game = UltimateGame()
        if GEMINI_CONN not in clients:
            clients[GEMINI_CONN] = "O"
            ready[GEMINI_CONN] = False

    send_json(conn, {"type": "assign", "player": player})
    broadcast_state()

    try:
        while True:
            msg, buffer = recv_json(conn, buffer)
            if msg is None:
                break

            if msg["type"] == "ready":
                if not game.vencedor_final:
                    continue
                with lock:
                    ready[conn] = True
                    ready[GEMINI_CONN] = True
                    if all(ready[k] for k in clients if k != GEMINI_CONN):
                        game = UltimateGame()
                        for c in clients:
                            if c == GEMINI_CONN:
                                continue
                            send_json(c, {"type": "reset"})
                        for k in ready:
                            ready[k] = False
                        broadcast_state()
                continue

            if msg["type"] != "move":
                continue
            if game.vencedor_final:
                continue
            if player != game.jogador:
                continue

            tb_l, tb_c, l, c = msg["tb_l"], msg["tb_c"], msg["l"], msg["c"]

            with lock:
                ok = apply_move(player, tb_l, tb_c, l, c)

            if ok:
                broadcast_state()
                if game.jogador == "O" and not game.vencedor_final:
                    gemini_turn()

    finally:
        with lock:
            clients.pop(conn, None)
            ready.pop(conn, None)
        conn.close()


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 3040))
    server.listen()
    print(f"Servidor rodando na porta 3040. IP: {get_local_ip()}")
    print("Player 2 (O) → Gemini 2.0 Flash  |  Player 1 (X) → Humano")
    while True:
        conn, addr = server.accept()
        print(f"[+] Cliente conectado: {addr}")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()