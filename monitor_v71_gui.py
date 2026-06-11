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
janela gráfica de verdade que **atualiza só o texto/cor dos campos que
mudaram**, sem apagar e redesenhar a tela. O resultado: os números mudam no
lugar, sem nenhum piscar.

Visual "moderno" (v3 — agora com customtkinter)
------------------------------------------------
A v2 já tinha trocado o visual "terminal" por um tema escuro tipo painel,
construído 100% em Tkinter puro (na época o pacote `customtkinter` não
instalava por causa de um bloqueio de certificado SSL no pip).

Esta versão (v3) usa o pacote `customtkinter` — uma "casca" sobre o Tkinter
que desenha os widgets com cantos arredondados de verdade, hover suave nos
botões, barra de progresso em pílula nativa e área rolável pronta. O
resultado é um visual ainda mais "estilo app moderno", com bem menos código
manual de desenho (a v2 tinha que desenhar pílulas no Canvas à mão — agora o
próprio `CTkProgressBar` já nasce arredondado).

A paleta continua sendo a "Aurora Dark" (fundo quase-preto azulado, cartões
com borda sutil, acentos em azul/verde/violeta/ciano), só que agora aplicada
através das cores próprias do customtkinter (`fg_color`/`text_color` em vez
de `bg`/`fg`):

  - Cartões com cantos arredondados e uma faixa colorida no topo (acento por
    seção), igual painéis de produtos tipo Notion/Linear/GitHub
  - Selos coloridos tipo "chip/badge" com cantos arredondados para status
    (PASSOU, BUY, SELL, etc.)
  - Barras de progresso em pílula nativas do customtkinter
  - Cartões organizados em **grade de 2 colunas** lado a lado + controle de
    **zoom** ao vivo (ver `_ajustar_zoom`)

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

# Fix: janela transparente no Windows 11 com customtkinter + GPU NVIDIA
# SetProcessDpiAwareness(2) = PROCESS_PER_MONITOR_DPI_AWARE, necessario
# antes de criar qualquer janela tkinter para evitar rendering transparente.
import ctypes as _ctypes
try:
    _ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import tkinter as tk
import customtkinter as ctk

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
# GitHub/Linear/Notion). No customtkinter as cores entram via fg_color
# (fundo) e text_color (texto), em vez de bg/fg do Tkinter puro.
# ============================================================

COR_FUNDO = "#0d1117"          # fundo geral — quase preto, com leve tom azulado
COR_CARTAO = "#161b22"         # fundo dos cartões/seções
COR_CARTAO_CLARO = "#1c2330"   # variação um pouco mais clara (hover, linhas internas)
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

