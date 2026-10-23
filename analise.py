"""Indicadores do relatório, separados da interface para facilitar a revisão.

Os limiares são exploratórios. Não representam diagnósticos, alertas oficiais,
UTCI, temperatura de superfície nem temperatura dentro das casas.

Como ler este arquivo (para quem não programa):
    Aqui ficam as CONTAS do projeto. Cada função recebe uma tabela (um "DataFrame"
    do Pandas, parecido com uma planilha) e devolve outra tabela já resumida:
      - indicadores_diarios: resume as 24 leituras de cada dia em máxima, média e mínima;
      - indicadores_noturnos: faz o mesmo para a noite, das 22h às 5h59;
      - episodios_quentes: encontra períodos de calor com vários dias seguidos;
      - resumo_anual: conta os dias quentes de cada ano;
      - perfil_horario: calcula a temperatura média de cada hora do dia;
      - correlacao_calor_umidade: mede o quanto calor e umidade variam juntos;
      - gerar_relatorio: monta o texto do relatório de terminal.
    Nada neste arquivo desenha gráficos; isso é feito em painel.py.
"""

from datetime import timedelta

import pandas as pd

from dados import FUSO


def indicadores_diarios(horarios: pd.DataFrame, limiar=30.0, cobertura_minima=0.9):
    """Calcula os dias locais e mantém a cobertura ao lado de cada resultado.

    O índice de entrada deve conter todas as horas esperadas (inclusive lacunas),
    como faz dados.limpar_horarios. Assim, dias sem dados não desaparecem.

    Em palavras simples: transforma a tabela de uma linha por hora em uma tabela
    de uma linha por dia, com a temperatura máxima, média e mínima, a cobertura
    (quantas horas do dia têm dado) e a marcação de "dia quente" (máxima >= limiar).
    """
    # As horas chegam em UTC; convertemos para o horário de São Paulo para que
    # cada "dia" corresponda ao dia vivido pelos moradores.
    local = horarios.tz_convert(FUSO)
    # Agrupar pela data civil evita problemas em meias-noites inexistentes no DST.
    dias = pd.Series(local.index.date, index=local.index, name="data")
    grupos = local.groupby(dias)
    # Para cada dia: média, máxima, mínima e quantas leituras de temperatura existem.
    diario = grupos["temperatura_c"].agg(
        temp_media_c="mean", temp_max_c="max", temp_min_c="min", horas_validas="count"
    )
    # Cobertura = horas com dado dividido pelas horas que o dia deveria ter (24, em geral).
    diario["horas_esperadas"] = grupos.size()
    diario["cobertura_pct"] = diario.horas_validas / diario.horas_esperadas * 100
    # Um dia só é "válido" se tiver ao menos 90% das horas (regra de cobertura mínima).
    diario["dia_valido"] = diario.cobertura_pct >= cobertura_minima * 100
    # Dia inválido fica sem temperatura (vazio), e não com zero: ausência não é "dia frio".
    colunas_temp = ["temp_media_c", "temp_max_c", "temp_min_c"]
    diario.loc[~diario.dia_valido, colunas_temp] = float("nan")
    # Contagem de horas com dados: não extrapolamos horas ausentes.
    diario["horas_calor_observadas"] = local.temperatura_c.ge(limiar).groupby(dias).sum()
    diario.loc[~diario.dia_valido, "horas_calor_observadas"] = float("nan")
    # Dia quente = dia válido cuja máxima chegou ao limiar escolhido.
    diario["dia_quente"] = diario.temp_max_c.ge(limiar).astype("boolean")
    diario.loc[~diario.dia_valido, "dia_quente"] = pd.NA
    # Umidade, vento e radiação: média do dia, só se houver 90% das horas daquela variável.
    for coluna in ["umidade_pct", "vento_ms", "radiacao_wm2"]:
        cobertura = grupos[coluna].count() / diario.horas_esperadas
        diario[coluna] = grupos[coluna].mean().where(cobertura >= cobertura_minima)
    # Um total com horas faltantes pode subestimar a chuva: exigimos 100% aqui.
    diario["precipitacao_mm"] = grupos.precipitacao_mm.sum(min_count=1).where(
        grupos.precipitacao_mm.count() == diario.horas_esperadas)
    diario.index = pd.DatetimeIndex(diario.index, name="data")
    return diario


