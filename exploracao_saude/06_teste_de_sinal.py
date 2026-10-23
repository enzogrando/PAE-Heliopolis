"""Passo 1 do plano: existe associação entre a temperatura máxima diária e as internações?

Cruza a série diária de internações (saidas/reduzidos/) com a temperatura ERA5 do dashboard
(buscada pela mesma função do projeto, dados.buscar_open_meteo, e guardada em saidas/ para
não precisar repetir a consulta). NÃO altera nenhum arquivo do projeto.

Modelo (para cada grupo e cada atraso de 0 a 3 dias): regressão de Poisson da contagem diária
sobre a temperatura máxima, controlando mês do ano, ano, dia da semana e fim de ano
(20/12 a 01/01). Os controles de mês e ano retiram a sazonalidade e a tendência de alta; o efeito
vem da diferença entre dias quentes e dias mais frios DENTRO do mesmo mês.
Resultado em "razão de taxas" (RR): RR = 1,03 significa 3% mais internações a cada +1 °C.
Uso: .venv\\Scripts\\python.exe 06_teste_de_sinal.py
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

AQUI = Path(__file__).parent
SAIDA = AQUI / "saidas"
sys.path.insert(0, str(AQUI.parent))  # para reutilizar dados.py e analise.py do projeto (somente leitura)
from analise import indicadores_diarios  # noqa: E402
from dados import buscar_open_meteo, carregar_json, exportar_json  # noqa: E402

TEMPERATURA_JSON = SAIDA / "06_era5_2021_2025.json"


def temperatura_diaria():
    """Temperatura máxima diária (°C) no horário de São Paulo, pela mesma regra do dashboard (dia válido)."""
    if TEMPERATURA_JSON.exists():
        conjunto = carregar_json(TEMPERATURA_JSON.read_bytes())
    else:
        conjunto = buscar_open_meteo(date(2021, 1, 1), date(2025, 12, 31))
        TEMPERATURA_JSON.write_bytes(exportar_json(conjunto))
    return indicadores_diarios(conjunto["horarios"], limiar=30.0)


def saude_diaria():
    """Contagens diárias por grupo (residentes na capital, AIH normal)."""
    arquivos = sorted((SAIDA / "reduzidos").glob("20??-??.csv"))
    t = pd.concat(pd.read_csv(f, dtype={"data_internacao": str, "ident": str}) for f in arquivos)
    t = t[t.ident == "1"].copy()
    t["data"] = pd.to_datetime(t.data_internacao, format="%Y%m%d", errors="coerce")
    dias = pd.date_range("2021-01-01", "2025-12-31", name="data")

    def serie(mascara):
        return t[mascara].groupby("data").n.sum().reindex(dias, fill_value=0)

    i, j, idoso, crianca = t.letra_cid == "I", t.letra_cid == "J", t.faixa_etaria == "65+", t.faixa_etaria == "0-14"
    return pd.DataFrame({"I00-I99 todas as idades": serie(i), "J00-J99 todas as idades": serie(j),
                         "I00-I99 65+": serie(i & idoso), "J00-J99 65+": serie(j & idoso),
                         "J00-J99 0-14": serie(j & crianca)})


def montar(temp, saude, grupo, atraso):
    df = pd.DataFrame({"n": saude[grupo]})
    df["tmax"] = temp.temp_max_c.shift(atraso)
    df["tmax_med_0a3"] = temp.temp_max_c.rolling(4).mean()
    df["quente"] = temp.dia_quente.astype("float").shift(atraso)
    df["mes"], df["ano"], df["dow"] = df.index.month, df.index.year, df.index.dayofweek
    df["fim_de_ano"] = ((df.index.month == 12) & (df.index.day >= 20) | (df.index.month == 1) & (df.index.day == 1)).astype(int)
    return df.dropna()


def ajustar(df, variavel):
    modelo = smf.glm(f"n ~ {variavel} + C(mes) + C(ano) + C(dow) + fim_de_ano", data=df,
                     family=sm.families.Poisson()).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    b, ep = modelo.params[variavel], modelo.bse[variavel]
    return {"rr": np.exp(b), "ic_inf": np.exp(b - 1.96 * ep), "ic_sup": np.exp(b + 1.96 * ep),
            "p": modelo.pvalues[variavel], "dias": int(modelo.nobs)}


def main():
    temp, saude = temperatura_diaria(), saude_diaria()
    print(f"Temperatura: {int(temp.dia_valido.sum())} dias válidos; máxima média {temp.temp_max_c.mean():.1f} °C; "
          f"dias >= 30 °C: {int(temp.dia_quente.sum())}")
    linhas = []
    for grupo in saude.columns:
        naive = saude[grupo].corr(temp.temp_max_c)
        for atraso in range(4):
            r = ajustar(montar(temp, saude, grupo, atraso), "tmax")
            linhas.append({"grupo": grupo, "medida": f"+1 °C na máxima, atraso {atraso} d", **r})
        linhas.append({"grupo": grupo, "medida": "+1 °C, média dos dias 0 a 3",
                       **ajustar(montar(temp, saude, grupo, 0), "tmax_med_0a3")})
        linhas.append({"grupo": grupo, "medida": "dia >= 30 °C x dia < 30 °C, atraso 0",
                       **ajustar(montar(temp, saude, grupo, 0), "quente")})
        linhas.append({"grupo": grupo, "medida": "correlação simples (sem controles)", "rr": naive,
                       "ic_inf": np.nan, "ic_sup": np.nan, "p": np.nan, "dias": len(saude)})
    resultado = pd.DataFrame(linhas)
    resultado.to_csv(SAIDA / "06_resultado_sinal.csv", index=False, sep=";")
    pd.set_option("display.width", 200)
    print(resultado.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
