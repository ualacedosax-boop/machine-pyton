# -*- coding: utf-8 -*-
"""
MONITOR V7.1 BLACKARROW — versão GUI (janela gráfica, visual moderno)
=====================================================================

Por que este programa existe
-----------------------------
O monitor original (`monitor_alarme_v71_oficial_completo.ps1`) roda direto no
console do PowerShell e, a cada ~2 segundos, faz `Clear-Host` + reescreve a
tela inteira do zero. Isso é o que causa o "piscar"/recarregar incômodo: o
terminal apaga tudo e desenha tudo de novo, a cada ciclo, para sempre.

Este programa resolve isso fazendo a mesma coisa de um jeito diferente: é uma
janela gráfica de verdade (Tkinter — já vem com o Python, não precisa
instalar nada a mais) que **atualiza só o texto/cor dos campos que mudaram**,
sem apagar e redesenhar a tela. O resultado: os números mudam no lugar, sem
nenhum piscar.

Visual "moderno" (v2)
---------------------
A primeira versão usava um tema estilo "terminal escuro" (fonte Consolas,
cinza/preto). Esta versão troca a casca visual por um estilo "painel/dashboard"
mais contemporâneo, mas continua 100% Tkinter puro (sem depender de pacotes
extras como customtkinter — que não pôde ser instalado aqui por causa de um
bloqueio de certificado SSL no pip):

  - Paleta escura tipo "GitHub Dark" / "Aurora" (fundo quase-preto azulado,
    cartões com borda sutil, acentos em azul/verde/violeta)
  - Tipografia "Segoe UI" (fonte nativa e moderna do Windows) para textos e
    "Cascadia Mono" para números/dados tabulares — em vez do Consolas "de
    terminal" usado antes
  - Cada seção vira um "cartão" com cantos retos porém com borda fina e uma
    faixa colorida no topo (igual painéis de produtos tipo Notion/Linear/GitHub)
  - Selos coloridos tipo "chip/badge" para status (PASSOU, BUY, SELL, etc.)
  - Barras de progresso em formato de "pílula" (pontas arredondadas)

Ele lê exatamente os mesmos arquivos que o monitor em PowerShell
(`ultimo_sinal_v71_blackarrow.json`, os CSVs de eventos/resultados, o CSV de
log de sinal) — então pode rodar em paralelo com ele, ou substituí-lo, sem
nenhuma mudança no robô ou no exportador.

Como rodar
----------
    .venv\\Scripts\\python.exe monitor_v71_gui.py

(ou use o atalho `iniciar_monitor_gui_v71.bat`)
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import threading
import time
import winsound
from datetime import datetime

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

# ============================================================
# CAMINHOS — os mesmos do monitor em PowerShell
# ============================================================

BASE_PATH = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

JSON_PATH_1 = os.path.join(BASE_PATH, "ultimo_sinal_v71_blackarrow.json")
JSON_PATH_2 = os.path.join(BASE_PATH, "operacional_v71_oficial", "ultimo_sinal_v71_blackarrow.json")

CSV_LOG_SINAL = os.path.join(BASE_PATH, "operacional_v71_oficial", "log_sinal_v71_blackarrow.csv")
CSV_EVENTOS = os.path.join(BASE_PATH, "operacional_v71_oficial", "aprendizado_v71", "eventos", "eventos_v71_inteligente.csv")
CSV_RESULTADOS = os.path.join(BASE_PATH, "operacional_v71_oficial", "aprendizado_v71", "resultados", "resultados_v71_inteligente.csv")

# ============================================================
# LIMITES OFICIAIS DA V7.1 (iguais ao monitor em PowerShell)
# ============================================================

MIN_PROB_V51 = 0.590
MIN_PROB_V55 = 0.425
MIN_BUY = 0.74
MIN_SELL = 0.50

INTERVALO_ATUALIZACAO_MS = 1500  # a cada 1,5s — suave, sem sobrecarregar

# ============================================================
# PALETA "AURORA DARK" — tema escuro moderno (inspirado em painéis tipo
# GitHub/Linear/Notion), bem diferente do visual "terminal" da v1
# ============================================================

COR_FUNDO = "#0d1117"          # fundo geral — quase preto, com leve tom azulado
COR_CARTAO = "#161b22"         # fundo dos cartões/seções
COR_CARTAO_CLARO = "#1c2330"   # variação um pouco mais clara (linhas internas)
COR_BORDA = "#30363d"          # borda sutil dos cartões
COR_TEXTO = "#e6edf3"          # texto principal — quase branco
COR_TEXTO_FRACO = "#8b949e"    # texto secundário/legendas
COR_TITULO = "#58a6ff"         # azul de destaque para títulos
COR_VERDE = "#3fb950"
COR_VERMELHO = "#f85149"
COR_AMARELO = "#d29922"
COR_AZUL = "#58a6ff"
COR_VIOLETA = "#bc8cff"
COR_CIANO = "#39d2c0"
COR_BARRA_FUNDO = "#21262d"

# Acentos por seção — cada cartão ganha uma "faixa" colorida no topo,
# o que ajuda a localizar visualmente cada bloco de informação rapidamente
ACENTO_STATUS = COR_AZUL
ACENTO_PROBABILIDADES = COR_CIANO
ACENTO_DIRECAO = COR_VIOLETA
ACENTO_MELHORES = COR_AMARELO
ACENTO_CHECKLIST = COR_VERDE
ACENTO_LOG = COR_TEXTO_FRACO
ACENTO_ALARME = COR_VERMELHO

# Tipografia: "Segoe UI" é a fonte nativa e moderna do Windows (usada no
# próprio Windows 10/11); "Cascadia Mono" é a fonte monoespaçada moderna da
# Microsoft (substitui o "Consolas" de visual mais antigo) — fica reservada
# para números e dados tabulares, onde o alinhamento em colunas importa
#
# IMPORTANTE — por que isso vira tkfont.Font (e não tuplas simples):
# tuplas tipo ("Segoe UI", 10) criam uma fonte "anônima" nova toda vez que
# são usadas, então não dá para mudar o tamanho de todo mundo de uma vez.
# Usando objetos tkfont.Font NOMEADOS — criados uma única vez e reutilizados
# em todos os widgets — qualquer texto que aponte para o mesmo objeto muda de
# tamanho instantaneamente quando a gente reconfigura esse objeto. É assim
# que o controle de "zoom" do cabeçalho funciona sem reconstruir a janela.
# Os objetos de verdade só podem ser criados depois que existir uma janela
# Tk (por isso ficam None aqui e são preenchidos em _inicializar_fontes()).
TAMANHOS_BASE_FONTE = {
    "FONTE_BASE": ("Segoe UI", 10),
    "FONTE_BASE_NEGRITO": ("Segoe UI Semibold", 10),
    "FONTE_TITULO": ("Segoe UI Semibold", 12),
    "FONTE_GRANDE": ("Segoe UI Semibold", 15),
    "FONTE_PEQUENA": ("Segoe UI", 8),
    "FONTE_MONO": ("Cascadia Mono", 10),
    "FONTE_MONO_PEQUENA": ("Cascadia Mono", 8),
    "FONTE_TITULO_APP": ("Segoe UI Semibold", 20),
    "FONTE_SUBTITULO_APP": ("Segoe UI", 14),
}

FONTE_BASE = None
FONTE_BASE_NEGRITO = None
FONTE_TITULO = None
FONTE_GRANDE = None
FONTE_PEQUENA = None
FONTE_MONO = None
FONTE_MONO_PEQUENA = None
FONTE_TITULO_APP = None
FONTE_SUBTITULO_APP = None

# fator de zoom permitido — 70% a 150%, em passos de 10%
ZOOM_MINIMO = 0.7
ZOOM_MAXIMO = 1.5
ZOOM_PASSO = 0.1


def inicializar_fontes():
    """Cria os objetos de fonte nomeados (uma vez, após existir uma janela
    Tk) e os publica como globais — assim 'cartao', 'CampoStatus', 'Selo'
    etc. (que referenciam FONTE_BASE etc.) passam a usar objetos
    compartilhados e ajustáveis em tempo real. Retorna o dicionário desses
    objetos, que o app guarda para poder mudar o tamanho (zoom)."""
    global FONTE_BASE, FONTE_BASE_NEGRITO, FONTE_TITULO, FONTE_GRANDE, FONTE_PEQUENA
    global FONTE_MONO, FONTE_MONO_PEQUENA, FONTE_TITULO_APP, FONTE_SUBTITULO_APP

    fontes = {}
    for nome, (familia, tamanho) in TAMANHOS_BASE_FONTE.items():
        fontes[nome] = tkfont.Font(family=familia, size=tamanho)

    FONTE_BASE = fontes["FONTE_BASE"]
    FONTE_BASE_NEGRITO = fontes["FONTE_BASE_NEGRITO"]
    FONTE_TITULO = fontes["FONTE_TITULO"]
    FONTE_GRANDE = fontes["FONTE_GRANDE"]
    FONTE_PEQUENA = fontes["FONTE_PEQUENA"]
    FONTE_MONO = fontes["FONTE_MONO"]
    FONTE_MONO_PEQUENA = fontes["FONTE_MONO_PEQUENA"]
    FONTE_TITULO_APP = fontes["FONTE_TITULO_APP"]
    FONTE_SUBTITULO_APP = fontes["FONTE_SUBTITULO_APP"]
    return fontes


# ============================================================
# FUNÇÕES UTILITÁRIAS DE LEITURA (espelham a lógica do .ps1)
# ============================================================

def localizar_json():
    if os.path.exists(JSON_PATH_1):
        return JSON_PATH_1
    return JSON_PATH_2


def ler_json_seguro(caminho):
    """Lê o JSON do robô. Pode falhar no meio de uma escrita — tenta de novo."""
    for _ in range(3):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            time.sleep(0.05)
    return None


def to_float(valor):
    try:
        if valor is None or valor == "":
            return float("nan")
        return float(valor)
    except (TypeError, ValueError):
        return float("nan")


def fmt_num(valor, casas=6):
    if valor is None:
        return "-"
    f = to_float(valor)
    if math.isnan(f):
        return "-"
    return f"{f:.{casas}f}".replace(".", ",")


def fmt_valor_bruto(valor):
    """Para campos que não são número (datas, textos, booleanos)."""
    if valor is None or valor == "":
        return "-"
    return str(valor)


# NOTA SOBRE CODIFICAÇÃO: alguns desses CSVs (em especial o de log de sinal,
# que cresce sem parar) acumularam ao longo do tempo trechos gravados em uma
# codificação diferente de UTF-8 (ex.: "Último"/"Máximo" em Latin-1/cp1252).
# Sem "errors='replace'", a leitura quebra com UnicodeDecodeError no meio do
# arquivo — e isso travava justamente a verificação que dispara o alarme
# sonoro (ver Bug #9 na skill v71-blackarrow-troubleshooting). Substituir os
# bytes inválidos por "�" deixa a leitura seguir em frente sem cair o monitor.

def contar_linhas_csv(caminho):
    if not os.path.exists(caminho):
        return 0
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace", newline="") as f:
            return max(0, sum(1 for _ in csv.reader(f, delimiter=";")) - 1)
    except OSError:
        return 0


def ler_ultima_linha_csv(caminho):
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace", newline="") as f:
            leitor = csv.DictReader(f, delimiter=";")
            ultima = None
            for linha in leitor:
                ultima = linha
            return ultima
    except OSError:
        return None


def ler_todas_linhas_csv(caminho):
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace", newline="") as f:
            leitor = csv.DictReader(f, delimiter=";")
            return list(leitor)
    except OSError:
        return []


def ler_cabecalho_csv(caminho):
    """Lê só a primeira linha (cabeçalho) do CSV — usado para montar o
    DictReader manualmente ao processar apenas o trecho novo de um arquivo
    grande, sem precisar reler tudo."""
    try:
        with open(caminho, "rb") as f:
            primeira_linha = f.readline()
        texto = primeira_linha.decode("utf-8", errors="replace")
        linhas = list(csv.reader([texto], delimiter=";"))
        return linhas[0] if linhas else None
    except OSError:
        return None


# ============================================================
# WIDGET: barra de progresso em formato de "pílula" (pontas arredondadas)
# — visual mais moderno que o retângulo reto da v1, e continua sem piscar
# (só apaga/redesenha o preenchimento, nunca o widget inteiro)
# ============================================================

class BarraProgresso(tk.Canvas):
    """Barra horizontal estilo 'pílula' (cantos arredondados nas duas pontas).
    Redesenha apenas o preenchimento a cada atualização — o trilho de fundo
    é fixo, então não há nenhum "flash" perceptível."""

    def __init__(self, master, largura=240, altura=10, **kwargs):
        super().__init__(master, width=largura, height=altura,
                         bg=COR_CARTAO, highlightthickness=0, **kwargs)
        self._largura = largura
        self._altura = altura
        self._raio = altura / 2
        self._desenhar_pilula(0, largura, COR_BARRA_FUNDO, tag="trilho")
        self._item_barra = []

    def _desenhar_pilula(self, x_ini, x_fim, cor, tag):
        """Desenha um retângulo com pontas arredondadas (duas semicircunferências
        + um retângulo central) usando primitivas simples do Canvas."""
        r = self._raio
        largura_total = max(0, x_fim - x_ini)
        if largura_total <= 0:
            return []
        itens = []
        if largura_total <= self._altura:
            # muito curta: desenha só um círculo (evita retângulo "negativo")
            itens.append(self.create_oval(x_ini, 0, x_ini + self._altura, self._altura,
                                           fill=cor, outline="", tags=tag))
            return itens
        itens.append(self.create_oval(x_ini, 0, x_ini + self._altura, self._altura,
                                       fill=cor, outline="", tags=tag))
        itens.append(self.create_rectangle(x_ini + r, 0, x_fim - r, self._altura,
                                            fill=cor, outline="", tags=tag))
        itens.append(self.create_oval(x_fim - self._altura, 0, x_fim, self._altura,
                                       fill=cor, outline="", tags=tag))
        return itens

    def atualizar(self, fracao, cor):
        fracao = max(0.0, min(1.0, fracao))
        largura_preenchida = int(self._largura * fracao)
        self.delete("preenchimento")
        if largura_preenchida > 0:
            self._desenhar_pilula(0, largura_preenchida, cor, tag="preenchimento")


# ============================================================
# SELO ("chip"/"badge") — texto curto destacado com fundo colorido,
# usado para status como PASSOU / NÃO PASSOU / BUY / SELL / sem dados
# ============================================================

class Selo(tk.Label):
    """Rótulo estilo 'badge' moderno: bloco colorido com cantos retos mas
    bastante respiro (padding) — o efeito visual de um 'chip' de status que
    aparece em painéis modernos, sem precisar desenhar formas no Canvas."""

    def __init__(self, master, texto="-", **kwargs):
        super().__init__(master, text=texto, font=FONTE_BASE_NEGRITO,
                         padx=10, pady=2, bd=0, **kwargs)

    def definir(self, texto, cor_fundo, cor_texto="#0d1117"):
        self.config(text=f" {texto} ", bg=cor_fundo, fg=cor_texto)


# ============================================================
# LINHA DE SCORE (nome, valor atual, mínimo, melhor, barra) — widget composto
# ============================================================

class LinhaScore:
    """Uma linha 'Prob V5.1 : 0,613 / min 0,590 | melhor 0,724' com barra
    de progresso em pílula e selo PASSOU/NÃO PASSOU — tudo atualizável no
    lugar, sem recriar widgets a cada ciclo."""

    def __init__(self, master, nome):
        self.frame = tk.Frame(master, bg=COR_CARTAO)
        self.frame.pack(fill="x", pady=(4, 10))

        linha_topo = tk.Frame(self.frame, bg=COR_CARTAO)
        linha_topo.pack(fill="x")

        self.lbl_nome = tk.Label(linha_topo, text=nome, font=FONTE_BASE_NEGRITO,
                                 fg=COR_TEXTO, bg=COR_CARTAO, width=11, anchor="w")
        self.lbl_nome.pack(side="left")

        self.lbl_valores = tk.Label(linha_topo, text="-", font=FONTE_MONO,
                                    fg=COR_TEXTO_FRACO, bg=COR_CARTAO, anchor="w")
        self.lbl_valores.pack(side="left", padx=(8, 0))

        linha_barra = tk.Frame(self.frame, bg=COR_CARTAO)
        linha_barra.pack(fill="x", pady=(6, 0))

        tk.Label(linha_barra, text="", width=11, bg=COR_CARTAO).pack(side="left")
        self.barra = BarraProgresso(linha_barra)
        self.barra.pack(side="left", padx=(8, 12))

        self.selo_status = Selo(linha_barra, "-", bg=COR_BARRA_FUNDO, fg=COR_TEXTO_FRACO)
        self.selo_status.pack(side="left")

        self.lbl_falta = tk.Label(linha_barra, text="", font=FONTE_PEQUENA,
                                  fg=COR_TEXTO_FRACO, bg=COR_CARTAO, anchor="w")
        self.lbl_falta.pack(side="left", padx=(10, 0))

    def atualizar(self, valor, minimo, melhor):
        valor_f = to_float(valor)
        minimo_f = to_float(minimo)
        melhor_f = to_float(melhor)

        self.lbl_valores.config(
            text=f"{fmt_num(valor_f, 6)}   ·   mínimo {fmt_num(minimo_f, 3)}   ·   melhor {fmt_num(melhor_f, 6)}"
        )

        if math.isnan(valor_f) or math.isnan(minimo_f) or minimo_f <= 0:
            self.barra.atualizar(0.0, COR_BARRA_FUNDO)
            self.selo_status.definir("SEM DADOS", COR_BARRA_FUNDO, COR_TEXTO_FRACO)
            self.lbl_falta.config(text="")
            return

        passou = valor_f >= minimo_f
        cor = COR_VERDE if passou else COR_VERMELHO
        fracao = valor_f / minimo_f if minimo_f > 0 else 0.0
        self.barra.atualizar(fracao, cor)

        falta = max(0.0, minimo_f - valor_f)
        if passou:
            self.selo_status.definir("PASSOU", COR_VERDE, "#0d1117")
            self.lbl_falta.config(text="dentro do mínimo ✓", fg=COR_VERDE)
        else:
            self.selo_status.definir("NÃO PASSOU", COR_VERMELHO, "#0d1117")
            self.lbl_falta.config(text=f"falta {fmt_num(falta, 6)}", fg=COR_TEXTO_FRACO)


# ============================================================
# CAMPO SIMPLES "rótulo : valor" reutilizável, atualizável no lugar
# ============================================================

class CampoStatus:
    def __init__(self, master, rotulo, largura_rotulo=14, fonte_valor=None):
        self.frame = tk.Frame(master, bg=COR_CARTAO)
        self.frame.pack(fill="x", pady=2)
        tk.Label(self.frame, text=rotulo, font=FONTE_BASE, fg=COR_TEXTO_FRACO,
                 bg=COR_CARTAO, width=largura_rotulo, anchor="w").pack(side="left")
        self.valor_lbl = tk.Label(self.frame, text="-", font=(fonte_valor or FONTE_BASE_NEGRITO),
                                  fg=COR_TEXTO, bg=COR_CARTAO, anchor="w")
        self.valor_lbl.pack(side="left", padx=(4, 0))

    def set(self, texto, cor=None):
        self.valor_lbl.config(text=str(texto), fg=(cor or COR_TEXTO))


# ============================================================
# CARTÃO DE SEÇÃO — bloco estilo "painel moderno": fundo levemente mais
# claro que o fundo geral, borda fina e uma faixa colorida no topo. É o
# equivalente visual aos "cards" usados em dashboards contemporâneos
# (GitHub, Linear, Notion etc.), e substitui o bloco "chapado" da v1.
# ============================================================

def cartao(master, titulo, icone="", cor_acento=None):
    """Monta um 'cartão' (moldura com borda + faixa colorida + título) mas
    DELIBERADAMENTE não se posiciona sozinho — quem chama decide se ele
    fica empilhado (.pack) ou lado a lado (.grid), o que é o que permite
    organizar os cartões em colunas. Devolve (moldura, corpo): "moldura" é
    o que vai para o gerenciador de geometria do chamador, "corpo" é onde
    o conteúdo da seção deve ser montado."""
    cor_acento = cor_acento or COR_TITULO

    moldura = tk.Frame(master, bg=COR_CARTAO, highlightbackground=COR_BORDA,
                       highlightcolor=COR_BORDA, highlightthickness=1, bd=0)

    faixa = tk.Frame(moldura, bg=cor_acento, height=3)
    faixa.pack(fill="x", side="top")

    corpo = tk.Frame(moldura, bg=COR_CARTAO, padx=20, pady=16)
    corpo.pack(fill="both", expand=True)

    cabecalho = tk.Frame(corpo, bg=COR_CARTAO)
    cabecalho.pack(fill="x", pady=(0, 12))
    texto_titulo = f"{icone}   {titulo}" if icone else titulo
    tk.Label(cabecalho, text=texto_titulo, font=FONTE_TITULO, fg=COR_TEXTO,
             bg=COR_CARTAO, anchor="w").pack(side="left")

    return moldura, corpo


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================

class MonitorV71App:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor V7.1 — BlackArrow")
        self.root.configure(bg=COR_FUNDO)
        # janela mais larga que a v2: agora os cartões ficam lado a lado em
        # duas colunas, então o layout aproveita melhor um formato "wide"
        self.root.geometry("1180x860")
        self.root.minsize(760, 560)

        # ---- zoom: fator aplicado sobre o tamanho-base de todas as fontes.
        # Criar as fontes como objetos nomeados (ver inicializar_fontes) é o
        # que torna isso possível sem reconstruir a interface inteira — só
        # mudamos o tamanho desses poucos objetos e cada texto que os usa
        # se redesenha sozinho, na hora.
        self._fator_zoom = 1.0
        self._fontes = inicializar_fontes()

        # ---- estado acumulado entre ciclos (espelha as variáveis "melhor*" do .ps1)
        self.melhores = {
            "v51": {"valor": float("-inf"), "hora": "", "preco": ""},
            "v55": {"valor": float("-inf"), "hora": "", "preco": ""},
            "gap": {"valor": float("-inf"), "hora": "", "preco": ""},
            "buy": {"valor": float("-inf"), "hora": "", "preco": ""},
            "sell": {"valor": float("-inf"), "hora": "", "preco": ""},
        }
        # estado para a leitura incremental ("tail") do CSV de log de sinal —
        # ver _verificar_entrada_real_csv para o porquê de não reler tudo
        self._posicao_csv_sinal = None       # posição em bytes de onde paramos de ler
        self._cabecalho_csv_sinal = None     # nomes das colunas (lidos uma vez só)
        self._ultimo_alarme_id = None        # evita repetir o mesmo alarme

        self._montar_interface()
        self._agendar_atualizacao(imediata=True)

    # --------------------------------------------------------
    # MONTAGEM DA INTERFACE (uma vez só — depois só atualizamos texto/cor)
    # --------------------------------------------------------
    def _montar_interface(self):
        LARGURA_TEXTO_LARGO = 920    # quebra de linha p/ textos que ocupam as 2 colunas
        LARGURA_TEXTO_ESTREITO = 430  # quebra de linha p/ textos de cartão de 1 coluna

        # --- cabeçalho estilo "topo de painel" ---
        cab = tk.Frame(self.root, bg=COR_FUNDO, padx=22, pady=16)
        cab.pack(fill="x")

        linha_titulo = tk.Frame(cab, bg=COR_FUNDO)
        linha_titulo.pack(fill="x", anchor="w")

        # "ponto" indicador estilo status — dá um toque de painel de monitoramento moderno
        self.indicador = tk.Canvas(linha_titulo, width=14, height=14, bg=COR_FUNDO, highlightthickness=0)
        self.indicador.pack(side="left", padx=(0, 10))
        self._ponto_indicador = self.indicador.create_oval(2, 2, 12, 12, fill=COR_VERDE, outline="")

        tk.Label(linha_titulo, text="Monitor V7.1", font=FONTE_TITULO_APP,
                 fg=COR_TEXTO, bg=COR_FUNDO).pack(side="left")
        tk.Label(linha_titulo, text="  ·  BlackArrow Oficial", font=FONTE_SUBTITULO_APP,
                 fg=COR_TEXTO_FRACO, bg=COR_FUNDO).pack(side="left")

        # ---- controle de ZOOM (deixa tudo menor/maior para caber mais na tela) ----
        zoom_box = tk.Frame(linha_titulo, bg=COR_FUNDO)
        zoom_box.pack(side="right")

        tk.Label(zoom_box, text="Zoom", font=FONTE_PEQUENA, fg=COR_TEXTO_FRACO,
                 bg=COR_FUNDO).pack(side="left", padx=(0, 6))

        def _botao_zoom(texto, comando):
            return tk.Label(zoom_box, text=texto, font=FONTE_BASE_NEGRITO, fg=COR_TEXTO,
                            bg=COR_CARTAO, padx=10, pady=3, cursor="hand2",
                            highlightbackground=COR_BORDA, highlightthickness=1)

        btn_zoom_menos = _botao_zoom("－", lambda: self._ajustar_zoom(-ZOOM_PASSO))
        btn_zoom_menos.pack(side="left", padx=(0, 4))
        btn_zoom_menos.bind("<Button-1>", lambda e: self._ajustar_zoom(-ZOOM_PASSO))

        self.lbl_zoom = tk.Label(zoom_box, text="100%", font=FONTE_BASE_NEGRITO, fg=COR_TEXTO_FRACO,
                                 bg=COR_FUNDO, width=5, anchor="center")
        self.lbl_zoom.pack(side="left")

        btn_zoom_mais = _botao_zoom("＋", lambda: self._ajustar_zoom(ZOOM_PASSO))
        btn_zoom_mais.pack(side="left", padx=(4, 0))
        btn_zoom_mais.bind("<Button-1>", lambda e: self._ajustar_zoom(ZOOM_PASSO))

        btn_zoom_resetar = tk.Label(zoom_box, text="100%", font=FONTE_PEQUENA, fg=COR_TEXTO_FRACO,
                                    bg=COR_FUNDO, padx=8, cursor="hand2", underline=0)
        # (rótulo de reset reaproveita o clique-duplo — ver bind abaixo)
        btn_zoom_mais.bind("<Double-Button-1>", lambda e: self._ajustar_zoom(reset=True))
        btn_zoom_menos.bind("<Double-Button-1>", lambda e: self._ajustar_zoom(reset=True))

        # atalhos de teclado: Ctrl + roda do mouse, Ctrl +/-/0 (como em navegadores)
        self.root.bind_all("<Control-MouseWheel>", self._zoom_pelo_mouse)
        self.root.bind_all("<Control-plus>", lambda e: self._ajustar_zoom(ZOOM_PASSO))
        self.root.bind_all("<Control-equal>", lambda e: self._ajustar_zoom(ZOOM_PASSO))
        self.root.bind_all("<Control-minus>", lambda e: self._ajustar_zoom(-ZOOM_PASSO))
        self.root.bind_all("<Control-Key-0>", lambda e: self._ajustar_zoom(reset=True))

        self.lbl_atualizacao = tk.Label(cab, text="Atualização: -", font=FONTE_BASE,
                                        fg=COR_TEXTO_FRACO, bg=COR_FUNDO)
        self.lbl_atualizacao.pack(anchor="w", pady=(6, 0))

        # detalhes técnicos (caminhos) — escondidos por padrão, expansível
        self._fontes_visiveis = tk.BooleanVar(value=False)
        self.btn_fontes = tk.Label(cab, text="▸ mostrar fontes de dados  ·  dica: Ctrl + roda do mouse para dar zoom",
                                   font=FONTE_PEQUENA, fg=COR_TEXTO_FRACO, bg=COR_FUNDO, cursor="hand2")
        self.btn_fontes.pack(anchor="w", pady=(8, 0))
        self.btn_fontes.bind("<Button-1>", self._alternar_fontes)
        self.lbl_fontes = tk.Label(cab, text="", font=FONTE_MONO_PEQUENA, fg=COR_TEXTO_FRACO,
                                   bg=COR_FUNDO, justify="left")
        # só é exibido quando o usuário clicar em "mostrar fontes de dados"

        # linha divisória sutil sob o cabeçalho
        tk.Frame(self.root, bg=COR_BORDA, height=1).pack(fill="x")

        # ---- BANNER DE ALARME — fica FIXO logo abaixo do cabeçalho (fora da
        # área rolável), assim continua visível mesmo se o usuário rolar a
        # tela para baixo para ver outros cartões ----
        self.banner = tk.Label(self.root, text="", font=FONTE_GRANDE, fg="#0d1117",
                               bg=COR_CARTAO, padx=18, pady=14, anchor="w", justify="left",
                               wraplength=LARGURA_TEXTO_LARGO)
        # só faz .pack() quando houver algo a mostrar (ver _atualizar_alarme/_mostrar_alarme_entrada)

        # --- área rolável: os cartões ficam em uma GRADE DE 2 COLUNAS lado a
        # lado, para aproveitar telas largas e mostrar mais coisa de uma vez
        # (em vez da pilha vertical única da v2, que obrigava a rolar muito) ---
        canvas = tk.Canvas(self.root, bg=COR_FUNDO, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.area = tk.Frame(canvas, bg=COR_FUNDO)
        self._canvas_area = canvas

        self.area.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _ajustar_largura_area(event):
            # faz o conteúdo da grade acompanhar a largura do canvas (senão
            # os cartões ficariam com largura "natural" e não esticariam)
            canvas.itemconfig(janela_area, width=event.width)
        janela_area = canvas.create_window((0, 0), window=self.area, anchor="nw")
        canvas.bind("<Configure>", _ajustar_largura_area)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # roda do mouse (sem Ctrl = rolar; com Ctrl = zoom, tratado à parte)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # duas colunas de largura igual — "uniform" garante que elas encolhem/
        # crescem juntas quando a janela é redimensionada
        self.area.grid_columnconfigure(0, weight=1, uniform="coluna_cartao")
        self.area.grid_columnconfigure(1, weight=1, uniform="coluna_cartao")

        PAD = dict(padx=8, pady=8)
        linha_grade = 0

        # ---- STATUS ATUAL — ocupa as duas colunas (é o cartão mais detalhado) ----
        moldura, bloco = cartao(self.area, "Status atual", "●", ACENTO_STATUS)
        moldura.grid(row=linha_grade, column=0, columnspan=2, sticky="nsew", **PAD)
        linha_grade += 1

        grade = tk.Frame(bloco, bg=COR_CARTAO)
        grade.pack(fill="x")
        col_esq = tk.Frame(grade, bg=COR_CARTAO)
        col_esq.pack(side="left", fill="both", expand=True, anchor="n")
        col_dir = tk.Frame(grade, bg=COR_CARTAO)
        col_dir.pack(side="left", fill="both", expand=True, anchor="n")

        self.campo_versao = CampoStatus(col_esq, "Versão")
        self.campo_sinal = CampoStatus(col_esq, "Sinal")
        self.campo_motivo = CampoStatus(col_esq, "Motivo")
        self.campo_execucao = CampoStatus(col_esq, "Execução")
        self.campo_candle = CampoStatus(col_esq, "Candle")
        self.campo_data = CampoStatus(col_esq, "Data")
        self.campo_preco = CampoStatus(col_esq, "Preço")
        self.campo_take = CampoStatus(col_esq, "Take")

        self.campo_stop = CampoStatus(col_dir, "Stop")
        self.campo_direcao = CampoStatus(col_dir, "Direção")
        self.campo_modo_seguro = CampoStatus(col_dir, "Modo seguro")
        self.campo_candles = CampoStatus(col_dir, "Candles")
        self.campo_dentro_hora = CampoStatus(col_dir, "Dentro horário")
        self.campo_horario_ok = CampoStatus(col_dir, "Horário ok")
        self.campo_bloq0430 = CampoStatus(col_dir, "Bloq 04:30")

        # ---- AVISO DE CANDLE TRAVADO (dentro do status, destaca quando existe) ----
        self.aviso_candle = tk.Label(bloco, text="", font=FONTE_BASE_NEGRITO, fg="#0d1117",
                                     bg=COR_AMARELO, padx=12, pady=10, anchor="w",
                                     justify="left", wraplength=LARGURA_TEXTO_LARGO)
        # só faz .pack quando houver aviso

        # ---- linha 2: Probabilidades (col. esquerda) | Direção/Scores (col. direita) ----
        moldura, bloco = cartao(self.area, "Probabilidades V7.1", "▲", ACENTO_PROBABILIDADES)
        moldura.grid(row=linha_grade, column=0, sticky="nsew", **PAD)
        self.linha_v51 = LinhaScore(bloco, "Prob V5.1")
        self.linha_v55 = LinhaScore(bloco, "Prob V5.5")
        self.campo_gap = CampoStatus(bloco, "Gap V51-V55", largura_rotulo=14, fonte_valor=FONTE_MONO)

        moldura, bloco = cartao(self.area, "Direção V3 / Scores", "↕", ACENTO_DIRECAO)
        moldura.grid(row=linha_grade, column=1, sticky="nsew", **PAD)
        self.campo_none = CampoStatus(bloco, "NONE", fonte_valor=FONTE_MONO)
        self.linha_buy = LinhaScore(bloco, "BUY")
        self.linha_sell = LinhaScore(bloco, "SELL")
        self.campo_score_diff = CampoStatus(bloco, "Score diff", fonte_valor=FONTE_MONO)
        linha_grade += 1

        # ---- linha 3: Melhores (col. esquerda) | Checklist (col. direita) ----
        moldura, bloco = cartao(self.area, "Melhores desde que abriu", "★", ACENTO_MELHORES)
        moldura.grid(row=linha_grade, column=0, sticky="nsew", **PAD)
        self.campo_melhor_v51 = CampoStatus(bloco, "Melhor V5.1", largura_rotulo=14, fonte_valor=FONTE_MONO)
        self.campo_melhor_v55 = CampoStatus(bloco, "Melhor V5.5", largura_rotulo=14, fonte_valor=FONTE_MONO)
        self.campo_melhor_gap = CampoStatus(bloco, "Melhor Gap", largura_rotulo=14, fonte_valor=FONTE_MONO)
        self.campo_melhor_buy = CampoStatus(bloco, "Melhor BUY", largura_rotulo=14, fonte_valor=FONTE_MONO)
        self.campo_melhor_sell = CampoStatus(bloco, "Melhor SELL", largura_rotulo=14, fonte_valor=FONTE_MONO)

        moldura, bloco = cartao(self.area, "Checklist V7.1", "✓", ACENTO_CHECKLIST)
        moldura.grid(row=linha_grade, column=1, sticky="nsew", **PAD)
        self.check_v51 = CampoStatus(bloco, "Prob V5.1 ≥ 0,590", largura_rotulo=20)
        self.check_v55 = CampoStatus(bloco, "Prob V5.5 ≥ 0,425", largura_rotulo=20)
        self.check_buy = CampoStatus(bloco, "BUY ≥ 0,74", largura_rotulo=20)
        self.check_sell = CampoStatus(bloco, "SELL ≥ 0,50", largura_rotulo=20)
        self.check_dir_buy = CampoStatus(bloco, "Direção BUY", largura_rotulo=20)
        self.check_dir_sell = CampoStatus(bloco, "Direção SELL", largura_rotulo=20)

        tk.Frame(bloco, bg=COR_BORDA, height=1).pack(fill="x", pady=10)
        self.lbl_regra_buy = tk.Label(bloco, text="Regra BUY  ·  V5.1 ≥ 0,590 + V5.5 ≥ 0,425 + BUY ≥ 0,74 + Direção BUY + horário/gestão",
                                      font=FONTE_PEQUENA, fg=COR_TEXTO_FRACO, bg=COR_CARTAO,
                                      anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_regra_buy.pack(fill="x")
        self.lbl_regra_sell = tk.Label(bloco, text="Regra SELL  ·  V5.1 ≥ 0,590 + V5.5 ≥ 0,425 + SELL ≥ 0,50 + Direção SELL + horário/gestão",
                                       font=FONTE_PEQUENA, fg=COR_TEXTO_FRACO, bg=COR_CARTAO,
                                       anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_regra_sell.pack(fill="x", pady=(3, 0))
        linha_grade += 1

        # ---- linha 4: Log inteligente (col. esquerda) | Status do alarme (col. direita) ----
        moldura, bloco = cartao(self.area, "Log inteligente", "▤", ACENTO_LOG)
        moldura.grid(row=linha_grade, column=0, sticky="nsew", **PAD)
        self.campo_eventos = CampoStatus(bloco, "Eventos registrados", largura_rotulo=18, fonte_valor=FONTE_MONO)
        self.campo_resultados = CampoStatus(bloco, "Resultados fechados", largura_rotulo=18, fonte_valor=FONTE_MONO)
        self.campo_ultimo_resultado = CampoStatus(bloco, "Último resultado", largura_rotulo=18)

        moldura, bloco = cartao(self.area, "Status do alarme", "⚑", ACENTO_ALARME)
        moldura.grid(row=linha_grade, column=1, sticky="nsew", **PAD)
        self.lbl_check_principal = tk.Label(bloco, text="-", font=FONTE_BASE, fg=COR_AMARELO,
                                            bg=COR_CARTAO, anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_check_principal.pack(fill="x", pady=3)
        self.lbl_alarme = tk.Label(bloco, text="-", font=FONTE_BASE, fg=COR_AMARELO,
                                   bg=COR_CARTAO, anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_alarme.pack(fill="x", pady=3)
        linha_grade += 1

        # espaço extra no fim da área rolável
        tk.Frame(self.area, bg=COR_FUNDO, height=14).grid(row=linha_grade, column=0, columnspan=2)

        # ---- rodapé ----
        tk.Frame(self.root, bg=COR_BORDA, height=1).pack(fill="x")
        rodape = tk.Frame(self.root, bg=COR_FUNDO, padx=22, pady=10)
        rodape.pack(fill="x")
        self.lbl_status_geral = tk.Label(rodape, text="iniciando…", font=FONTE_PEQUENA,
                                         fg=COR_TEXTO_FRACO, bg=COR_FUNDO, anchor="w")
        self.lbl_status_geral.pack(side="left")

    # --------------------------------------------------------
    # ZOOM — muda o tamanho de TODAS as fontes de uma vez (ver inicializar_fontes:
    # como os widgets compartilham os mesmos objetos tkfont.Font, não é preciso
    # reconstruir nada — eles se redesenham sozinhos no novo tamanho)
    # --------------------------------------------------------
    def _ajustar_zoom(self, delta=0.0, reset=False):
        novo_fator = 1.0 if reset else round(self._fator_zoom + delta, 2)
        novo_fator = max(ZOOM_MINIMO, min(ZOOM_MAXIMO, novo_fator))
        if novo_fator == self._fator_zoom:
            return
        self._fator_zoom = novo_fator

        for nome, (_familia, tamanho_base) in TAMANHOS_BASE_FONTE.items():
            novo_tamanho = max(6, round(tamanho_base * self._fator_zoom))
            self._fontes[nome].configure(size=novo_tamanho)

        self.lbl_zoom.config(text=f"{round(self._fator_zoom * 100)}%")

    def _zoom_pelo_mouse(self, evento):
        """Ctrl + roda do mouse = zoom (igual navegadores e editores modernos)."""
        if evento.delta > 0:
            self._ajustar_zoom(ZOOM_PASSO)
        else:
            self._ajustar_zoom(-ZOOM_PASSO)
        return "break"  # evita que o evento "vaze" e role a tela ao mesmo tempo

    # --------------------------------------------------------
    # alterna a exibição do bloco "fontes de dados" (caminhos completos)
    # --------------------------------------------------------
    def _alternar_fontes(self, _evento=None):
        mostrar = not self._fontes_visiveis.get()
        self._fontes_visiveis.set(mostrar)
        if mostrar:
            self.btn_fontes.config(text="▾ ocultar fontes de dados")
            self.lbl_fontes.pack(anchor="w", pady=(4, 0))
        else:
            self.btn_fontes.config(text="▸ mostrar fontes de dados")
            self.lbl_fontes.pack_forget()

    # --------------------------------------------------------
    # CICLO DE ATUALIZAÇÃO (agendado via root.after — não bloqueia a janela)
    # --------------------------------------------------------
    def _agendar_atualizacao(self, imediata=False):
        if imediata:
            self.root.after(50, self._ciclo)
        else:
            self.root.after(INTERVALO_ATUALIZACAO_MS, self._ciclo)

    def _ciclo(self):
        try:
            self._atualizar_tudo()
            self.indicador.itemconfig(self._ponto_indicador, fill=COR_VERDE)
            self.lbl_status_geral.config(
                text=f"Última leitura OK às {datetime.now().strftime('%H:%M:%S')}  ·  atualizando a cada {INTERVALO_ATUALIZACAO_MS/1000:.1f}s",
                fg=COR_TEXTO_FRACO)
        except Exception as exc:  # nunca deixa o loop morrer por um erro pontual de leitura
            self.indicador.itemconfig(self._ponto_indicador, fill=COR_AMARELO)
            self.lbl_status_geral.config(text=f"Aviso: erro ao atualizar ({exc})", fg=COR_AMARELO)
        finally:
            self._agendar_atualizacao()

    def _atualizar_tudo(self):
        caminho_json = localizar_json()
        self.lbl_fontes.config(
            text=(f"JSON do robô :  {caminho_json}\n"
                  f"CSV de sinal :  {CSV_LOG_SINAL}\n"
                  f"Eventos      :  {CSV_EVENTOS}\n"
                  f"Resultados   :  {CSV_RESULTADOS}")
        )
        self.lbl_atualizacao.config(text=f"Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not os.path.exists(caminho_json):
            self.indicador.itemconfig(self._ponto_indicador, fill=COR_VERMELHO)
            self.lbl_check_principal.config(text="ERRO: JSON não encontrado — verifique se o robô está rodando.", fg=COR_VERMELHO)
            return

        dados = ler_json_seguro(caminho_json)
        if dados is None:
            self.indicador.itemconfig(self._ponto_indicador, fill=COR_VERMELHO)
            self.lbl_check_principal.config(text="ERRO: não foi possível ler o JSON (tente de novo no próximo ciclo).", fg=COR_VERMELHO)
            return

        self._atualizar_status(dados)
        self._atualizar_probabilidades(dados)
        self._atualizar_direcao_scores(dados)
        self._atualizar_melhores(dados)
        self._atualizar_checklist(dados)
        self._atualizar_log_inteligente()
        self._atualizar_alarme(dados)
        self._verificar_entrada_real_csv()

    # ----- seções individuais -----

    def _atualizar_status(self, d):
        sinal = str(d.get("sinal", "none")).lower()
        cor_sinal = COR_VERDE if sinal == "buy" else COR_VERMELHO if sinal == "sell" else COR_TEXTO_FRACO

        direcao = str(d.get("Direcao", d.get("direcao", "-")))
        cor_direcao = COR_VERDE if direcao == "BUY" else COR_VERMELHO if direcao == "SELL" else COR_TEXTO

        self.campo_versao.set(fmt_valor_bruto(d.get("versao_robo")))
        self.campo_sinal.set(sinal, cor_sinal)
        self.campo_motivo.set(fmt_valor_bruto(d.get("motivo")))
        self.campo_execucao.set(fmt_valor_bruto(d.get("datahora_execucao")))
        self.campo_candle.set(fmt_valor_bruto(d.get("datahora_ultimo_candle_sp")))
        self.campo_data.set(fmt_valor_bruto(d.get("data")))
        self.campo_preco.set(fmt_valor_bruto(d.get("preco_close")))
        self.campo_take.set(fmt_valor_bruto(d.get("preco_take")))

        self.campo_stop.set(fmt_valor_bruto(d.get("preco_stop")))
        self.campo_direcao.set(direcao, cor_direcao)
        self.campo_modo_seguro.set(fmt_valor_bruto(d.get("modo_seguro_sem_ordem")))
        self.campo_candles.set(fmt_valor_bruto(d.get("candles_disponiveis")))

        dentro_hora = bool(d.get("dentro_horario_v4") or d.get("dentro_horario_v7"))
        self.campo_dentro_hora.set(dentro_hora, COR_VERDE if dentro_hora else COR_TEXTO_FRACO)

        horario_ok = bool(d.get("horario_operacional_valido"))
        self.campo_horario_ok.set(horario_ok, COR_VERDE if horario_ok else COR_TEXTO_FRACO)

        bloq = bool(d.get("bloqueio_0430_0444") or d.get("bloquear_0430_0444"))
        self.campo_bloq0430.set(bloq, COR_VERMELHO if bloq else COR_TEXTO_FRACO)

        # aviso de candle travado — só aparece quando existe
        aviso = str(d.get("aviso_candle_travado") or "").strip()
        if aviso:
            self.aviso_candle.config(text=f"⚠  DADOS DESATUALIZADOS — {aviso}\n     Verifique o exportador Excel (exportar_blackarrow_excel_v71.ps1)")
            if not self.aviso_candle.winfo_ismapped():
                self.aviso_candle.pack(fill="x", pady=(12, 0))
        else:
            if self.aviso_candle.winfo_ismapped():
                self.aviso_candle.pack_forget()

    def _atualizar_probabilidades(self, d):
        prob_v51 = d.get("prob_v51", d.get("prob_win_v4"))
        prob_v55 = d.get("prob_v55", d.get("prob_v5_5"))
        gap = d.get("gap_v51_v55", d.get("gap"))

        self.linha_v51.atualizar(prob_v51, MIN_PROB_V51, self.melhores["v51"]["valor"])
        self.linha_v55.atualizar(prob_v55, MIN_PROB_V55, self.melhores["v55"]["valor"])

        gap_f = to_float(gap)
        melhor_gap = self.melhores["gap"]["valor"]
        self.campo_gap.set(
            f"{fmt_num(gap_f, 6)}   ·   melhor {fmt_num(melhor_gap if melhor_gap != float('-inf') else float('nan'), 6)}"
        )

        # guarda os valores atuais para o cálculo de "melhores"
        self._ultimo_v51 = to_float(prob_v51)
        self._ultimo_v55 = to_float(prob_v55)
        self._ultimo_gap = gap_f

    def _atualizar_direcao_scores(self, d):
        none_score = d.get("score_NONE")
        buy_score = d.get("score_BUY")
        sell_score = d.get("score_SELL")
        score_diff = d.get("score_diff")

        self.campo_none.set(fmt_num(to_float(none_score), 6))
        self.linha_buy.atualizar(buy_score, MIN_BUY, self.melhores["buy"]["valor"])
        self.linha_sell.atualizar(sell_score, MIN_SELL, self.melhores["sell"]["valor"])
        self.campo_score_diff.set(fmt_num(to_float(score_diff), 6))

        self._ultimo_buy = to_float(buy_score)
        self._ultimo_sell = to_float(sell_score)
        self._ultima_direcao = str(d.get("Direcao", d.get("direcao", "")))

    def _atualizar_melhores(self, d):
        candle = fmt_valor_bruto(d.get("datahora_ultimo_candle_sp"))
        preco = fmt_valor_bruto(d.get("preco_close"))

        def _checa(chave, valor_atual):
            if not math.isnan(valor_atual) and valor_atual > self.melhores[chave]["valor"]:
                self.melhores[chave] = {"valor": valor_atual, "hora": candle, "preco": preco}

        _checa("v51", getattr(self, "_ultimo_v51", float("nan")))
        _checa("v55", getattr(self, "_ultimo_v55", float("nan")))
        _checa("gap", getattr(self, "_ultimo_gap", float("nan")))
        _checa("buy", getattr(self, "_ultimo_buy", float("nan")))
        _checa("sell", getattr(self, "_ultimo_sell", float("nan")))

        def _linha(m):
            if m["valor"] == float("-inf"):
                return "ainda sem dados nesta sessão"
            return f"{fmt_num(m['valor'], 6)}   ·   {m['hora']}   ·   preço {m['preco']}"

        self.campo_melhor_v51.set(_linha(self.melhores["v51"]))
        self.campo_melhor_v55.set(_linha(self.melhores["v55"]))
        self.campo_melhor_gap.set(_linha(self.melhores["gap"]))
        self.campo_melhor_buy.set(_linha(self.melhores["buy"]))
        self.campo_melhor_sell.set(_linha(self.melhores["sell"]))

    def _atualizar_checklist(self, d):
        v51 = getattr(self, "_ultimo_v51", float("nan"))
        v55 = getattr(self, "_ultimo_v55", float("nan"))
        buy = getattr(self, "_ultimo_buy", float("nan"))
        sell = getattr(self, "_ultimo_sell", float("nan"))
        direcao = getattr(self, "_ultima_direcao", "")

        passou_v51 = (not math.isnan(v51)) and v51 >= MIN_PROB_V51
        passou_v55 = (not math.isnan(v55)) and v55 >= MIN_PROB_V55
        passou_buy = (not math.isnan(buy)) and buy >= MIN_BUY
        passou_sell = (not math.isnan(sell)) and sell >= MIN_SELL
        dir_buy = direcao == "BUY"
        dir_sell = direcao == "SELL"

        def _marca(campo, ok):
            campo.set(("✓  PASSOU" if ok else "✕  NÃO PASSOU"), COR_VERDE if ok else COR_VERMELHO)

        _marca(self.check_v51, passou_v51)
        _marca(self.check_v55, passou_v55)
        _marca(self.check_buy, passou_buy)
        _marca(self.check_sell, passou_sell)
        _marca(self.check_dir_buy, dir_buy)
        _marca(self.check_dir_sell, dir_sell)

        self._regra_buy = passou_v51 and passou_v55 and passou_buy and dir_buy
        self._regra_sell = passou_v51 and passou_v55 and passou_sell and dir_sell

    def _atualizar_log_inteligente(self):
        qtd_eventos = contar_linhas_csv(CSV_EVENTOS)
        qtd_resultados = contar_linhas_csv(CSV_RESULTADOS)
        ultimo = ler_ultima_linha_csv(CSV_RESULTADOS)

        self.campo_eventos.set(qtd_eventos)
        self.campo_resultados.set(qtd_resultados)

        if ultimo:
            resultado = ultimo.get("resultado") or ultimo.get("resultado_futuro") or ultimo.get("tipo_resultado") or "-"
            pontos = ultimo.get("pontos_resultado") or ultimo.get("pontos") or ultimo.get("resultado_pontos") or "-"
            data_hora = ultimo.get("datahora_resultado") or ultimo.get("datahora_fechamento") or ultimo.get("datahora_execucao") or "-"
            cor = COR_VERDE if str(resultado).lower() in ("take", "win", "ganho") else COR_VERMELHO if str(resultado).lower() in ("stop", "loss", "perda") else COR_TEXTO
            self.campo_ultimo_resultado.set(f"{resultado}   ·   {pontos} pontos   ·   {data_hora}", cor)
        else:
            self.campo_ultimo_resultado.set("nenhum ainda", COR_TEXTO_FRACO)

    def _atualizar_alarme(self, d):
        sinal = str(d.get("sinal", "none")).lower()

        if getattr(self, "_regra_buy", False):
            self.lbl_check_principal.config(
                text="CHECK PRINCIPAL — BUY passou nas probabilidades e direção. Aguardando horário/gestão/sinal oficial.",
                fg=COR_VERDE)
        elif getattr(self, "_regra_sell", False):
            self.lbl_check_principal.config(
                text="CHECK PRINCIPAL — SELL passou nas probabilidades e direção. Aguardando horário/gestão/sinal oficial.",
                fg=COR_VERMELHO)
        else:
            self.lbl_check_principal.config(text="CHECK PRINCIPAL — ainda sem setup completo V7.1.", fg=COR_AMARELO)

        if sinal == "buy":
            self.lbl_alarme.config(text="ALARME — sinal oficial de COMPRA no JSON. Entrada real será confirmada pelo CSV.", fg=COR_VERDE)
        elif sinal == "sell":
            self.lbl_alarme.config(text="ALARME — sinal oficial de VENDA no JSON. Entrada real será confirmada pelo CSV.", fg=COR_VERMELHO)
        else:
            self.lbl_alarme.config(text="ALARME — monitorando… sem sinal oficial.", fg=COR_AMARELO)

        # banner geral grande no topo (junta candle travado + sinal oficial em destaque)
        aviso = str(d.get("aviso_candle_travado") or "").strip()
        if aviso:
            self.banner.config(text=f"⚠  DADOS DESATUALIZADOS  —  {aviso}", bg=COR_AMARELO, fg="#0d1117")
            if not self.banner.winfo_ismapped():
                self.banner.pack(fill="x", padx=16, pady=(10, 6), before=self._canvas_area)
        else:
            if self.banner.winfo_ismapped():
                self.banner.pack_forget()

    def _verificar_entrada_real_csv(self):
        """Espelha 'Verificar-Alarme-CSV' do .ps1: detecta linhas novas com
        motivo == sinal_valido no CSV de log de sinal e toca um alarme sonoro.

        IMPORTANTE — por que isso lê só o "rabo" do arquivo:
        O CSV de log de sinal cresce sem parar e já passa de 100 MB. A versão
        original desta função relia o arquivo INTEIRO a cada 1,5s (pesado, e
        ainda quebrava com UnicodeDecodeError nos trechos antigos gravados em
        outra codificação — ver Bug #9 da skill v71-blackarrow-troubleshooting).
        Em vez disso, guardamos a posição (em bytes) de onde paramos e, a cada
        ciclo, lemos só os bytes adicionados desde então — exatamente como um
        `tail -f`. Isso é rápido (não importa o tamanho do arquivo) e tolera
        bytes inválidos com `errors='replace'`."""
        if not os.path.exists(CSV_LOG_SINAL):
            return

        try:
            tamanho_atual = os.path.getsize(CSV_LOG_SINAL)
        except OSError:
            return

        primeira_vez = self._posicao_csv_sinal is None
        arquivo_recriado = (not primeira_vez) and tamanho_atual < self._posicao_csv_sinal

        if primeira_vez or arquivo_recriado:
            # primeira leitura OU o arquivo encolheu (foi truncado/recriado):
            # só guarda o cabeçalho e a posição atual — não dispara alarme
            # com base no histórico já existente (evita alarme falso ao abrir)
            self._cabecalho_csv_sinal = ler_cabecalho_csv(CSV_LOG_SINAL)
            self._posicao_csv_sinal = tamanho_atual
            return

        if tamanho_atual == self._posicao_csv_sinal:
            return  # nada novo desde o último ciclo

        if not self._cabecalho_csv_sinal:
            # sem cabeçalho conhecido (arquivo apareceu depois de o monitor
            # já estar de pé) — tenta capturar agora e seguir a partir daqui
            self._cabecalho_csv_sinal = ler_cabecalho_csv(CSV_LOG_SINAL)

        try:
            with open(CSV_LOG_SINAL, "rb") as f:
                f.seek(self._posicao_csv_sinal)
                trecho_novo = f.read()
        except OSError:
            return

        self._posicao_csv_sinal = tamanho_atual

        if not self._cabecalho_csv_sinal:
            return  # sem cabeçalho não dá para montar o DictReader corretamente

        texto_novo = trecho_novo.decode("utf-8", errors="replace")
        linhas_texto = [l for l in texto_novo.splitlines() if l.strip()]
        if not linhas_texto:
            return

        leitor = csv.DictReader(linhas_texto, fieldnames=self._cabecalho_csv_sinal, delimiter=";")

        for linha in leitor:
            motivo = linha.get("motivo", "")
            if motivo != "sinal_valido":
                continue

            sinal = str(linha.get("sinal", "")).lower()
            event_id = linha.get("event_id") or f"{linha.get('datahora_execucao')}|{sinal}|{linha.get('preco_close')}"

            if event_id == self._ultimo_alarme_id:
                continue
            self._ultimo_alarme_id = event_id

            if sinal == "buy":
                self._mostrar_alarme_entrada("COMPRA", linha, COR_VERDE)
                self._tocar_som(comprar=True)
            elif sinal == "sell":
                self._mostrar_alarme_entrada("VENDA", linha, COR_VERMELHO)
                self._tocar_som(comprar=False)

    def _mostrar_alarme_entrada(self, tipo, linha, cor):
        texto = (
            f"●  ENTRADA REAL DETECTADA — {tipo}\n"
            f"Data/Hora: {linha.get('datahora_execucao', '-')}      "
            f"Preço: {linha.get('preco_close', '-')}      "
            f"Direção: {linha.get('Direcao', '-')}\n"
            f"Prob V5.1: {linha.get('prob_v51', linha.get('prob_win_v4', '-'))}"
        )
        self.banner.config(text=texto, bg=cor, fg="#0d1117")
        if not self.banner.winfo_ismapped():
            self.banner.pack(fill="x", padx=16, pady=(10, 6), before=self._canvas_area)
        # o banner permanece até o próximo ciclo recalcular o estado (candle travado / sinal oficial)

    def _tocar_som(self, comprar):
        """Toca um alarme sonoro simples e não-bloqueante (thread separada),
        para não travar a interface enquanto o som toca."""
        def _alarme():
            try:
                if comprar:
                    for _ in range(3):
                        winsound.Beep(1400, 150)
                        winsound.Beep(1800, 150)
                        time.sleep(0.25)
                else:
                    for _ in range(3):
                        winsound.Beep(700, 250)
                        winsound.Beep(500, 250)
                        time.sleep(0.25)
            except RuntimeError:
                pass  # ambiente sem suporte a som — ignora silenciosamente

        threading.Thread(target=_alarme, daemon=True).start()


def main():
    root = tk.Tk()
    app = MonitorV71App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