def indicadores_noturnos(horarios: pd.DataFrame, cobertura_minima=0.9):
    """Agrupa a noite de 22h a 05h59 pela data em que ela começou.

    A parte da madrugada pertence ao dia anterior. Noites cortadas pelas bordas
    da consulta são excluídas, mesmo que as poucas horas disponíveis sejam válidas.

    Em palavras simples: para cada noite, calcula a temperatura média e a mínima
    entre 22h e 5h59 e diz se a noite é "válida" (completa e com 90% das horas).
    """
    local = horarios.tz_convert(FUSO)
    # Fica só com as leituras das 22h às 5h59.
    selecionadas = local.loc[(local.index.hour >= 22) | (local.index.hour < 6)].copy()
    if selecionadas.empty:
        return pd.DataFrame(columns=["temp_noturna_media_c", "temp_noturna_min_c",
                                     "horas_validas", "horas_esperadas", "noite_valida"])
    # Madrugada (antes das 6h) entra na noite que começou no dia anterior.
    chaves = [instante.date() - timedelta(days=1) if instante.hour < 6 else instante.date()
              for instante in selecionadas.index]
    grupos = selecionadas.groupby(chaves)
    noites = grupos.temperatura_c.agg(temp_noturna_media_c="mean", temp_noturna_min_c="min",
                                    horas_validas="count")
    # Em uma transição de horário de verão, a noite pode ter 7 ou 9 horas.
    esperadas = []
    completas = []
    for data_noite in noites.index:
        # Início (22h) e fim (6h do dia seguinte) de cada noite, no horário de São Paulo.
        inicio = (pd.Timestamp(data_noite) + pd.Timedelta(hours=22)).tz_localize(FUSO)
        fim = (pd.Timestamp(data_noite + timedelta(days=1)) + pd.Timedelta(hours=6)).tz_localize(FUSO)
        quantidade = int((fim.tz_convert("UTC") - inicio.tz_convert("UTC")).total_seconds() / 3600)
        esperadas.append(quantidade)
        # A noite só é completa se começa e termina dentro do período consultado.
        completas.append(inicio.tz_convert("UTC") >= horarios.index.min() and
                         fim.tz_convert("UTC") <= horarios.index.max() + pd.Timedelta(hours=1))
    noites["horas_esperadas"] = esperadas
    # Noite válida = completa + pelo menos 90% das horas com temperatura.
    noites["noite_valida"] = ((noites.horas_validas / noites.horas_esperadas >= cobertura_minima)
                               & pd.Series(completas, index=noites.index))
    noites.loc[~noites.noite_valida, ["temp_noturna_media_c", "temp_noturna_min_c"]] = float("nan")
    noites.index = pd.DatetimeIndex(noites.index, name="inicio_da_noite")
    return noites


def episodios_quentes(diario: pd.DataFrame, minimo_dias=3):
    """Localiza sequências; dias ausentes ou inválidos interrompem um episódio.

    Chamamos de episódios acima do limiar, não de ondas de calor oficiais.

    Em palavras simples: percorre os dias em ordem e anota cada período de pelo
    menos 3 dias seguidos em que a máxima ficou igual ou acima do limiar.
    """
    registros, sequencia = [], []

    def guardar():
        # Só vira "episódio" a sequência que atinge o mínimo de dias seguidos.
        if len(sequencia) >= minimo_dias:
            trecho = diario.loc[sequencia]
            registros.append({"inicio": sequencia[0], "fim": sequencia[-1],
                              "duracao_dias": len(sequencia),
                              "maior_temperatura_c": trecho.temp_max_c.max(),
                              "media_das_maximas_c": trecho.temp_max_c.mean(),
                              # Marca episódios que encostam no começo ou no fim do período:
                              # eles podem continuar fora do que foi consultado.
                              "toca_borda_da_consulta": sequencia[0] == diario.index.min()
                              or sequencia[-1] == diario.index.max()})

    for dia, linha in diario.sort_index().iterrows():
        quente = pd.notna(linha.dia_quente) and bool(linha.dia_quente)
        # Dia quente e colado no anterior: a sequência continua.
        if quente and (not sequencia or (dia - sequencia[-1]).days == 1):
            sequencia.append(dia)
        else:
            # Dia frio, inválido ou com buraco no calendário: fecha a sequência atual.
            guardar()
            sequencia = [dia] if quente else []
    guardar()
    return pd.DataFrame(registros, columns=["inicio", "fim", "duracao_dias", "maior_temperatura_c",
                                           "media_das_maximas_c", "toca_borda_da_consulta"])


