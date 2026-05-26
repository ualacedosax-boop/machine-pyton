import time
from datetime import datetime

import win32com.client


INTERVALO_SEGUNDOS = 2


def conectar_excel():
    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
        print("Excel aberto encontrado.")
        return excel
    except Exception as e:
        print("Não encontrei Excel aberto.")
        print(e)
        return None


def listar_workbooks(excel):
    print("\n=====================================================")
    print("WORKBOOKS ABERTOS NO EXCEL")
    print("=====================================================")

    try:
        qtd = excel.Workbooks.Count
        print("Quantidade:", qtd)

        if qtd == 0:
            return []

        lista = []

        for i in range(1, qtd + 1):
            wb = excel.Workbooks(i)

            try:
                nome = wb.Name
            except Exception:
                nome = "SEM_NOME"

            try:
                caminho = wb.FullName
            except Exception:
                caminho = ""

            print(f"{i}: {nome} | {caminho}")

            lista.append(wb)

        return lista

    except Exception as e:
        print("Erro ao listar workbooks:")
        print(e)
        return []


def obter_workbook(excel):
    workbooks = listar_workbooks(excel)

    if not workbooks:
        print("\nNenhuma pasta de trabalho encontrada.")
        print("Abra o Excel, clique na planilha do BlackArrow e salve como blackarrow_rtd.xlsx.")
        return None

    # Pega o primeiro workbook aberto
    wb = workbooks[0]

    print("\nWorkbook escolhido:", wb.Name)

    return wb


def listar_abas(wb):
    print("\n=====================================================")
    print("ABAS DO WORKBOOK")
    print("=====================================================")

    abas = []

    try:
        qtd = wb.Worksheets.Count

        for i in range(1, qtd + 1):
            sheet = wb.Worksheets(i)
            print(f"{i}: {sheet.Name}")
            abas.append(sheet)

        return abas

    except Exception as e:
        print("Erro ao listar abas:")
        print(e)
        return []


def obter_sheet(wb):
    abas = listar_abas(wb)

    if not abas:
        return None

    # Pega a primeira aba
    sheet = abas[0]

    print("\nAba escolhida:", sheet.Name)

    return sheet


def ler_tabela(sheet):
    try:
        used = sheet.UsedRange
        valores = used.Value

        if valores is None:
            return []

        if not isinstance(valores, tuple):
            return [[valores]]

        tabela = []

        for linha in valores:
            if isinstance(linha, tuple):
                tabela.append(list(linha))
            else:
                tabela.append([linha])

        return tabela

    except Exception as e:
        print("Erro ao ler tabela:")
        print(e)
        return []


def imprimir_tabela(tabela):
    print("\n=====================================================")
    print("LEITURA:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=====================================================")

    if not tabela:
        print("Tabela vazia.")
        return

    for i, linha in enumerate(tabela, start=1):
        print(f"Linha {i}: {linha}")


def main():
    print("=====================================================")
    print("TESTE LER BLACKARROW RTD VIA EXCEL")
    print("=====================================================")

    excel = conectar_excel()

    if excel is None:
        return

    try:
        excel.Visible = True
    except Exception:
        pass

    wb = obter_workbook(excel)

    if wb is None:
        return

    sheet = obter_sheet(wb)

    if sheet is None:
        return

    while True:
        tabela = ler_tabela(sheet)
        imprimir_tabela(tabela)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()