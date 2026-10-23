"""Tarefa 1: lista os arquivos do SIH (AIH Reduzida, RD) de SP entre 01/2021 e 12/2025.

Não baixa nenhum dado: só consulta o catálogo do PySUS (espelho dos arquivos do DATASUS).
Uso: .venv\\Scripts\\python.exe 01_listar_arquivos.py
"""
import asyncio
from pathlib import Path

import pandas as pd
from pysus.api.client import PySUS

SAIDA = Path(__file__).parent / "saidas"


async def listar():
    async with PySUS() as p:
        # Grupo "RD" = AIH Reduzida (uma linha por internação). "SP" no nome do arquivo
        # de outros grupos significa "Serviços Profissionais", não o estado.
        arquivos = await p.query(dataset="SIH", group="RD", state="SP")
    return pd.DataFrame([{
        "arquivo": a.name, "ano": 2000 + int(a.name[4:6]) if int(a.name[4:6]) < 90 else 1900 + int(a.name[4:6]),
        "mes": int(a.name[6:8]), "tamanho_mb": round((a.size or 0) / 1e6, 1),
        "linhas": a.rows, "modificado_em": a.modify, "caminho": str(a.path),
    } for a in arquivos])


def main():
    SAIDA.mkdir(exist_ok=True)
    tabela = asyncio.run(listar()).sort_values(["ano", "mes"])
    tabela.to_csv(SAIDA / "01_arquivos_sih_sp.csv", index=False, sep=";")
    periodo = tabela[(tabela.ano >= 2021) & (tabela.ano <= 2025)]
    print(f"Arquivos RD de SP no catálogo (todos os anos): {len(tabela)}")
    print(f"Primeiro: {tabela.ano.min()}-{tabela.mes.iloc[0]:02d}  Último: "
          f"{tabela.ano.iloc[-1]}-{tabela.mes.iloc[-1]:02d}")
    print(f"\nEntre 2021 e 2025: {len(periodo)} de 60 arquivos esperados; "
          f"{periodo.tamanho_mb.sum():,.0f} MB no total.")
    esperados = {(a, m) for a in range(2021, 2026) for m in range(1, 13)}
    faltam = sorted(esperados - set(zip(periodo.ano, periodo.mes)))
    print("Meses ausentes no período:", faltam or "nenhum")
    print("\nArquivos por ano:")
    print(periodo.groupby("ano").agg(arquivos=("arquivo", "count"), mb=("tamanho_mb", "sum"),
                                     linhas=("linhas", "sum")).to_string())
    print("\nÚltimos 6 arquivos do catálogo:")
    print(tabela.tail(6)[["arquivo", "ano", "mes", "tamanho_mb", "linhas", "modificado_em"]].to_string(index=False))


if __name__ == "__main__":
    main()
