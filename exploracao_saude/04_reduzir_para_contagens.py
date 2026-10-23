"""Tarefas 4 e 5: baixa o SIH de SP mês a mês, reduz cada arquivo a contagens e apaga o bruto.

Para cada arquivo (competência) ele guarda em saidas/reduzidos/AAAA-MM.csv apenas:
    competencia, data_internacao, letra_cid, faixa_etaria, ident, hospital_na_capital, n
(somente pacientes RESIDENTES na capital, MUNIC_RES = 355030) mais uma linha de totais em
saidas/04_totais_por_arquivo.csv. Nenhum CEP, nome de coluna sensível ou linha individual é mantido.

Fonte de cada mês: espelho Parquet do PySUS quando existe; senão, o .dbc do FTP do DATASUS
convertido com pyreaddbc (8 meses do estudo não estão no espelho).
Reexecutar pula os meses já reduzidos. Uso: .venv\\Scripts\\python.exe 04_reduzir_para_contagens.py
"""
import os
from pathlib import Path

AQUI = Path(__file__).parent
# Deve ser definido ANTES de importar o pysus: mantém o cache dentro desta pasta e sem barras de progresso.
os.environ["PYSUS_CACHE_PATH"] = str(AQUI / "cache")
os.environ["PYSUS_PROGRESS_BARS"] = "false"

import asyncio
import ftplib
import time

import pandas as pd
from dbfread import DBF
from pyreaddbc import dbc2dbf
from pysus.api.client import PySUS

SAIDA = AQUI / "saidas"
REDUZIDOS = SAIDA / "reduzidos"
CACHE = AQUI / "cache"
PASTA_FTP = "/dissemin/publicos/SIHSUS/200801_/Dados/"
SP_CAPITAL = "355030"
CAMPOS = ["IDENT", "DT_INTER", "DIAG_PRINC", "MUNIC_RES", "MUNIC_MOV", "IDADE", "COD_IDADE"]
# Competências 2021-01 a 2026-08 (o DATASUS publicou até 2026-08). Os meses de 2026 servem para
# completar as internações de 2025, que chegam com atraso.
MESES = [(a, m) for a in range(2021, 2027) for m in range(1, 13) if (a, m) <= (2026, 8)]


def faixa_etaria(idade, cod):
    """Agrupa a idade: COD_IDADE 4 = anos, 5 = 100 anos ou mais, 1/2/3 = horas, dias, meses (menos de 1 ano)."""
    anos = pd.to_numeric(idade, errors="coerce")
    anos = anos.mask(cod == "5", 100 + anos).where(cod.isin(["4", "5"]), 0)
    faixa = pd.cut(anos, [-1, 14, 64, 200], labels=["0-14", "15-64", "65+"])
    return faixa.astype(object).where(anos.notna(), "sem idade")


def reduzir(df, ano, mes):
    """Transforma a tabela de internações em contagens e devolve (contagens, totais)."""
    totais = {"competencia": f"{ano}-{mes:02d}", "linhas_no_arquivo": len(df),
              "linhas_residentes_capital": int((df.MUNIC_RES == SP_CAPITAL).sum())}
    res = df[df.MUNIC_RES == SP_CAPITAL].copy()
    res["faixa_etaria"] = faixa_etaria(res.IDADE, res.COD_IDADE)
    res["letra_cid"] = res.DIAG_PRINC.fillna("").str[:1].replace("", "?")
    res["hospital_na_capital"] = res.MUNIC_MOV == SP_CAPITAL
    contagens = (res.groupby(["DT_INTER", "letra_cid", "faixa_etaria", "IDENT", "hospital_na_capital"], observed=True)
                 .size().rename("n").reset_index()
                 .rename(columns={"DT_INTER": "data_internacao", "IDENT": "ident"}))
    contagens.insert(0, "competencia", f"{ano}-{mes:02d}")
    return contagens, totais


def ler_dbc(caminho_dbc):
    """Converte o .dbc em .dbf e lê só as colunas necessárias."""
    dbf = caminho_dbc.with_suffix(".dbf")
    dbc2dbf(str(caminho_dbc), str(dbf))
    tabela = pd.DataFrame(({c: r[c] for c in CAMPOS} for r in DBF(str(dbf), encoding="latin-1", load=False)))
    dbf.unlink()
    return tabela.astype(str).apply(lambda s: s.str.strip())


def baixar_ftp(ano, mes):
    nome = f"RDSP{str(ano)[2:]}{mes:02d}.dbc"
    destino = CACHE / nome
    ftp = ftplib.FTP("ftp.datasus.gov.br", timeout=120)
    ftp.login()
    with open(destino, "wb") as f:
        ftp.retrbinary(f"RETR {PASTA_FTP}{nome}", f.write)
    ftp.quit()
    return destino


async def processar():
    CACHE.mkdir(exist_ok=True)
    REDUZIDOS.mkdir(parents=True, exist_ok=True)
    async with PySUS() as p:
        catalogo = {(int(a.name[4:6]) + 2000, int(a.name[6:8])): a
                    for a in await p.query(dataset="SIH", group="RD", state="SP")}
        for ano, mes in MESES:
            saida = REDUZIDOS / f"{ano}-{mes:02d}.csv"
            if saida.exists():
                continue
            inicio = time.time()
            if (ano, mes) in catalogo:
                origem = "espelho Parquet"
                local = Path((await p.download(catalogo[(ano, mes)])).path)
                tabela = pd.read_parquet(local, columns=CAMPOS)
            else:
                origem = "FTP .dbc"
                local = baixar_ftp(ano, mes)
                tabela = ler_dbc(local)
            baixado_mb = local.stat().st_size / 1e6
            contagens, totais = reduzir(tabela, ano, mes)
            local.unlink()
            contagens.to_csv(saida, index=False)
            totais.update(origem=origem, mb_baixados=round(baixado_mb, 1), segundos=round(time.time() - inicio, 1))
            pd.DataFrame([totais]).to_csv(REDUZIDOS / f"totais_{ano}-{mes:02d}.csv", index=False)
            print(f"{ano}-{mes:02d} {origem:16s} {baixado_mb:5.1f} MB  {totais['segundos']:5.1f} s  "
                  f"{totais['linhas_no_arquivo']:,} linhas, {totais['linhas_residentes_capital']:,} da capital", flush=True)


def main():
    asyncio.run(processar())
    totais = pd.concat(pd.read_csv(f) for f in sorted(REDUZIDOS.glob("totais_*.csv")))
    totais.to_csv(SAIDA / "04_totais_por_arquivo.csv", index=False, sep=";")
    print(f"\nTotal baixado: {totais.mb_baixados.sum():,.0f} MB em {totais.segundos.sum() / 60:.1f} min "
          f"({len(totais)} arquivos).")


if __name__ == "__main__":
    main()
