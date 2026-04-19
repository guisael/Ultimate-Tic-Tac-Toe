# Ultimate Jogo da Velha Online 🎮

Jogo da velha final (Ultimate Tic-Tac-Toe) multijogador com interface gráfica em Pyxel. O jogador humano (X) enfrenta a IA **Gemini 2.0 Flash** (O) via servidor local.

---

## Como funciona

O jogo segue as regras do **Ultimate Tic-Tac-Toe**: um tabuleiro 3×3 de mini-tabuleiros, onde cada jogada determina em qual mini-tabuleiro o adversário deverá jogar a seguir. Quem conquistar três mini-tabuleiros em linha no tabuleiro principal vence.

A IA usa o modelo **Gemini 2.0 Flash** via API do Google, com um prompt estratégico que prioriza: vitória imediata → bloqueio → controle de posição → centro e cantos.

---

## Pré-requisitos

- Python 3.8+
- Conta com acesso à [API do Google Gemini](https://aistudio.google.com/)

Instale as dependências:

```bash
pip install pyxel
```

> O servidor usa apenas bibliotecas padrão do Python (`socket`, `threading`, `json`, `urllib`).

---

## Configuração

### Chave da API Gemini

No arquivo `server.py`, substitua a chave pela sua:

```python
GEMINI_API_KEY = "SUA_CHAVE_AQUI"
```

---

## Como executar

### 1. Inicie o servidor

```bash
python server.py
```

O terminal exibirá o IP local da máquina e confirmará que está aguardando conexões na porta `3040`.

### 2. Inicie o cliente (jogo)

Em outro terminal (ou outra máquina na mesma rede):

```bash
python game.py
```

Quando solicitado, digite o IP do servidor (use `127.0.0.1` se estiver rodando localmente).

---

## Como jogar

- **Clique** em uma célula válida para realizar sua jogada como **X**
- O tabuleiro destacado em **amarelo** indica onde você pode jogar; em **vermelho**, é a vez da IA
- Após cada jogada, a IA (O) responde automaticamente
- Ao fim da partida, clique em **"JOGAR NOVAMENTE"** para reiniciar

---

## Estrutura dos arquivos

```
.
├── server.py   # Servidor TCP + lógica do jogo + integração com Gemini
└── game.py     # Cliente gráfico com Pyxel
```

### `server.py`
- Gerencia a conexão TCP na porta `3040`
- Controla o estado do jogo e valida jogadas
- Integra com a API Gemini para gerar jogadas da IA
- Faz broadcast do estado atualizado para os clientes

### `game.py`
- Interface gráfica com Pyxel (270×270 px)
- Tela de menu, tela de jogo e tela de vitória
- Comunicação assíncrona com o servidor via thread separada

---

## Detalhes técnicos

| Item | Valor |
|---|---|
| Porta TCP | `3040` |
| Resolução | 270 × 270 px |
| Modelo de IA | `gemini-2.0-flash` |
| Protocolo | JSON por linha (`\n`) sobre TCP |
| Player humano | X |
| Player IA | O |