# Tipografia: "Segoe UI" é a fonte nativa e moderna do Windows; "Cascadia
# Mono" é a fonte monoespaçada moderna da Microsoft — reservada para números
# e dados tabulares, onde o alinhamento em colunas importa.
#
# IMPORTANTE — por que isso vira CTkFont (e não tuplas simples):
# tuplas tipo ("Segoe UI", 10) criam uma fonte "anônima" nova toda vez que
# são usadas, então não dá para mudar o tamanho de todo mundo de uma vez.
# CTkFont é o equivalente do customtkinter ao tkfont.Font: um objeto NOMEADO
# e compartilhado — todo widget que aponta para o mesmo objeto muda de
# tamanho instantaneamente quando a gente reconfigura esse objeto. É assim
# que o controle de "zoom" do cabeçalho funciona sem reconstruir a janela.
# Os objetos de verdade só podem ser criados depois que existir uma janela
# CTk (por isso ficam None aqui e são preenchidos em inicializar_fontes()).
TAMANHOS_BASE_FONTE = {
    "FONTE_BASE": ("Segoe UI", 13),
    "FONTE_BASE_NEGRITO": ("Segoe UI Semibold", 13),
    "FONTE_TITULO": ("Segoe UI Semibold", 15),
    "FONTE_GRANDE": ("Segoe UI Semibold", 18),
    "FONTE_PEQUENA": ("Segoe UI", 11),
    "FONTE_MONO": ("Cascadia Mono", 13),
    "FONTE_MONO_PEQUENA": ("Cascadia Mono", 11),
    "FONTE_TITULO_APP": ("Segoe UI Semibold", 24),
    "FONTE_SUBTITULO_APP": ("Segoe UI", 16),
}
# (os tamanhos-base aqui já são um pouco maiores que os da v2 em Tkinter
# puro porque o customtkinter aplica um fator de escala de tela próprio —
# isso é só o ponto de partida do "zoom 100%", ajustável pelo usuário)

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
    CTk) e os publica como globais — assim 'cartao', 'CampoStatus', 'Selo'
    etc. (que referenciam FONTE_BASE etc.) passam a usar objetos
    compartilhados e ajustáveis em tempo real. Retorna o dicionário desses
    objetos, que o app guarda para poder mudar o tamanho (zoom)."""
    global FONTE_BASE, FONTE_BASE_NEGRITO, FONTE_TITULO, FONTE_GRANDE, FONTE_PEQUENA
    global FONTE_MONO, FONTE_MONO_PEQUENA, FONTE_TITULO_APP, FONTE_SUBTITULO_APP

    fontes = {}
    for nome, (familia, tamanho) in TAMANHOS_BASE_FONTE.items():
        fontes[nome] = ctk.CTkFont(family=familia, size=tamanho)

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
# FUNÇÕES UTILITÁRIAS DE LEITURA (espelham a lógica do .ps1 — independem
# de qual biblioteca gráfica está sendo usada, por isso ficam intactas)
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


# NOTA SOBRE O DELIMITADOR: todos os CSVs que o robô grava (eventos,
# resultados e log de sinal) usam VÍRGULA como separador de campo — não
# ponto-e-vírgula. (Isso foi confirmado inspecionando os bytes brutos dos
# arquivos: o cabeçalho de "eventos"/"resultados" tem ~37/~51 vírgulas e
# nenhum ponto-e-vírgula, e o mesmo vale para as linhas de dados do log de
# sinal.) Usamos "utf-8-sig" para já descartar de cara o BOM (﻿) que o
# robô grava no início dos arquivos de eventos/resultados — sem isso, o nome
# da primeira coluna viria com um caractere invisível grudado na frente
# (ex.: "﻿event_id" em vez de "event_id"), quebrando os `.get(...)`.
#
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
        with open(caminho, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            return max(0, sum(1 for _ in csv.reader(f, delimiter=",")) - 1)
    except OSError:
        return 0


def ler_ultima_linha_csv(caminho):
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            leitor = csv.DictReader(f, delimiter=",")
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
        with open(caminho, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            leitor = csv.DictReader(f, delimiter=",")
            return list(leitor)
    except OSError:
        return []


# ============================================================
# WIDGET: barra de progresso em "pílula" — agora é o CTkProgressBar nativo
# do customtkinter (já nasce com pontas arredondadas; não precisamos mais
# desenhar à mão no Canvas como na v2). Só envolvemos numa classinha para
# manter a mesma assinatura `.atualizar(fracao, cor)` usada pelo resto do
# código (e poder trocar a cor de preenchimento conforme passou/não passou).
# ============================================================

class BarraProgresso(ctk.CTkProgressBar):
    def __init__(self, master, largura=230, altura=12):
        super().__init__(master, width=largura, height=altura,
                         corner_radius=altura // 2,
                         fg_color=COR_BARRA_FUNDO, progress_color=COR_VERDE)
        self.set(0.0)

    def atualizar(self, fracao, cor):
        fracao = max(0.0, min(1.0, fracao))
        self.configure(progress_color=cor)
        self.set(fracao)


# ============================================================
# SELO ("chip"/"badge") — texto curto destacado com fundo colorido e
# cantos arredondados de verdade (CTkLabel já suporta corner_radius nativo),
# usado para status como PASSOU / NÃO PASSOU / BUY / SELL / sem dados
# ============================================================

class Selo(ctk.CTkLabel):
    def __init__(self, master, texto="-", **kwargs):
        super().__init__(master, text=f"  {texto}  ", font=FONTE_BASE_NEGRITO,
                         corner_radius=8, height=26, **kwargs)

    def definir(self, texto, cor_fundo, cor_texto="#0d1117"):
        self.configure(text=f"  {texto}  ", fg_color=cor_fundo, text_color=cor_texto)


# ============================================================
# LINHA DE SCORE (nome, valor atual, mínimo, melhor, barra) — widget composto
# ============================================================

class LinhaScore:
    """Uma linha 'Prob V5.1 : 0,613 / min 0,590 | melhor 0,724' com barra
    de progresso em pílula e selo PASSOU/NÃO PASSOU — tudo atualizável no
    lugar, sem recriar widgets a cada ciclo. Usa grid local (dentro de cada
    sub-frame) com `minsize` na 1ª coluna para alinhar os nomes em coluna,
    já que CTkLabel não aceita `width` em "caracteres" como o tk.Label."""

    LARGURA_NOME = 100  # px — aproxima a largura fixa que o tk.Label tinha (width=11)

    def __init__(self, master, nome):
        self.frame = ctk.CTkFrame(master, fg_color=COR_CARTAO)
        self.frame.pack(fill="x", pady=(4, 12))

        linha_topo = ctk.CTkFrame(self.frame, fg_color=COR_CARTAO)
        linha_topo.pack(fill="x")
        linha_topo.grid_columnconfigure(0, minsize=self.LARGURA_NOME)

        self.lbl_nome = ctk.CTkLabel(linha_topo, text=nome, font=FONTE_BASE_NEGRITO,
                                     text_color=COR_TEXTO, anchor="w")
        self.lbl_nome.grid(row=0, column=0, sticky="w")

        self.lbl_valores = ctk.CTkLabel(linha_topo, text="-", font=FONTE_MONO,
                                        text_color=COR_TEXTO_FRACO, anchor="w")
        self.lbl_valores.grid(row=0, column=1, sticky="w", padx=(8, 0))

        linha_barra = ctk.CTkFrame(self.frame, fg_color=COR_CARTAO)
        linha_barra.pack(fill="x", pady=(8, 0))
        linha_barra.grid_columnconfigure(0, minsize=self.LARGURA_NOME)

        self.barra = BarraProgresso(linha_barra)
        self.barra.grid(row=0, column=1, sticky="w", padx=(0, 12))

        self.selo_status = Selo(linha_barra, "-", fg_color=COR_BARRA_FUNDO, text_color=COR_TEXTO_FRACO)
        self.selo_status.grid(row=0, column=2, sticky="w")

        self.lbl_falta = ctk.CTkLabel(linha_barra, text="", font=FONTE_PEQUENA,
                                      text_color=COR_TEXTO_FRACO, anchor="w")
        self.lbl_falta.grid(row=0, column=3, sticky="w", padx=(10, 0))

    def atualizar(self, valor, minimo, melhor):
        valor_f = to_float(valor)
        minimo_f = to_float(minimo)
        melhor_f = to_float(melhor)

        self.lbl_valores.configure(
            text=f"{fmt_num(valor_f, 6)}   ·   mínimo {fmt_num(minimo_f, 3)}   ·   melhor {fmt_num(melhor_f, 6)}"
        )

        if math.isnan(valor_f) or math.isnan(minimo_f) or minimo_f <= 0:
            self.barra.atualizar(0.0, COR_BARRA_FUNDO)
            self.selo_status.definir("SEM DADOS", COR_BARRA_FUNDO, COR_TEXTO_FRACO)
            self.lbl_falta.configure(text="")
            return

        passou = valor_f >= minimo_f
        cor = COR_VERDE if passou else COR_VERMELHO
        fracao = valor_f / minimo_f if minimo_f > 0 else 0.0
        self.barra.atualizar(fracao, cor)

        falta = max(0.0, minimo_f - valor_f)
        if passou:
            self.selo_status.definir("PASSOU", COR_VERDE, "#0d1117")
            self.lbl_falta.configure(text="dentro do mínimo ✓", text_color=COR_VERDE)
        else:
            self.selo_status.definir("NÃO PASSOU", COR_VERMELHO, "#0d1117")
            self.lbl_falta.configure(text=f"falta {fmt_num(falta, 6)}", text_color=COR_TEXTO_FRACO)


# ============================================================
# CAMPO SIMPLES "rótulo : valor" reutilizável, atualizável no lugar.
# Também usa grid+minsize para simular o alinhamento em coluna que o
# parâmetro `width` (em caracteres) dava no tk.Label clássico.
# ============================================================

class CampoStatus:
    def __init__(self, master, rotulo, largura_rotulo=14, fonte_valor=None):
        self.frame = ctk.CTkFrame(master, fg_color=COR_CARTAO)
        self.frame.pack(fill="x", pady=3)

        largura_px = max(96, largura_rotulo * 9)  # ~9px por caractere em Segoe UI 13pt
        self.frame.grid_columnconfigure(0, minsize=largura_px)

        ctk.CTkLabel(self.frame, text=rotulo, font=FONTE_BASE, text_color=COR_TEXTO_FRACO,
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.valor_lbl = ctk.CTkLabel(self.frame, text="-", font=(fonte_valor or FONTE_BASE_NEGRITO),
                                      text_color=COR_TEXTO, anchor="w")
        self.valor_lbl.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def set(self, texto, cor=None):
        self.valor_lbl.configure(text=str(texto), text_color=(cor or COR_TEXTO))


# ============================================================
# CARTÃO DE SEÇÃO — bloco estilo "painel moderno": cantos arredondados de
# verdade (corner_radius nativo do CTkFrame), borda fina e uma faixa
# colorida no topo. Substitui o "cartão" desenhado à mão na v2 com
# tk.Frame + highlightthickness (que só conseguia cantos retos).
# ============================================================

def cartao(master, titulo, icone="", cor_acento=None):
    """Monta um 'cartão' (moldura arredondada + faixa colorida + título) mas
    DELIBERADAMENTE não se posiciona sozinho — quem chama decide se ele fica
    empilhado (.pack) ou lado a lado (.grid), o que é o que permite organizar
    os cartões em colunas. Devolve (moldura, corpo): "moldura" é o que vai
    para o gerenciador de geometria do chamador, "corpo" é onde o conteúdo
    da seção deve ser montado."""
    cor_acento = cor_acento or COR_TITULO

    moldura = ctk.CTkFrame(master, fg_color=COR_CARTAO, corner_radius=14,
                           border_width=1, border_color=COR_BORDA)

    faixa = ctk.CTkFrame(moldura, fg_color=cor_acento, height=4, corner_radius=10)
    faixa.pack(fill="x", side="top", padx=16, pady=(16, 0))

    corpo = ctk.CTkFrame(moldura, fg_color=COR_CARTAO, corner_radius=0)
    corpo.pack(fill="both", expand=True, padx=22, pady=(14, 20))

    cabecalho = ctk.CTkFrame(corpo, fg_color=COR_CARTAO)
    cabecalho.pack(fill="x", pady=(0, 14))
    texto_titulo = f"{icone}   {titulo}" if icone else titulo
    ctk.CTkLabel(cabecalho, text=texto_titulo, font=FONTE_TITULO, text_color=COR_TEXTO,
                 anchor="w").pack(side="left")

    return moldura, corpo


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================

class MonitorV71App:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor V7.1 — BlackArrow")
        self.root.configure(fg_color=COR_FUNDO)
        # janela "wide": os cartões ficam lado a lado em duas colunas
        self.root.geometry("1220x880")
        self.root.minsize(800, 580)

        # ---- zoom: usamos a ESCALA NATIVA do customtkinter (set_widget_scaling),
        # não apenas o tamanho da fonte. Ela redimensiona, de uma vez e ao vivo,
        # TUDO que compõe a "proporção" de cada widget — largura, altura, cantos
        # arredondados, espessura de borda e até os espaçamentos padx/pady de
        # quem usa .pack()/.grid() — além do tamanho das fontes CTkFont. Por
        # isso, ao dar zoom out, os cartões/barras/selos encolhem junto com o
        # texto (em vez de só o texto encolher e sobrar espaço vazio em volta).
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
        self._ultimo_alarme_id = None        # evita repetir o mesmo alarme (sinal/hora/preço)
        self._alarme_ts = None               # timestamp (time.time()) do último alarme disparado
        self._alarme_banner_duracao = 300    # segundos que o banner de alarme permanece visível (5 min)
        self._ultimo_alarme_json_id = None   # deduplicação do alarme baseado no JSON

        self._montar_interface()
        self._agendar_atualizacao(imediata=True)

    # --------------------------------------------------------
    # MONTAGEM DA INTERFACE (uma vez só — depois só atualizamos texto/cor)
    # --------------------------------------------------------
    def _montar_interface(self):
        LARGURA_TEXTO_LARGO = 940     # quebra de linha p/ textos que ocupam as 2 colunas
        LARGURA_TEXTO_ESTREITO = 440  # quebra de linha p/ textos de cartão de 1 coluna

        # --- cabeçalho estilo "topo de painel" ---
        cab = ctk.CTkFrame(self.root, fg_color=COR_FUNDO)
        cab.pack(fill="x", padx=22, pady=(18, 12))

        linha_titulo = ctk.CTkFrame(cab, fg_color=COR_FUNDO)
        linha_titulo.pack(fill="x", anchor="w")

        # "ponto" indicador de saúde do monitor — agora é um CTkLabel circular
        # (corner_radius = metade da largura/altura = círculo perfeito),
        # bem mais simples que desenhar um círculo no Canvas como na v2
        self.indicador = ctk.CTkLabel(linha_titulo, text="", width=14, height=14,
                                      corner_radius=7, fg_color=COR_VERDE)
        self.indicador.pack(side="left", padx=(2, 12))

        ctk.CTkLabel(linha_titulo, text="Monitor V7.1", font=FONTE_TITULO_APP,
                     text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(linha_titulo, text="  ·  BlackArrow Oficial", font=FONTE_SUBTITULO_APP,
                     text_color=COR_TEXTO_FRACO).pack(side="left")

        # ---- controle de ZOOM (deixa tudo menor/maior para caber mais na tela) ----
        zoom_box = ctk.CTkFrame(linha_titulo, fg_color=COR_FUNDO)
        zoom_box.pack(side="right")

        ctk.CTkLabel(zoom_box, text="Zoom", font=FONTE_PEQUENA,
                     text_color=COR_TEXTO_FRACO).pack(side="left", padx=(0, 8))

        def _botao_zoom(texto, comando):
            return ctk.CTkButton(zoom_box, text=texto, width=36, height=30, corner_radius=8,
                                 fg_color=COR_CARTAO, hover_color=COR_CARTAO_CLARO,
                                 text_color=COR_TEXTO, border_width=1, border_color=COR_BORDA,
                                 font=FONTE_BASE_NEGRITO, command=comando)

        btn_zoom_menos = _botao_zoom("－", lambda: self._ajustar_zoom(-ZOOM_PASSO))
        btn_zoom_menos.pack(side="left", padx=(0, 6))
        btn_zoom_menos.bind("<Double-Button-1>", lambda e: self._ajustar_zoom(reset=True))

        self.lbl_zoom = ctk.CTkLabel(zoom_box, text="100%", font=FONTE_BASE_NEGRITO,
                                     text_color=COR_TEXTO_FRACO, width=48, anchor="center")
        self.lbl_zoom.pack(side="left")

        btn_zoom_mais = _botao_zoom("＋", lambda: self._ajustar_zoom(ZOOM_PASSO))
        btn_zoom_mais.pack(side="left", padx=(6, 0))
        btn_zoom_mais.bind("<Double-Button-1>", lambda e: self._ajustar_zoom(reset=True))

        # atalhos de teclado: Ctrl + roda do mouse, Ctrl +/-/0 (como em navegadores)
        self.root.bind_all("<Control-MouseWheel>", self._zoom_pelo_mouse)
        self.root.bind_all("<Control-plus>", lambda e: self._ajustar_zoom(ZOOM_PASSO))
        self.root.bind_all("<Control-equal>", lambda e: self._ajustar_zoom(ZOOM_PASSO))
        self.root.bind_all("<Control-minus>", lambda e: self._ajustar_zoom(-ZOOM_PASSO))
        self.root.bind_all("<Control-Key-0>", lambda e: self._ajustar_zoom(reset=True))

        self.lbl_atualizacao = ctk.CTkLabel(cab, text="Atualização: -", font=FONTE_BASE,
                                            text_color=COR_TEXTO_FRACO, anchor="w")
        self.lbl_atualizacao.pack(anchor="w", pady=(8, 0))

        # detalhes técnicos (caminhos) — escondidos por padrão, expansível
        self._fontes_visiveis = tk.BooleanVar(value=False)
        self.btn_fontes = ctk.CTkLabel(cab, text="▸ mostrar fontes de dados  ·  dica: Ctrl + roda do mouse para dar zoom",
                                       font=FONTE_PEQUENA, text_color=COR_TEXTO_FRACO,
                                       anchor="w", cursor="hand2")
        self.btn_fontes.pack(anchor="w", pady=(10, 0))
        self.btn_fontes.bind("<Button-1>", self._alternar_fontes)
        self.lbl_fontes = ctk.CTkLabel(cab, text="", font=FONTE_MONO_PEQUENA,
                                       text_color=COR_TEXTO_FRACO, justify="left", anchor="w")
        # só é exibido quando o usuário clicar em "mostrar fontes de dados"

        # linha divisória sutil sob o cabeçalho
        ctk.CTkFrame(self.root, fg_color=COR_BORDA, height=1, corner_radius=0).pack(fill="x")

        # ---- BANNER DE ALARME — fica FIXO logo abaixo do cabeçalho (fora da
        # área rolável), assim continua visível mesmo se o usuário rolar a
        # tela para baixo para ver outros cartões. CTkLabel não tem padx/pady
        # internos, então usamos um CTkFrame por fora para dar "respiro" ao
        # texto e manter os cantos arredondados. ----
        self.banner_moldura = ctk.CTkFrame(self.root, fg_color=COR_CARTAO, corner_radius=12)
        self.banner = ctk.CTkLabel(self.banner_moldura, text="", font=FONTE_GRANDE,
                                   text_color="#0d1117", fg_color=COR_CARTAO,
                                   anchor="w", justify="left", wraplength=LARGURA_TEXTO_LARGO)
        self.banner.pack(fill="both", expand=True, padx=20, pady=16)
        # só faz .pack() na MOLDURA quando houver algo a mostrar (ver
        # _atualizar_alarme/_mostrar_alarme_entrada/_mostrar_banner)

        # --- área rolável: CTkScrollableFrame já cuida do canvas + scrollbar +
        # rolagem pelo mouse internamente — bem mais simples que montar isso
        # manualmente como na v2. Os cartões ficam em GRADE DE 2 COLUNAS lado
        # a lado, para aproveitar telas largas e mostrar mais coisa de uma vez
        # (em vez da pilha vertical única que obrigava a rolar muito) ---
        self.area = ctk.CTkScrollableFrame(self.root, fg_color=COR_FUNDO,
                                            scrollbar_button_color=COR_BORDA,
                                            scrollbar_button_hover_color=COR_TITULO)
        self.area.pack(fill="both", expand=True, padx=4)

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

        grade = ctk.CTkFrame(bloco, fg_color=COR_CARTAO)
        grade.pack(fill="x")
        col_esq = ctk.CTkFrame(grade, fg_color=COR_CARTAO)
        col_esq.pack(side="left", fill="both", expand=True, anchor="n")
        col_dir = ctk.CTkFrame(grade, fg_color=COR_CARTAO)
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
        self.aviso_moldura = ctk.CTkFrame(bloco, fg_color=COR_AMARELO, corner_radius=10)
        self.aviso_candle = ctk.CTkLabel(self.aviso_moldura, text="", font=FONTE_BASE_NEGRITO,
                                         text_color="#0d1117", fg_color=COR_AMARELO,
                                         anchor="w", justify="left", wraplength=LARGURA_TEXTO_LARGO)
        self.aviso_candle.pack(fill="both", expand=True, padx=14, pady=12)
        # só faz .pack (na moldura) quando houver aviso

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

        ctk.CTkFrame(bloco, fg_color=COR_BORDA, height=1, corner_radius=0).pack(fill="x", pady=12)
        self.lbl_regra_buy = ctk.CTkLabel(bloco, text="Regra BUY  ·  V5.1 ≥ 0,590 + V5.5 ≥ 0,425 + BUY ≥ 0,74 + Direção BUY + horário/gestão",
                                          font=FONTE_PEQUENA, text_color=COR_TEXTO_FRACO,
                                          anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_regra_buy.pack(fill="x")
        self.lbl_regra_sell = ctk.CTkLabel(bloco, text="Regra SELL  ·  V5.1 ≥ 0,590 + V5.5 ≥ 0,425 + SELL ≥ 0,50 + Direção SELL + horário/gestão",
                                           font=FONTE_PEQUENA, text_color=COR_TEXTO_FRACO,
                                           anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_regra_sell.pack(fill="x", pady=(4, 0))
        linha_grade += 1

        # ---- linha 4: Log inteligente (col. esquerda) | Status do alarme (col. direita) ----
        moldura, bloco = cartao(self.area, "Log inteligente", "▤", ACENTO_LOG)
        moldura.grid(row=linha_grade, column=0, sticky="nsew", **PAD)
        self.campo_eventos = CampoStatus(bloco, "Eventos registrados", largura_rotulo=18, fonte_valor=FONTE_MONO)
        self.campo_resultados = CampoStatus(bloco, "Resultados fechados", largura_rotulo=18, fonte_valor=FONTE_MONO)
        self.campo_ultimo_resultado = CampoStatus(bloco, "Último resultado", largura_rotulo=18)

        moldura, bloco = cartao(self.area, "Status do alarme", "⚑", ACENTO_ALARME)
        moldura.grid(row=linha_grade, column=1, sticky="nsew", **PAD)
        self.lbl_check_principal = ctk.CTkLabel(bloco, text="-", font=FONTE_BASE, text_color=COR_AMARELO,
                                                 anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_check_principal.pack(fill="x", pady=4)
        self.lbl_alarme = ctk.CTkLabel(bloco, text="-", font=FONTE_BASE, text_color=COR_AMARELO,
                                       anchor="w", justify="left", wraplength=LARGURA_TEXTO_ESTREITO)
        self.lbl_alarme.pack(fill="x", pady=4)
        linha_grade += 1

        # espaço extra no fim da área rolável
        ctk.CTkFrame(self.area, fg_color=COR_FUNDO, height=14).grid(row=linha_grade, column=0, columnspan=2)

        # ---- rodapé ----
        ctk.CTkFrame(self.root, fg_color=COR_BORDA, height=1, corner_radius=0).pack(fill="x")
        rodape = ctk.CTkFrame(self.root, fg_color=COR_FUNDO)
        rodape.pack(fill="x", padx=22, pady=12)
        self.lbl_status_geral = ctk.CTkLabel(rodape, text="iniciando…", font=FONTE_PEQUENA,
                                             text_color=COR_TEXTO_FRACO, anchor="w")
        self.lbl_status_geral.pack(side="left")

    # --------------------------------------------------------
    # ZOOM — usa a ESCALA NATIVA do customtkinter (set_widget_scaling) em vez
    # de só mudar o tamanho das fontes. Isso é o que faz o zoom out encolher
    # a PROPORÇÃO dos cartões/barras/selos junto com o texto, e não deixar
    # espaço vazio sobrando ao redor de um texto menor (ver explicação maior
    # junto da definição de self._fator_zoom, no __init__).
    # --------------------------------------------------------
    def _ajustar_zoom(self, delta=0.0, reset=False):
        novo_fator = 1.0 if reset else round(self._fator_zoom + delta, 2)
        novo_fator = max(ZOOM_MINIMO, min(ZOOM_MAXIMO, novo_fator))
        if novo_fator == self._fator_zoom:
            return
        self._fator_zoom = novo_fator

        ctk.set_widget_scaling(self._fator_zoom)

        self.lbl_zoom.configure(text=f"{round(self._fator_zoom * 100)}%")

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
            self.btn_fontes.configure(text="▾ ocultar fontes de dados")
            self.lbl_fontes.pack(anchor="w", pady=(6, 0))
        else:
            self.btn_fontes.configure(text="▸ mostrar fontes de dados  ·  dica: Ctrl + roda do mouse para dar zoom")
            self.lbl_fontes.pack_forget()

    # --------------------------------------------------------
    # BANNER DE ALARME — mostra/oculta a moldura arredondada fixa logo
    # abaixo do cabeçalho (ver _montar_interface). Centralizar aqui evita
    # repetir a lógica de "antes de qual widget" em dois lugares.
    # --------------------------------------------------------
    def _mostrar_banner(self, texto, cor_fundo, cor_texto="#0d1117"):
        self.banner_moldura.configure(fg_color=cor_fundo)
        self.banner.configure(text=texto, fg_color=cor_fundo, text_color=cor_texto)
        try:
            if not self.banner_moldura.winfo_ismapped():
                self.banner_moldura.pack(fill="x", padx=18, pady=(12, 6), before=self.area)
        except Exception:
            pass

    def _ocultar_banner(self):
        try:
            if self.banner_moldura.winfo_ismapped():
                self.banner_moldura.pack_forget()
        except Exception:
            pass

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
            self.indicador.configure(fg_color=COR_VERDE)
            self.lbl_status_geral.configure(
                text=f"Última leitura OK às {datetime.now().strftime('%H:%M:%S')}  ·  atualizando a cada {INTERVALO_ATUALIZACAO_MS/1000:.1f}s",
                text_color=COR_TEXTO_FRACO)
        except Exception as exc:  # nunca deixa o loop morrer por um erro pontual de leitura
            self.indicador.configure(fg_color=COR_AMARELO)
            self.lbl_status_geral.configure(text=f"Aviso: erro ao atualizar ({exc})", text_color=COR_AMARELO)
        finally:
            self._agendar_atualizacao()

    def _atualizar_tudo(self):
        caminho_json = localizar_json()
        self.lbl_fontes.configure(
            text=(f"JSON do robô :  {caminho_json}\n"
                  f"CSV de sinal :  {CSV_LOG_SINAL}\n"
                  f"Eventos      :  {CSV_EVENTOS}\n"
                  f"Resultados   :  {CSV_RESULTADOS}")
        )
        self.lbl_atualizacao.configure(text=f"Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not os.path.exists(caminho_json):
            self.indicador.configure(fg_color=COR_VERMELHO)
            self.lbl_check_principal.configure(text="ERRO: JSON não encontrado — verifique se o robô está rodando.", text_color=COR_VERMELHO)
            return

        dados = ler_json_seguro(caminho_json)
        if dados is None:
            self.indicador.configure(fg_color=COR_VERMELHO)
            self.lbl_check_principal.configure(text="ERRO: não foi possível ler o JSON (tente de novo no próximo ciclo).", text_color=COR_VERMELHO)
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
        try:
            if aviso:
                self.aviso_candle.configure(text=f"⚠  DADOS DESATUALIZADOS — {aviso}\n     Verifique o exportador Excel (exportar_blackarrow_excel_v71.ps1)")
                if not self.aviso_moldura.winfo_ismapped():
                    self.aviso_moldura.pack(fill="x", pady=(14, 0))
            else:
                if self.aviso_moldura.winfo_ismapped():
                    self.aviso_moldura.pack_forget()
        except Exception:
            pass

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

    def _alarme_recente(self):
        """Retorna True se um alarme de entrada foi disparado nos últimos _alarme_banner_duracao segundos."""
        if self._alarme_ts is None:
            return False
        return (time.time() - self._alarme_ts) < self._alarme_banner_duracao

    def _atualizar_alarme(self, d):
        import time as _time
        sinal = str(d.get("sinal", "none")).lower()
        motivo = str(d.get("motivo", "")).strip()

        if getattr(self, "_regra_buy", False):
            self.lbl_check_principal.configure(
                text="CHECK PRINCIPAL — BUY passou nas probabilidades e direção. Aguardando horário/gestão/sinal oficial.",
                text_color=COR_VERDE)
        elif getattr(self, "_regra_sell", False):
            self.lbl_check_principal.configure(
                text="CHECK PRINCIPAL — SELL passou nas probabilidades e direção. Aguardando horário/gestão/sinal oficial.",
                text_color=COR_VERMELHO)
        else:
            self.lbl_check_principal.configure(text="CHECK PRINCIPAL — ainda sem setup completo V7.1.", text_color=COR_AMARELO)

        if sinal == "buy":
            self.lbl_alarme.configure(text="ALARME — sinal oficial de COMPRA no JSON. Entrada real será confirmada pelo CSV.", text_color=COR_VERDE)
        elif sinal == "sell":
            self.lbl_alarme.configure(text="ALARME — sinal oficial de VENDA no JSON. Entrada real será confirmada pelo CSV.", text_color=COR_VERMELHO)
        else:
            self.lbl_alarme.configure(text="ALARME — monitorando… sem sinal oficial.", text_color=COR_AMARELO)

        # --- Alarme sonoro baseado no JSON ---
        # Caminho 1: motivo == "sinal_valido" — janela curta (1-2s), pode ser perdida pelo poll.
        # Caminho 2: motivo == "sinal_ja_enviado_neste_candle" — persiste o candle inteiro,
        #            100% confiavel. Usa candle_sp + direcao como chave de deduplicacao.
        if motivo == "sinal_valido" and sinal in ("buy", "sell"):
            event_id_json = str(d.get("event_id", "")) or (
                f"{d.get('datahora_execucao','')}|{sinal}|{d.get('preco_close','')}"
            )
            if event_id_json != self._ultimo_alarme_json_id:
                self._ultimo_alarme_json_id = event_id_json
                self._alarme_ts = _time.time()
                registro = {
                    "datahora_execucao": str(d.get("datahora_execucao", "-")),
                    "preco_close":       str(d.get("preco_close", "-")),
                    "Direcao":           sinal.upper(),
                }
                tipo = "COMPRA" if sinal == "buy" else "VENDA"
                cor  = COR_VERDE if sinal == "buy" else COR_VERMELHO
                self._mostrar_alarme_entrada(tipo, registro, cor)
                self._tocar_som(comprar=(sinal == "buy"))

        elif motivo == "sinal_ja_enviado_neste_candle":
            # Backup: captura o alarme mesmo que sinal_valido tenha sido perdido pelo poll.
            direcao = str(d.get("Direcao", "")).strip().lower()
            candle_sp = str(d.get("datahora_ultimo_candle_sp", "")).strip()
            if direcao in ("buy", "sell") and candle_sp:
                event_id_backup = f"enviado|{candle_sp}|{direcao}"
                if event_id_backup != self._ultimo_alarme_json_id:
                    self._ultimo_alarme_json_id = event_id_backup
                    self._alarme_ts = _time.time()
                    registro = {
                        "datahora_execucao": str(d.get("datahora_execucao", "-")),
                        "preco_close":       str(d.get("preco_close", "-")),
                        "Direcao":           direcao.upper(),
                    }
                    tipo = "COMPRA" if direcao == "buy" else "VENDA"
                    cor  = COR_VERDE if direcao == "buy" else COR_VERMELHO
                    self._mostrar_alarme_entrada(tipo, registro, cor)
                    self._tocar_som(comprar=(direcao == "buy"))

        # --- Banner de dados desatualizados (candle travado) ---
        # Só oculta o banner se NÃO houver alarme de entrada ativo.
        aviso = str(d.get("aviso_candle_travado") or "").strip()
        if aviso:
            self._mostrar_banner(f"⚠  DADOS DESATUALIZADOS  —  {aviso}", COR_AMARELO, "#0d1117")
        elif not self._alarme_recente():
            # sem alarme ativo e sem dados desatualizados → oculta banner
            self._ocultar_banner()

    def _verificar_entrada_real_csv(self):
        """Lê os últimos 200 KB do CSV de log de sinal a cada ciclo e dispara
        alarme para qualquer linha sinal_valido com timestamp nos últimos 5 min.

        Leitura pelo rabo do arquivo (seek para tamanho-200KB): o log passa de
        100 MB e não faz sentido reler tudo. 200 KB cobre folga os ~5 minutos
        mesmo na pior taxa de escrita (~500 bytes/linha × 2 linhas/s = 600 KB/min).

        A janela de 5 minutos garante que o alarme dispara mesmo se o monitor
        foi reiniciado ou perdeu um ciclo — sem depender de controle de posição.

        Campos por posição (o cabeçalho do arquivo está defasado em relação às
        ~70 colunas gravadas hoje, então não usamos DictReader):
            índice 2 = sinal ("buy"/"sell")
            índice 3 = motivo
            índice 5 = datahora_execucao  ("YYYY-MM-DD HH:MM:SS")
            índice 8 = preco_close
        """
        if not os.path.exists(CSV_LOG_SINAL):
            return

        JANELA_BYTES   = 200 * 1024   # 200 KB — cobre ~5 min de linhas
        JANELA_SEGUNDOS = 5 * 60      # ignora linhas com mais de 5 min

        try:
            tamanho = os.path.getsize(CSV_LOG_SINAL)
            inicio  = max(0, tamanho - JANELA_BYTES)
            with open(CSV_LOG_SINAL, "rb") as f:
                f.seek(inicio)
                trecho = f.read()
        except OSError:
            return

        agora = datetime.now()
        texto = trecho.decode("utf-8", errors="replace")

        for linha_bruta in texto.splitlines():
            linha_bruta = linha_bruta.strip()
            if not linha_bruta or ",sinal_valido," not in linha_bruta:
                continue

            campos = linha_bruta.split(",")
            if len(campos) < 9:
                continue

            sinal  = campos[2].strip().lower()
            motivo = campos[3].strip()
            if motivo != "sinal_valido" or sinal not in ("buy", "sell"):
                continue

            datahora_execucao = campos[5].strip()
            preco_close       = campos[8].strip()

            # Descarta linhas fora da janela de 5 minutos
            try:
                ts = datetime.strptime(datahora_execucao, "%Y-%m-%d %H:%M:%S")
                if (agora - ts).total_seconds() > JANELA_SEGUNDOS:
                    continue
            except (ValueError, TypeError):
                continue

            event_id = f"{datahora_execucao}|{sinal}|{preco_close}"
            if event_id == self._ultimo_alarme_id:
                continue
            self._ultimo_alarme_id = event_id

            registro = {
                "datahora_execucao": datahora_execucao,
                "preco_close":       preco_close,
                "Direcao":           sinal.upper(),
            }

            if sinal == "buy":
                self._mostrar_alarme_entrada("COMPRA", registro, COR_VERDE)
                self._tocar_som(comprar=True)
            else:
                self._mostrar_alarme_entrada("VENDA", registro, COR_VERMELHO)
                self._tocar_som(comprar=False)

    def _mostrar_alarme_entrada(self, tipo, linha, cor):
        import time as _time
        texto = (
            f"●  ENTRADA REAL DETECTADA — {tipo}\n"
            f"Data/Hora: {linha.get('datahora_execucao', '-')}      "
            f"Preço: {linha.get('preco_close', '-')}      "
            f"Direção: {linha.get('Direcao', '-')}"
        )
        self._alarme_ts = _time.time()   # registra quando disparou para manter o banner visível
        self._mostrar_banner(texto, cor, "#0d1117")

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
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    app = MonitorV71App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
