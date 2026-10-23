"""Formatação compartilhada dos indicadores do painel."""
import pandas as pd


def numero(valor, casas=1, sufixo=""):
    """Ausência aparece como travessão; zero continua sendo um resultado válido.

    Formata um número no padrão brasileiro: vírgula nos decimais e ponto nos milhares
    (por exemplo, 1234.5 vira "1.234,5"). "casas" é o número de casas decimais e
    "sufixo" é um texto opcional colocado depois do número (por exemplo, " °C").
    """
    if pd.isna(valor):
        return "—"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".") + sufixo
