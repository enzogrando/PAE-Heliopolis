"""Confere, com o modelo de regressão (06_teste_de_sinal.py), o efeito de 'dia quente' em vários limiares.

Serve para validar o método descritivo usado no dashboard (saude.py) com uma técnica independente.
Uso: .venv\\Scripts\\python.exe 08_conferir_limiares.py
"""
import importlib.util
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
spec = importlib.util.spec_from_file_location("sinal", AQUI / "06_teste_de_sinal.py")
sinal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sinal)


def main():
    temp, saude = sinal.temperatura_diaria(), sinal.saude_diaria()
    linhas = []
    for limiar in (25, 26, 27, 28, 29, 30, 32):
        quente = (temp.temp_max_c >= limiar).astype(float)
        for grupo in ["I00-I99 todas as idades", "J00-J99 todas as idades", "I00-I99 65+", "J00-J99 65+"]:
            df = pd.DataFrame({"n": saude[grupo], "quente": quente}).dropna()
            df["mes"], df["ano"], df["dow"] = df.index.month, df.index.year, df.index.dayofweek
            df["fim_de_ano"] = (((df.index.month == 12) & (df.index.day >= 20))
                                | ((df.index.month == 1) & (df.index.day == 1))).astype(int)
            r = sinal.ajustar(df, "quente")
            linhas.append({"limiar": limiar, "dias_quentes": int(df.quente.sum()), "grupo": grupo,
                           "variacao_pct": 100 * (r["rr"] - 1), "ic_inf_pct": 100 * (r["ic_inf"] - 1),
                           "ic_sup_pct": 100 * (r["ic_sup"] - 1), "p": r["p"]})
    resultado = pd.DataFrame(linhas)
    resultado.to_csv(AQUI / "saidas" / "08_limiares_regressao.csv", index=False, sep=";")
    pd.set_option("display.width", 200)
    print(resultado.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
