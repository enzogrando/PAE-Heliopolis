"""Internações hospitalares (SIH/SUS) e sua comparação com os dias quentes.

Como ler este arquivo (para quem não programa):
    Aqui ficam as CONTAS da seção "Calor e internações" do dashboard. Os dados de saúde vêm
    de uma tabela pequena, já pronta, em dados_saude/internacoes_diarias_sp.csv: uma linha por
    dia, grupo de doença e faixa etária, com o número de internações de moradores da CIDADE
    de São Paulo. Não há dados de pessoas, nem do bairro de Heliópolis.
      - carregar_internacoes lê essa tabela;
      - serie_diaria escolhe o grupo de doença e as faixas de idade e devolve um número por dia;
      - comparar_dias_quentes compara os dias quentes com os demais.
    Nada aqui desenha gráficos (isso é feito em painel.py) nem escreve textos (interpretacao.py).

A comparação é descritiva. Para tirar o efeito de coisas que não são clima (mês do ano, ano,
dia da semana), cada dia quente é comparado com o que seria ESPERADO: a média dos dias NÃO quentes
daquele mesmo ano, mês e dia da semana. Não é um modelo de causa e efeito.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE_SAUDE = Path(__file__).parent / "dados_saude" / "internacoes_diarias_sp.csv"
ORIGEM_SAUDE = BASE_SAUDE.with_suffix(".json")

# Grupos de doença (CID-10) disponíveis na tabela e nome usado na tela.
GRUPOS = {"I00-I99": "Doenças do coração e da circulação",
          "J00-J99": "Doenças respiratórias"}
# Recortes de idade: nome na tela -> faixas da tabela.
RECORTES = {"Todas as idades": ["0-14", "15-64", "65+", "sem idade"], "65 anos ou mais": ["65+"]}
# Faixas de temperatura máxima (°C) do gráfico "por faixa": (mínimo incluído, limite excluído, nome).
FAIXAS_TEMPERATURA = [(-np.inf, 20, "abaixo de 20 °C"), (20, 24, "20 a 24 °C"), (24, 27, "24 a 27 °C"),
                      (27, 30, "27 a 30 °C"), (30, np.inf, "30 °C ou mais")]
# Com poucos dias quentes o resultado oscila demais para ser comentado.
MINIMO_DIAS_QUENTES = 10
REPETICOES = 2000


def carregar_internacoes(caminho=BASE_SAUDE):
    """Lê a tabela de internações. Devolve None se o arquivo não existir."""
    caminho = Path(caminho)
    if not caminho.is_file():
        return None
    return pd.read_csv(caminho, parse_dates=["data"])


def serie_diaria(internacoes, grupo, faixas):
    """Número de internações por dia para um grupo de doença e as faixas de idade escolhidas."""
    filtro = internacoes[(internacoes.grupo_cid == grupo) & internacoes.faixa_etaria.isin(faixas)]
    serie = filtro.groupby("data").n_internacoes.sum()
    serie.index = pd.DatetimeIndex(serie.index, name="data")
    return serie


def comparar_dias_quentes(diario, serie, semente=0):
    """Compara as internações dos dias quentes com o esperado (dias não quentes do mesmo ano, mês e dia da semana).

    Recebe a tabela diária do dashboard (analise.indicadores_diarios) e a série de internações.
    Só entram dias válidos que existam nas duas tabelas. Devolve um dicionário com:
      dias_quentes, dias_comparacao   quantos dias entraram em cada grupo; dias_usados é quantos
                                      dias quentes tinham dias de referência suficientes;
      media_quentes, media_demais     internações por dia, em média;
      variacao_pct                    quanto as internações nos dias quentes ficaram acima (+) ou
                                      abaixo (−) do esperado, em %;
      ic_inf_pct, ic_sup_pct          intervalo de 95% dessa variação (reamostragem dos dias);
      conclusivo                      False se há dias quentes demais ou de menos para comentar.
    """
    comum = diario.index.intersection(serie.index)
    dias = diario.loc[comum]
    dias = dias[dias.dia_valido & dias.dia_quente.notna()]
    return _comparar(serie.reindex(dias.index), dias.dia_quente.astype(bool), semente)


def _comparar(n, quente, semente=0):
    """Compara as internações (n) dos dias marcados em "quente" com o esperado nos demais dias.

    "n" e "quente" têm um valor por dia, no mesmo índice de datas. É o núcleo usado tanto pela
    comparação de dias quentes quanto pela comparação por faixa de temperatura.
    """
    resultado = {"dias_quentes": int(quente.sum()), "dias_comparacao": int((~quente).sum()),
                 "media_quentes": float(n[quente].mean()) if quente.any() else float("nan"),
                 "media_demais": float(n[~quente].mean()) if (~quente).any() else float("nan"),
                 "dias_usados": 0, "variacao_pct": float("nan"), "ic_inf_pct": float("nan"),
                 "ic_sup_pct": float("nan"), "conclusivo": False}
    if resultado["dias_quentes"] < MINIMO_DIAS_QUENTES or resultado["dias_comparacao"] < MINIMO_DIAS_QUENTES:
        return resultado
    # Esperado = média das internações dos dias NÃO quentes com o mesmo ano, mês e dia da semana.
    # Os dias quentes ficam de fora dessa média para que ela não "puxe" o esperado para perto deles.
    tabela = pd.DataFrame({"n": n, "quente": quente, "ano": n.index.year,
                           "mes": n.index.month, "dia_semana": n.index.dayofweek})
    referencia = (tabela[~tabela.quente].groupby(["ano", "mes", "dia_semana"]).n
                  .agg(esperado="mean", dias_referencia="count"))
    quentes = tabela[tabela.quente].join(referencia, on=["ano", "mes", "dia_semana"])
    # Um dia quente sem pelo menos 2 dias de referência no mesmo mês e dia da semana fica de fora.
    quentes = quentes[(quentes.dias_referencia >= 2) & (quentes.esperado > 0)]
    resultado["dias_usados"] = len(quentes)
    if len(quentes) < MINIMO_DIAS_QUENTES:
        return resultado
    reais, esperados = quentes.n.to_numpy(float), quentes.esperado.to_numpy(float)
    # Diferença = internações reais / internações esperadas nos dias quentes − 1.
    # O intervalo vem de sortear, com reposição, os dias quentes (reamostragem).
    sorteio = np.random.default_rng(semente).integers(0, len(quentes), size=(REPETICOES, len(quentes)))
    razoes = reais[sorteio].sum(axis=1) / esperados[sorteio].sum(axis=1)
    resultado.update(variacao_pct=(reais.sum() / esperados.sum() - 1) * 100,
                     ic_inf_pct=(np.percentile(razoes, 2.5) - 1) * 100,
                     ic_sup_pct=(np.percentile(razoes, 97.5) - 1) * 100, conclusivo=True)
    return resultado


def comparar_por_faixas(diario, internacoes):
    """Compara as internações em cada faixa de temperatura máxima (todas as idades).

    Para cada grupo de doença e cada faixa, os dias da faixa são comparados com o esperado, calculado
    com os dias FORA da faixa no mesmo ano, mês e dia da semana. Não depende do limiar do painel.
    Devolve uma tabela com uma linha por grupo e faixa, na ordem da menor para a maior temperatura.
    """
    dias = diario[diario.dia_valido & diario.temp_max_c.notna()]
    linhas = []
    for grupo, nome_grupo in GRUPOS.items():
        serie = serie_diaria(internacoes, grupo, RECORTES["Todas as idades"])
        comum = dias.index.intersection(serie.index)
        n, maxima = serie.reindex(comum), dias.loc[comum, "temp_max_c"]
        for ordem, (minimo, limite, nome) in enumerate(FAIXAS_TEMPERATURA):
            resultado = _comparar(n, (maxima >= minimo) & (maxima < limite))
            linhas.append({"grupo": nome_grupo, "faixa": nome, "ordem": ordem, **resultado})
    return pd.DataFrame(linhas)


def comparar_todos(diario, internacoes):
    """Roda a comparação para cada grupo de doença e recorte de idade. Devolve uma tabela."""
    linhas = []
    for grupo, nome_grupo in GRUPOS.items():
        for recorte, faixas in RECORTES.items():
            resultado = comparar_dias_quentes(diario, serie_diaria(internacoes, grupo, faixas))
            linhas.append({"grupo": nome_grupo, "idade": recorte, **resultado})
    return pd.DataFrame(linhas)
