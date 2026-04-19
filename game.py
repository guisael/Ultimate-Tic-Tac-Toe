import pyxel
import asyncio
import json
import threading
import socket
#CONFIGURAÇÕES
TAMANHO = 270
CELULA = TAMANHO // 9

COR_FUNDO = 0
COR_LINHA = 7
COR_DESTAQUE = 10
COR_X = 12
COR_O = 8

MENU = 0
JOGO = 1
VITORIA = 2

ESPESSURA_PRINCIPAL = 3
ESPESSURA_INTERNA = 1
COR_LINHA_INTERNA = 6  #cinza escuro
COR_DESTAQUE_JOGADOR = 10  #amarelo
COR_DESTAQUE_OUTRO = 8     #vermelho

#CLIENTE DE REDE 
class NetworkClient:
    def __init__(self, game, server_ip):
        self.game = game
        self.server_ip = server_ip
        self.conn = None
        self.buffer = b""
        threading.Thread(target=self.run, daemon=True).start()

    #ENVIO
    def send_json(self, msg):
        try:
            self.conn.sendall((json.dumps(msg) + "\n").encode())
        except:
            pass

    def send_move(self, tb_l, tb_c, l, c):
        self.send_json({
            "type": "move",
            "tb_l": tb_l,
            "tb_c": tb_c,
            "l": l,
            "c": c
        })

    def send_ready(self):
        self.send_json({"type": "ready"})

    #RECEPÇÃO 
    def recv_json(self):
        while b"\n" not in self.buffer:
            data = self.conn.recv(1024)
            if not data:
                return None
            self.buffer += data

        line, self.buffer = self.buffer.split(b"\n", 1)
        return json.loads(line.decode())

    #LOOP DE REDE
    def run(self):
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.connect((self.server_ip, 3040))

            while True:
                msg = self.recv_json()
                if msg is None:
                    break

                #ASSIGN - Define o Jogador X ou O
                if msg["type"] == "assign":
                    self.game.player = msg["player"]

                #STATE - estado completo do jogo
                elif msg["type"] == "state":
                    self.game.mini = msg["mini"]
                    self.game.principal = msg["principal"]
                    self.game.jogador = msg["jogador"]
                    self.game.proximo_tabuleiro = msg["proximo_tabuleiro"]
                    self.game.vencedor_final = msg["vencedor"]

                    if self.game.vencedor_final:
                        self.game.estado = VITORIA
                    else:
                        self.game.estado = JOGO

                #READY - jogador que quer reiniciar o jogo
                elif msg["type"] == "ready":
                    self.game.pronto_outro = True

                #RESET - reinicia a partida
                elif msg["type"] == "reset":
                    self.game.estado = MENU
                    self.game.pronto = False
                    self.game.pronto_outro = False
                    self.game.vencedor_final = None
                    self.game.jogador = None
                    self.game.proximo_tabuleiro = None

                    self.game.mini = [[[["" for _ in range(3)] for _ in range(3)]
                                       for _ in range(3)] for _ in range(3)]
                    self.game.principal = [["" for _ in range(3)] for _ in range(3)]

        except Exception as e:
            print("Erro de rede:", e)

        finally:
            if self.conn:
                self.conn.close()