def resumo_anual(diario: pd.DataFrame):
    """Exibe denominadores para não confundir períodos incompletos com anos frios.

    Em palavras simples: para cada ano, conta os dias válidos, os dias quentes e
    calcula a porcentagem de dias quentes (dias quentes / dias válidos x 100).
    """
    grupos = diario.groupby(diario.index.year)
    resumo = grupos.agg(dias_no_recorte=("dia_valido", "size"), dias_validos=("dia_valido", "sum"),
                        dias_quentes=("dia_quente", "sum"), temperatura_media_c=("temp_media_c", "mean"))
    # O denominador é o número de dias válidos, e não 365: dias sem dados não contam.
    resumo["dias_quentes_pct"] = resumo.dias_quentes / resumo.dias_validos.replace(0, float("nan")) * 100
    resumo.loc[resumo.dias_validos == 0, "dias_quentes"] = float("nan")
    resumo["ano_completo_no_recorte"] = [
        quantidade == (366 if pd.Timestamp(ano, 1, 1).is_leap_year else 365)
        for ano, quantidade in resumo.dias_no_recorte.items()]
    resumo.index.name = "ano"
    return resumo


def perfil_horario(horarios: pd.DataFrame):
    """Temperatura média de cada hora do dia (0h a 23h) em todo o período.

    Em palavras simples: o ponto das 14h é a média de todas as leituras válidas
    feitas às 14h, em todos os dias do recorte. Esse cálculo não depende do
    limiar de dia quente nem da regra de 90% de cobertura diária.
    """
    local = horarios.tz_convert(FUSO)
    perfil = local.temperatura_c.groupby(local.index.hour).mean()
    perfil.index.name = "Hora de São Paulo"
    return perfil


def correlacao_calor_umidade(diario: pd.DataFrame):
    """Mede o quanto a temperatura e a umidade médias dos dias variam juntas.

    Devolve (r, dias): r é o coeficiente de correlação de Pearson (de -1 a +1) e
    dias é quantos dias entraram na conta. Usa os mesmos pontos do gráfico
    "Calor e umidade": dias válidos com temperatura e umidade médias disponíveis.
    Descreve um padrão; não indica que uma variável causa a outra.
    """
    pontos = diario.loc[diario.dia_valido, ["temp_media_c", "umidade_pct"]].dropna()
    if len(pontos) < 2:
        return float("nan"), len(pontos)
    return pontos.temp_media_c.corr(pontos.umidade_pct), len(pontos)


def gerar_relatorio(conjunto, diario, noites, episodios, limiar, minimo_dias, cobertura):
    """Gera um relatório textual reproduzível para download, sem inferir causalidade."""
    meta = conjunto["metadados"]
    validos = int(diario.dia_valido.sum())
    quentes = int(diario.dia_quente.sum()) if validos else "não calculável"
    maxima = f"{diario.temp_max_c.max():.1f} °C" if validos else "não calculável"
    return f"""RELATÓRIO EXPLORATÓRIO INICIAL — HELIÓPOLIS

Período local: {meta['inicio']} a {meta['fim']}.
Fonte: Open-Meteo / Copernicus ERA5. Grade de 0,25 grau (~25 km).
Consulta: {meta.get('latitude_solicitada')} / {meta.get('longitude_solicitada')}.
Célula retornada: {meta.get('latitude_retornada')} / {meta.get('longitude_retornada')}.
Coleta (UTC): {meta.get('coletado_em_utc', 'não informado')}.

Critérios: máxima diária >= {limiar:.1f} °C; episódios de pelo menos
{minimo_dias} dias consecutivos; cobertura mínima por variável de {cobertura:.0%}.
Máximas e mínimas são calculadas a partir dos registros horários válidos.
Noite: 22h a 05h59, atribuída à data inicial. Noites parciais são excluídas.

Dias com cobertura suficiente: {validos} de {len(diario)}.
Dias acima do limiar: {quentes}.
Maior temperatura nos dias válidos: {maxima}.
Episódios identificados: {len(episodios)}.
Noites completas com cobertura suficiente: {int(noites.noite_valida.sum())}.

RESUMO POR ANO
{resumo_anual(diario).round(2).to_string()}

QUALIDADE DOS DADOS
{conjunto['qualidade'].to_string(index=False)}

LIMITES DA INTERPRETAÇÃO
Esta é uma estimativa meteorológica regional, não uma estação em Heliópolis.
O ponto de consulta é aproximado e não define o limite oficial do território.
O limiar é exploratório, não um alerta oficial ou classificação clínica.
Lacunas não foram interpoladas. Dias inválidos interrompem os episódios.
Eventos na borda podem continuar fora do intervalo consultado.
Não foram integrados dados de saúde, população, UTCI ou imagens de satélite.
Os resultados não comprovam impactos individuais ou relações causais na saúde.
Dados reabertos de arquivos dependem da integridade do arquivo fornecido.

Referência: https://open-meteo.com/en/docs/historical-weather-api
Atribuição: Open-Meteo e Copernicus Climate Change Service / ECMWF (ERA5).
Os dados foram tratados e agregados por este projeto.
"""
