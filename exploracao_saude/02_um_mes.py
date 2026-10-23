"""Tarefa 2: baixa UM mês do SIH de SP (RD) e mostra as colunas e os campos de interesse.

Uso: .venv\\Scripts\\python.exe 02_um_mes.py [ano] [mes]    (padrão: 2023 1)
O arquivo baixado fica em exploracao_saude/cache/ (não em outra pasta do computador).

Nota: nesta versão do PySUS (2.11.7), pysus.ftp.sih() e pysus.ftp.list_files() devolvem
tabela vazia; por isso usamos a interface de baixo nível (PySUS.query + download).
"""
import asyncio
import sys
from pathlib import Path

import pandas as pd
import pysus
from pysus.api.client import PySUS

AQUI = Path(__file__).parent
SAIDA = AQUI / "saidas"


async def baixar(ano, mes):
    async with PySUS() as p:
        arquivos = await p.query(dataset="SIH", group="RD", state="SP", year=ano, month=mes)
        if not arquivos:
            raise SystemExit(f"{ano}-{mes:02d} não está no catálogo do PySUS.")
        local = await p.download(arquivos[0])
        return Path(local.path)


def main():
    ano = int(sys.argv[1]) if len(sys.argv) > 2 else 2023
    mes = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    pysus.set_cache(str(AQUI / "cache"))
    caminho = asyncio.run(baixar(ano, mes))
    print("Arquivo local:", caminho, f"({caminho.stat().st_size / 1e6:.1f} MB)")
    df = pd.read_parquet(caminho)
    print(f"{ano}-{mes:02d}: {len(df):,} linhas x {df.shape[1]} colunas")
    SAIDA.mkdir(exist_ok=True)
    df.head(200).to_csv(SAIDA / "02_amostra_200_linhas.csv", index=False, sep=";")
    resumo = pd.DataFrame({"tipo": df.dtypes.astype(str), "preenchido_pct": (df.notna().mean() * 100).round(1),
                           "exemplo": df.iloc[0]})
    resumo.to_csv(SAIDA / "02_colunas.csv", sep=";")
    print(resumo.to_string())


if __name__ == "__main__":
    main()