#JOGO PYXEL
class UltimateJogoDaVelha:
    def __init__(self):
        pyxel.init(TAMANHO, TAMANHO, title="Ultimate Jogo da Velha Online")
        pyxel.mouse(True)

        self.estado = MENU
        self.player = None
        self.jogador = None
        self.proximo_tabuleiro = None
        self.vencedor_final = None
        self.pronto = False
        self.pronto_outro = False


        self.mini = [[[["" for _ in range(3)] for _ in range(3)]
                      for _ in range(3)] for _ in range(3)]
        self.principal = [["" for _ in range(3)] for _ in range(3)]
        server_input = input("Digite o IP do servidor: ")
        self.net = NetworkClient(self, server_ip=server_input)

        pyxel.run(self.update, self.draw)

    #UPDATE
    def update(self):
        if self.estado == MENU:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.estado = JOGO

        elif self.estado == JOGO:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if self.player != self.jogador:
                    return

                mx, my = pyxel.mouse_x, pyxel.mouse_y
                cx = mx // CELULA
                cy = my // CELULA

                tb_c = cx // 3
                tb_l = cy // 3
                c = cx % 3
                l = cy % 3

                self.net.send_move(tb_l, tb_c, l, c)
        elif self.estado == VITORIA:
                pass


    #DRAW
    def draw(self):
        pyxel.cls(COR_FUNDO)

        if self.estado == MENU:
            pyxel.text(80, 120, "AGUARDANDO CONEXAO...", 7)

        elif self.estado == JOGO:
            self.desenhar_grade()
            self.desenhar_destaque()
            self.desenhar_simbolos()

            if self.player:
                pyxel.text(5, 5, f"Voce: {self.player}", 7)
            if self.jogador:
                pyxel.text(5, 15, f"Vez: {self.jogador}", 7)

        elif self.estado == VITORIA:
            #posição do botão (referência para centralização)
            bx, by, bw, bh = 80, 120, 110, 25
            centro_x = bx + bw // 2

            def texto_centralizado(y, texto, cor=7):
                largura = len(texto) * 4
                pyxel.text(centro_x - largura // 2, y, texto, cor)

            #mensagem principal
            if self.vencedor_final == "V":
                texto_centralizado(90, "DEU VELHA!")
                texto_centralizado(100, "NENHUM JOGADOR VENCEU")
            else:
                texto_centralizado(95, f"JOGADOR {self.vencedor_final} VENCEU!")

            #botão / status
            if self.pronto:
                texto_centralizado(120, "AGUARDANDO OUTRO JOGADOR...", 6)
            else:
                if self.botao(bx, by, bw, bh, "JOGAR NOVAMENTE"):
                    self.pronto = True
                    self.net.send_ready()

            if self.pronto and self.pronto_outro:
                texto_centralizado(150, "REINICIANDO...", 11)


    #DESENHO
    def desenhar_grade(self):
        #Grade principal (sempre visível)
        for i in range(1, 3):
            x = i * 3 * CELULA
            pyxel.rect(x - 1, 0, 3, TAMANHO, COR_LINHA)
            pyxel.rect(0, x - 1, TAMANHO, 3, COR_LINHA)

        #Grades internas (somente se o bloco NÃO foi vencido)
        for tb_l in range(3):
            for tb_c in range(3):
                if self.principal[tb_l][tb_c]:
                    continue  #bloco vencido → sem linhas internas

                base_x = tb_c * 3 * CELULA
                base_y = tb_l * 3 * CELULA

                for i in range(1, 3):
                    x = base_x + i * CELULA
                    y = base_y + i * CELULA
                    pyxel.line(x, base_y, x, base_y + 3 * CELULA, COR_LINHA_INTERNA)
                    pyxel.line(base_x, y, base_x + 3 * CELULA, y, COR_LINHA_INTERNA)



    def desenhar_simbolos(self):
        for tb_l in range(3):
            for tb_c in range(3):
                vencedor = self.principal[tb_l][tb_c]

                if vencedor:
                    base_x = tb_c * 3 * CELULA
                    base_y = tb_l * 3 * CELULA
                    tamanho = 3 * CELULA

                    if vencedor == "X":
                        cor = COR_X
                        pyxel.line(base_x + 10, base_y + 10,
                                base_x + tamanho - 10, base_y + tamanho - 10, cor)
                        pyxel.line(base_x + tamanho - 10, base_y + 10,
                                base_x + 10, base_y + tamanho - 10, cor)

                    elif vencedor == "O":
                        cor = COR_O
                        pyxel.circb(base_x + tamanho // 2,
                                    base_y + tamanho // 2,
                                    tamanho // 2 - 10, cor)

                    elif vencedor == "V":
                        pyxel.text(base_x + tamanho//2 - 4,
                                base_y + tamanho//2 - 4,
                                "V", 7)

                    continue


                for l in range(3):
                    for c in range(3):
                        s = self.mini[tb_l][tb_c][l][c]
                        if s:
                            cx = (tb_c * 3 + c) * CELULA + CELULA // 2
                            cy = (tb_l * 3 + l) * CELULA + CELULA // 2
                            pyxel.text(cx - 2, cy - 3, s,
                                       COR_X if s == "X" else COR_O)

    def desenhar_destaque(self):
        #Decide a cor com base no turno
        if self.player == self.jogador:
            cor = COR_DESTAQUE_JOGADOR
        else:
            cor = COR_DESTAQUE_OUTRO

        margem = ESPESSURA_PRINCIPAL // 2
        tamanho = 3 * CELULA + ESPESSURA_PRINCIPAL - 2

        def desenhar_bloco(l, c):
            x = c * 3 * CELULA - margem + 1
            y = l * 3 * CELULA - margem + 1

            pyxel.rectb(x, y, tamanho, tamanho, cor)
            pyxel.rectb(x + 1, y + 1, tamanho - 2, tamanho - 2, cor)

        #Pode jogar em qualquer tabuleiro
        if self.proximo_tabuleiro is None:
            for l in range(3):
                for c in range(3):
                    if not self.principal[l][c]:
                        desenhar_bloco(l, c)
            return

        #Tabuleiro específico
        l, c = self.proximo_tabuleiro
        desenhar_bloco(l, c)
    
    def botao(self, x, y, w, h, texto):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hover = x <= mx <= x + w and y <= my <= y + h

        cor = 11 if hover else 7
        pyxel.rectb(x, y, w, h, cor)
        pyxel.text(x + w // 2 - len(texto) * 2,
                y + h // 2 - 3, texto, cor)

        return hover and pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)


#START
UltimateJogoDaVelha()