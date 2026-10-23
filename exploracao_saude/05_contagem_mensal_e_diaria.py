"""Tarefa 5: junta as contagens reduzidas, gera a tabela diária e checa se os meses finais estão incompletos.

Entrada: saidas/reduzidos/*.csv (gerados por 04_reduzir_para_contagens.py).
Saídas:  saidas/05_contagem_diaria.csv  (data; grupo_cid; n_internacoes — 2021-01-01 a 2025-12-31, com zeros)
         saidas/05_contagem_mensal.csv  (mês de internação x grupo, com o que já chegou em cada competência)
Regras: só residentes na capital (MUNIC_RES 355030); só IDENT = 1 (AIH normal), para não contar a
mesma internação duas vezes (IDENT = 5 é continuação de longa permanência).
"""
from pathlib import Path

import pandas as pd

SAIDA = Path(__file__).parent / "saidas"
GRUPOS = {"I": "I00-I99", "J": "J00-J99"}


def carregar():
    arquivos = sorted((SAIDA / "reduzidos").glob("20??-??.csv"))
    tabela = pd.concat((pd.read_csv(f, dtype={"data_internacao": str, "ident": str}) for f in arquivos))
    tabela["data"] = pd.to_datetime(tabela.data_internacao, format="%Y%m%d", errors="coerce")
    return tabela


def main():
    t = carregar()
    print(f"Competências lidas: {t.competencia.nunique()} ({t.competencia.min()} a {t.competencia.max()})")
    normal = t[t.ident == "1"].copy()
    normal["grupo_cid"] = normal.letra_cid.map(GRUPOS).fillna("outros")
    normal["mes"] = normal.data.dt.to_period("M")

    # --- tabela diária (alvo do projeto): 1 linha por dia e grupo, incluindo dias com zero ---
    dias = pd.date_range("2021-01-01", "2025-12-31", name="data")
    diaria = (normal[normal.grupo_cid.isin(GRUPOS.values())].groupby(["data", "grupo_cid"]).n.sum()
              .unstack(fill_value=0).reindex(dias, fill_value=0).stack().rename("n_internacoes").reset_index())
    diaria.to_csv(SAIDA / "05_contagem_diaria.csv", index=False, sep=";")
    print(f"\nTabela diária: {len(diaria):,} linhas ({len(dias)} dias x 2 grupos).")
    print("Dias com zero internações:", diaria.groupby("grupo_cid").n_internacoes.apply(lambda s: int((s == 0).sum())).to_dict())
    print(diaria.groupby("grupo_cid").n_internacoes.describe().round(1).to_string())

    # --- contagem mensal por mês de internação (todas as causas e os dois grupos) ---
    mensal = normal.assign(todos=1).groupby("mes").n.sum().rename("todas_as_causas").to_frame()
    for g in GRUPOS.values():
        mensal[g] = normal[normal.grupo_cid == g].groupby("mes").n.sum()
    mensal = mensal.fillna(0).astype(int)
    mensal = mensal[(mensal.index >= pd.Period("2021-01")) & (mensal.index <= pd.Period("2026-08"))]
    mensal["variacao_vs_mes_anterior_%"] = (mensal.todas_as_causas.pct_change() * 100).round(1)
    mensal.to_csv(SAIDA / "05_contagem_mensal.csv", sep=";")
    print("\nInternações por mês de internação (residentes na capital, IDENT=1):")
    print(mensal.to_string())

    # --- atraso de chegada: de quantos meses depois da internação ela aparece no arquivo ---
    normal["atraso_meses"] = (pd.PeriodIndex(normal.competencia, freq="M") - normal.mes).map(lambda d: d.n)
    estudo = normal[(normal.mes >= pd.Period("2021-01")) & (normal.mes <= pd.Period("2025-12"))]
    atraso = estudo.groupby("atraso_meses").n.sum()
    atraso = (atraso / atraso.sum() * 100).round(1)
    print("\nDistribuição do atraso (meses entre a internação e o arquivo em que aparece), % do total 2021-2025:")
    print(atraso.head(8).to_string())
    print("Acumulado:", atraso.cumsum().head(8).round(1).to_dict())
    # Comparação "como estava" x "como ficou": quanto do mês estava visível com 0, 1, 2 e 3 meses de atraso.
    for corte in (0, 1, 2, 3):
        visivel = estudo[estudo.atraso_meses <= corte].groupby("mes").n.sum()
        completo = estudo.groupby("mes").n.sum()
        print(f"Com {corte} mês(es) de espera: mediana de {float((visivel / completo).median() * 100):.1f}% do total final do mês")


if __name__ == "__main__":
    main()
