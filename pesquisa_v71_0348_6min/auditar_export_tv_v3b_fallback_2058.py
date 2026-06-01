from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
DOWNLOADS = Path(r"C:\Users\ualac\Downloads")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_XLSX = SAIDA_DIR / "auditoria_export_tv_v3b_fallback_2058.xlsx"
ARQ_TRADES = SAIDA_DIR / "auditoria_export_tv_v3b_fallback_2058_trades.csv"
ARQ_RESUMO = SAIDA_DIR / "auditoria_export_tv_v3b_fallback_2058_resumo.csv"


def localizar_export():
    if len(sys.argv) > 1:
        caminho = Path(sys.argv[1])
        if caminho.exists():
            return caminho
        raise FileNotFoundError(f"Arquivo informado nao existe: {caminho}")

    padroes = [
        "V71_Pesquisa_Regime_V3B_Fallback_2058_Operavel*.csv",
        "V71 Pesquisa Regime V3B Fallback 2058 Operavel*.csv",
        "*V71*Regime*V3B*Fallback*2058*.csv",
        "*V3B*2058*.csv",
    ]
    encontrados = []
    for padrao in padroes:
        encontrados.extend(DOWNLOADS.glob(padrao))
    if not encontrados:
        raise FileNotFoundError(
            "Nao encontrei export CSV do TradingView para a V3B em Downloads. "
            "Exporte a aba Lista de negociacoes do TV em CSV e rode novamente."
        )
    return max(encontrados, key=lambda p: p.stat().st_mtime)


def ler_csv_tv(csv_path):
    erros = []
    for encoding in ["utf-8-sig", "utf-8", "latin1"]:
        try:
            return pd.read_csv(csv_path, sep=None, engine="python", encoding=encoding)
        except Exception as exc:
            erros.append(f"{encoding}: {exc}")
    raise ValueError("Nao consegui ler o CSV do TradingView. Tentativas: " + " | ".join(erros))


def chave_coluna(nome):
    texto = str(nome).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def numero_tv(valor):
    texto = str(valor).strip()
    if texto == "" or texto.lower() in {"nan", "none"}:
        return np.nan
    texto = re.sub(r"[^0-9,\.\-]", "", texto)
    if texto.count(",") == 1 and texto.count(".") >= 1 and texto.rfind(",") > texto.rfind("."):
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(",") == 1 and texto.count(".") == 0:
        texto = texto.replace(",", ".")
    elif texto.count(".") > 1:
        partes = texto.split(".")
        texto = "".join(partes[:-1]) + "." + partes[-1]
    return pd.to_numeric(texto, errors="coerce")


