"""Gera a tabela que o dashboard lê: dados_saude/internacoes_diarias_sp.csv (+ arquivo de origem .json).

Parte de saidas/reduzidos/ (feito por 04_reduzir_para_contagens.py) e mantém só:
    data, grupo_cid, faixa_etaria, n_internacoes
para 01/01/2021 a 31/12/2025, residentes na cidade de São Paulo, AIH normal (IDENT = 1),
CID I00-I99 e J00-J99. Dias sem internação aparecem com 0 (o dado existe e o valor é zero).
Não contém CEP, idade exata, hospital nem qualquer dado individual.
Uso: .venv\\Scripts\\python.exe 07_exportar_para_dashboard.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
DESTINO = AQUI.parent / "dados_saude"
GRUPOS = {"I": "I00-I99", "J": "J00-J99"}
FAIXAS = ["0-14", "15-64", "65+", "sem idade"]


def main():
    arquivos = sorted((AQUI / "saidas" / "reduzidos").glob("20??-??.csv"))
    t = pd.concat(pd.read_csv(f, dtype={"data_internacao": str, "ident": str}) for f in arquivos)
    t = t[(t.ident == "1") & t.letra_cid.isin(GRUPOS)].copy()
    t["data"] = pd.to_datetime(t.data_internacao, format="%Y%m%d", errors="coerce")
    t["grupo_cid"] = t.letra_cid.map(GRUPOS)
    contagem = t.groupby(["data", "grupo_cid", "faixa_etaria"]).n.sum()
    indice = pd.MultiIndex.from_product(
        [pd.date_range("2021-01-01", "2025-12-31"), GRUPOS.values(), FAIXAS],
        names=["data", "grupo_cid", "faixa_etaria"])
    saida = contagem.reindex(indice, fill_value=0).rename("n_internacoes").reset_index()
    DESTINO.mkdir(exist_ok=True)
    saida.to_csv(DESTINO / "internacoes_diarias_sp.csv", index=False, date_format="%Y-%m-%d")
    meta = {
        "fonte": "SIH/SUS (AIH Reduzida, RD), DATASUS, arquivos de São Paulo (RDSP)",
        "obtido_via": "PySUS 2.11.7 (espelho Parquet) e FTP ftp.datasus.gov.br (8 meses ausentes do espelho)",
        "periodo": "2021-01-01 a 2025-12-31 (data da internação)",
        "arquivos_usados": f"competências {arquivos[0].stem} a {arquivos[-1].stem}; os meses de 2026 completam as "
                           "internações de 2025, que chegam com atraso",
        "filtros": "residentes na cidade de São Paulo (MUNIC_RES = 355030); somente AIH normal (IDENT = 1); "
                   "CID principal I00-I99 (aparelho circulatório) e J00-J99 (aparelho respiratório)",
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "linhas": len(saida),
    }
    (DESTINO / "internacoes_diarias_sp.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(saida):,} linhas; {saida.n_internacoes.sum():,} internações; "
          f"{(DESTINO / 'internacoes_diarias_sp.csv').stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
