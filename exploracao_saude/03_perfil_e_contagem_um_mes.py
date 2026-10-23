"""Tarefas 2 (detalhe) e 3: examina os campos-chave de um mês e conta internações por dia.

Uso: .venv\\Scripts\\python.exe 03_perfil_e_contagem_um_mes.py [caminho do parquet]
Lê o arquivo já baixado por 02_um_mes.py (padrão: RDSP2301). Não baixa nada.
"""
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
SAIDA = AQUI / "saidas"
PADRAO = Path.home() / "pysus" / "downloads" / "ducklake" / "sih" / "RDSP2301.parquet"
SP_CAPITAL = "355030"  # código IBGE de São Paulo (capital) com 6 dígitos, como o SIH usa


def preenchido(serie):
    """Conta como preenchido o que não é vazio nem só zeros (o SIH usa '' e '0000' para 'sem dado')."""
    texto = serie.fillna("").astype(str).str.strip()
    return (texto != "") & ~texto.str.fullmatch("0+")


def main():
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    df = pd.read_parquet(caminho)
    print(f"Arquivo: {caminho.name} | {len(df):,} linhas")

    print("\n== Preenchimento real dos campos de interesse (vazio e só-zeros não contam) ==")
    for col in ["DT_INTER", "DT_SAIDA", "DIAG_PRINC", "MUNIC_RES", "MUNIC_MOV", "NASC", "IDADE",
                "COD_IDADE", "CEP", "SEXO", "RACA_COR", "MORTE", "IDENT"]:
        print(f"{col:11s} {preenchido(df[col]).mean() * 100:6.1f}%   exemplos: {df[col].dropna().unique()[:5].tolist()}")

    print("\n== Duplicidade e tipo de AIH ==")
    print("IDENT (1=AIH normal, 5=continuação/longa permanência):", df.IDENT.value_counts().to_dict())
    print("N_AIH únicos:", df.N_AIH.nunique(), "de", len(df))

    print("\n== Datas de internação dentro do arquivo (competência", df.ANO_CMPT.iloc[0] + "-" + df.MES_CMPT.iloc[0], ") ==")
    datas = pd.to_datetime(df.DT_INTER, format="%Y%m%d", errors="coerce")
    print("Inválidas:", int(datas.isna().sum()), "| menor:", datas.min().date(), "| maior:", datas.max().date())
    mensal = datas.dt.to_period("M").value_counts().sort_index()
    print(f"Internações com data anterior a 2022-10 (reapresentadas/atrasadas): {int(mensal[mensal.index < '2022-10'].sum()):,}")
    print(mensal[mensal.index >= "2022-10"].to_string())

    print("\n== Município (código IBGE de 6 dígitos) ==")
    print("MUNIC_RES = município de residência do paciente; MUNIC_MOV = município do hospital.")
    res = df.MUNIC_RES == SP_CAPITAL
    mov = df.MUNIC_MOV == SP_CAPITAL
    print(f"Residem na capital: {res.sum():,} | internados em hospital da capital: {mov.sum():,} | ambos: {(res & mov).sum():,}")

    print("\n== CEP (apenas pacientes residentes na capital) ==")
    cep = df.loc[res, "CEP"].fillna("").astype(str).str.strip()
    print(f"CEP com 8 dígitos válidos (não zero): {(cep.str.fullmatch(r'\d{8}') & preenchido(cep)).mean() * 100:.1f}%")
    print(f"CEP únicos: {cep.nunique():,} para {len(cep):,} internações")
    print(f"CEP terminado em 000 (geralmente CEP genérico de bairro/município): {cep.str.endswith('000').mean() * 100:.1f}%")
    print(f"CEP dentro da faixa da capital (01000-09999): {cep.str[:5].between('01000', '09999').mean() * 100:.1f}%")
    print("CEPs mais frequentes:", cep.value_counts().head(5).to_dict())

    print("\n== Idade ==")
    print("COD_IDADE (1=horas, 2=dias, 3=meses, 4=anos):", df.COD_IDADE.value_counts().to_dict())
    nasc = pd.to_datetime(df.NASC, format="%Y%m%d", errors="coerce")
    print(f"NASC válida: {nasc.notna().mean() * 100:.1f}%")

    print("\n== CID principal (DIAG_PRINC): 4 caracteres mais comuns ==")
    print(df.DIAG_PRINC.str.len().value_counts().to_dict())
    print(df.DIAG_PRINC.str[:3].value_counts().head(8).to_dict())

    # ---- Tarefa 3: internações por dia, cidade de São Paulo, CID I00-I99 e J00-J99 ----
    letra = df.DIAG_PRINC.str[0]
    grupo = letra.map({"I": "I00-I99 coração", "J": "J00-J99 respiratório"})
    base = df[res & grupo.notna() & (df.IDENT == "1")].assign(data=datas, grupo=grupo)
    por_dia = base.groupby(["data", "grupo"]).size().unstack(fill_value=0)
    SAIDA.mkdir(exist_ok=True)
    por_dia.to_csv(SAIDA / "03_contagem_diaria_um_mes.csv", sep=";")
    print("\n== Internações por dia (residentes na capital, IDENT=1), só dias do mês de competência ==")
    print(por_dia.describe().round(1).to_string())
    print(por_dia.head(10).to_string())
    print("\nTotais no arquivo:", base.grupo.value_counts().to_dict())
    print("Se incluir IDENT=5 (continuação):", int(((res & grupo.notna())).sum()))


if __name__ == "__main__":
    main()