def parse_data_tv(serie):
    datas = pd.to_datetime(serie, errors="coerce")
    if datas.notna().sum() < max(1, len(serie) // 2):
        datas = pd.to_datetime(serie, errors="coerce", dayfirst=True)
    return datas


def max_drawdown(pnl):
    eq = pnl.astype(float).cumsum()
    if eq.empty:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pnl):
    ganhos = float(pnl[pnl > 0].sum())
    perdas = abs(float(pnl[pnl < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def resumir(df, janela, grupo="TOTAL"):
    if df.empty:
        return {
            "janela": janela,
            "grupo": grupo,
            "trades": 0,
            "takes": 0,
            "stops": 0,
            "winrate": 0.0,
            "pnl_usd": 0.0,
            "pontos_aprox": 0.0,
            "max_drawdown_usd": 0.0,
            "profit_factor": 0.0,
        }
    pnl = df["pnl"].astype(float)
    return {
        "janela": janela,
        "grupo": grupo,
        "trades": int(len(df)),
        "takes": int((pnl > 0).sum()),
        "stops": int((pnl < 0).sum()),
        "winrate": float((pnl > 0).mean() * 100),
        "pnl_usd": float(pnl.sum()),
        "pontos_aprox": float(pnl.sum() / 2.0),
        "max_drawdown_usd": max_drawdown(pnl),
        "profit_factor": profit_factor(pnl),
    }


def normalizar_modulo(sinal):
    s = str(sinal).upper()
    mapa = {
        "D3B0348": "DMI3_0348_BUY",
        "D3B1030": "DMI3_1030_BUY",
        "D3B2058": "DMI3_2058_BUY",
        "D3S1030": "DMI3_1030_SELL",
        "R0346S": "REG_0346_SELL",
        "R0348B": "REG_0348_BUY",
        "R1030S": "REG_1030_SELL",
        "R2052B": "REG_2052_BUY",
        "R2052SA": "REG_2052_SELL_A",
        "R2058B": "REG_2058_BUY",
        "FBB": "FALLBACK_2058_BUY",
        "FBS": "FALLBACK_2058_SELL",
    }
    for chave, modulo in mapa.items():
        if chave in s:
            return modulo
    if "FALLBACK" in s and "BUY" in s:
        return "FALLBACK_2058_BUY"
    if "FALLBACK" in s and "SELL" in s:
        return "FALLBACK_2058_SELL"
    if "BUY" in s:
        return "OUTRO_BUY"
    if "SELL" in s:
        return "OUTRO_SELL"
    return "OUTRO"


def detectar_colunas(df):
    cols = {chave_coluna(c): c for c in df.columns}
    obrigatorias = {
        "tipo": cols.get("tipo"),
        "data": cols.get("data e hora") or cols.get("date time") or cols.get("data hora"),
        "trade": cols.get("trade number") or cols.get("numero da negociacao") or cols.get("n da negociacao"),
        "pnl": cols.get("net pnl usd") or cols.get("lucro liquido usd") or cols.get("resultado liquido usd"),
        "sinal": cols.get("sinal") or cols.get("signal"),
    }
    faltando = [k for k, v in obrigatorias.items() if v is None and k not in {"trade", "sinal"}]
    if faltando:
        raise ValueError(f"Colunas obrigatorias ausentes no CSV do TV: {faltando}. Colunas: {list(df.columns)}")
    return obrigatorias


def consolidar(csv_path):
    df = ler_csv_tv(csv_path)
    c = detectar_colunas(df)
    entradas = df[df[c["tipo"]].astype(str).str.contains("Entrada|Entry", case=False, na=False)].copy()
    entradas["Data e hora"] = parse_data_tv(entradas[c["data"]])
    entradas = entradas.dropna(subset=["Data e hora"])
    if c["trade"]:
        entradas = entradas.sort_values(c["trade"])
    else:
        entradas = entradas.sort_values("Data e hora")
    entradas["pnl"] = entradas[c["pnl"]].map(numero_tv).fillna(0.0)
    entradas["direcao"] = entradas[c["tipo"]].astype(str).str.extract(r"(long|short)", expand=False).map(
        {"long": "BUY", "short": "SELL"}
    )
    sinal_col = c["sinal"]
    entradas["sinal_tv"] = entradas[sinal_col].astype(str) if sinal_col else ""
    entradas["resultado"] = np.where(entradas["pnl"] > 0, "TAKE", "STOP")
    entradas["modulo"] = entradas["sinal_tv"].map(normalizar_modulo)
    entradas["hhmm_execucao"] = entradas["Data e hora"].dt.strftime("%H:%M")
    entradas["dia_semana"] = entradas["Data e hora"].dt.day_name()
    entradas["mes"] = entradas["Data e hora"].dt.to_period("M").astype(str)
    return entradas


def montar_resumo(trades):
    fim = trades["Data e hora"].max()
    linhas = []
    janelas = [
        ("all", trades),
        ("365d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=365)]),
        ("90d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=90)]),
        ("30d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=30)]),
    ]
    for janela, base in janelas:
        linhas.append(resumir(base, janela))
        for modulo, grupo in base.groupby("modulo", dropna=False):
            linhas.append(resumir(grupo, janela, f"modulo={modulo}"))
        for hhmm, grupo in base.groupby("hhmm_execucao", dropna=False):
            linhas.append(resumir(grupo, janela, f"hora={hhmm}"))
        if janela == "all":
            for mes, grupo in base.groupby("mes", dropna=False):
                linhas.append(resumir(grupo, "mes", f"mes={mes}"))
    return pd.DataFrame(linhas)


def checar_alvos(resumo):
    total365 = resumo[(resumo["janela"] == "365d") & (resumo["grupo"] == "TOTAL")]
    if total365.empty:
        return pd.DataFrame()
    row = total365.iloc[0]
    return pd.DataFrame(
        [
            {
                "referencia": "Conservador local",
                "trades_ref": 224,
                "winrate_ref": 86.16,
                "pontos_ref": 6119.5,
                "trades_tv": row["trades"],
                "winrate_tv": row["winrate"],
                "pontos_tv_aprox": row["pontos_aprox"],
                "diff_trades": row["trades"] - 224,
                "diff_winrate": row["winrate"] - 86.16,
            },
            {
                "referencia": "Frequente local",
                "trades_ref": 230,
                "winrate_ref": 85.22,
                "pontos_ref": 5920.0,
                "trades_tv": row["trades"],
                "winrate_tv": row["winrate"],
                "pontos_tv_aprox": row["pontos_aprox"],
                "diff_trades": row["trades"] - 230,
                "diff_winrate": row["winrate"] - 85.22,
            },
        ]
    )


def main():
    csv_path = localizar_export()
    trades = consolidar(csv_path)
    resumo = montar_resumo(trades)
    alvos = checar_alvos(resumo)

    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)
        alvos.to_excel(writer, sheet_name="comparacao_alvos", index=False)

    print("Export analisado:", csv_path)
    print(resumo[resumo["grupo"].eq("TOTAL")].to_string(index=False))
    if not alvos.empty:
        print("\nComparacao com alvos locais:")
        print(alvos.to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)


if __name__ == "__main__":
    main()
