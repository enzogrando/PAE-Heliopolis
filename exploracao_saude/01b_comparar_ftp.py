"""Tarefa 1 (complemento): compara o catálogo do PySUS com o FTP oficial do DATASUS.

Só lista nomes de arquivos do FTP, sem baixar nada. Mostra até que mês o DATASUS publicou
e quais meses do estudo existem no FTP mas faltam no espelho do PySUS.
"""
import ftplib
import re
from pathlib import Path

import pandas as pd

PASTA = "/dissemin/publicos/SIHSUS/200801_/Dados/"
SAIDA = Path(__file__).parent / "saidas"


def listar_ftp():
    ftp = ftplib.FTP("ftp.datasus.gov.br", timeout=60)
    ftp.login()
    linhas = []
    ftp.retrlines("LIST " + PASTA, linhas.append)
    ftp.quit()
    registros = []
    for linha in linhas:
        achado = re.search(r"(\d+) (RDSP(\d\d)(\d\d)\.dbc)$", linha, re.I)
        if achado:
            registros.append({"arquivo": achado[2], "ano": 2000 + int(achado[3]),
                              "mes": int(achado[4]), "tamanho_mb": int(achado[1]) / 1e6})
    return pd.DataFrame(registros).sort_values(["ano", "mes"])


def main():
    ftp = listar_ftp()
    ftp.to_csv(SAIDA / "01b_arquivos_ftp_sp.csv", index=False, sep=";")
    estudo = ftp[(ftp.ano >= 2021) & (ftp.ano <= 2025)]
    mirror = pd.read_csv(SAIDA / "01_arquivos_sih_sp.csv", sep=";")
    no_mirror = set(zip(mirror.ano, mirror.mes))
    print(f"FTP: {len(estudo)} de 60 meses do estudo; {estudo.tamanho_mb.sum():,.0f} MB (.dbc compactado).")
    print(f"Último mês publicado no FTP: {ftp.ano.iloc[-1]}-{ftp.mes.iloc[-1]:02d}")
    print("Meses do estudo no FTP mas ausentes no espelho do PySUS:",
          [(a, m) for a, m in zip(estudo.ano, estudo.mes) if (a, m) not in no_mirror])


if __name__ == "__main__":
    main()
