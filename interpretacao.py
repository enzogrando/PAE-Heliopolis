"""Textos explicativos do dashboard, escritos para quem não é de dados nem de programação.

Este arquivo guarda DOIS tipos de texto, para que a equipe possa revisá-los sem
mexer nos cálculos nem na tela:

1. Textos fixos (primeira parte): explicam as fontes, o limiar de "dia quente"
   e o significado dos termos. Não mudam quando o usuário mexe nos filtros.
2. Textos que acompanham os números (segunda parte): são funções que recebem as
   tabelas já calculadas e devolvem uma frase em português com os valores do
   período e do limiar escolhidos. Assim a interpretação nunca fica
   desatualizada em relação ao gráfico que está na tela.

Nenhuma função aqui faz cálculo estatístico novo: elas apenas descrevem, em
palavras, resultados que já existem em analise.py.
"""

import pandas as pd

from apoio import numero
from saude import MINIMO_DIAS_QUENTES

# ---------------------------------------------------------------------------
# 1. TEXTOS FIXOS
# ---------------------------------------------------------------------------

FONTES_RESUMO = (
    "**De onde vêm os dados?** Usamos o **ERA5**, uma base pública do centro europeu de "
    "meteorologia (ECMWF) para o serviço climático Copernicus. O ERA5 combina medições "
    "históricas (estações meteorológicas, satélites e outros instrumentos) com um modelo "
    "físico da atmosfera para estimar, hora a hora, como estava o tempo em cada região do "
    "planeta desde 1940. Nós acessamos essa base pelo **Open-Meteo**, um site que a "
    "disponibiliza gratuitamente.\n\n"
    "**Período:** 2021 a 2025, os cinco anos completos anteriores a 2026. "
    "**Local:** um ponto aproximado de Heliópolis, dentro de uma área de cerca de 25 km. "
    "**O que usamos:** a temperatura do ar e a umidade relativa, a 2 metros do chão."
)

FONTES_DETALHE = (
    "**O que esse dado é.** Uma estimativa do tempo para a região onde Heliópolis fica. "
    "Não é a leitura de um termômetro instalado no bairro.\n\n"
    "**O que esse dado não é.** Como a área estimada tem cerca de 25 km, ele não enxerga "
    "ruas, vielas, tipos de telhado ou árvores. Por isso, não mede a temperatura dentro das "
    "casas, nem diferenças entre partes do bairro, nem sintomas ou qualidade do sono.\n\n"
    "**Por que ainda assim ele serve.** Mostra o contexto de calor da região ao longo do "
    "tempo: quão quente fica, com que frequência, por quantos dias seguidos e em que "
    "horários. Para ligar isso à saúde e à qualidade de vida dos moradores, ainda serão "
    "necessários dados locais, medidos nos mesmos dias e no mesmo território.\n\n"
    "**Lacunas.** Quando falta uma medição, nós não a preenchemos nem a estimamos. Um dia "
    "só entra nas análises se tiver pelo menos 90% das horas com dado (22 de 24 horas).\n\n"
    "Fontes: [ECMWF, ERA5](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5) · "
    "[Copernicus, dados horários do ERA5]"
    "(https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) · "
    "[Open-Meteo, API de dados históricos](https://open-meteo.com/en/docs/historical-weather-api)."
)

LIMIAR_TITULO = "Defina o que é um dia quente"

LIMIAR_TEXTO = (
    "Não existe uma norma oficial de temperatura que valha especificamente para Heliópolis. "
    "Há índices internacionais de calor, como os da NOAA (agência meteorológica dos Estados "
    "Unidos), mas eles foram pensados para outras realidades e se afastam das condições do "
    "bairro. Por isso, em vez de impor um número, **deixamos a escolha com você**: um dia é "
    "contado como quente quando a temperatura máxima chega ao valor definido abaixo. "
    "Esse valor é um critério de análise, não um limite de risco para a saúde."
)

LIMIAR_MUDA = (
    "**Muda quando você move o controle:**\n"
    "- cartão \"Dias com máxima ≥ limiar\"\n"
    "- cartão \"Sequências de calor\"\n"
    "- gráfico \"Frequência de dias quentes\"\n"
    "- tabela de sequências de calor persistente\n"
    "- a frase de conclusão sobre dias quentes e sequências"
)

LIMIAR_NAO_MUDA = (
    "**Não muda (mostram a temperatura em si):**\n"
    "- \"Temperatura ao longo do tempo\"\n"
    "- \"Calor por horário\"\n"
    "- \"Temperatura à noite\"\n"
    "- \"Calor e umidade\"\n"
    "- cartões de maior temperatura e de temperatura média noturna"
)

GLOSSARIO = [
    ("Dia válido",
     "Dia em que pelo menos 90% das horas têm temperatura medida (22 de 24 horas). Um dia "
     "com muitas lacunas fica de fora: ele não é tratado como um dia ameno, apenas como um "
     "dia sem informação suficiente."),
    ("Temperatura máxima, média e mínima",
     "Para cada dia: a maior, a média e a menor temperatura entre as leituras de hora em "
     "hora. A máxima pode não captar picos rápidos que aconteçam entre duas leituras."),
    ("Média mensal",
     "Nos gráficos de vários anos, cada ponto é a média dos dias válidos de um mês. A linha "
     "de máxima mostra a média das máximas diárias do mês, e não o maior valor que ocorreu "
     "naquele mês."),
    ("Frequência de dias quentes",
     "Quantos dias válidos tiveram máxima igual ou acima do limiar, dividido pelo total de "
     "dias válidos do ano. Exemplo: 70 dias quentes entre 350 dias válidos são 20%."),
    ("Sequência de calor",
     "Três ou mais dias seguidos com máxima igual ou acima do limiar. É um critério "
     "exploratório do projeto, e não uma definição oficial de onda de calor."),
    ("Noite",
     "O período das 22h às 5h59. A madrugada conta como parte da noite que começou no dia "
     "anterior. Uma noite só entra se tiver pelo menos 90% das horas medidas."),
    ("Umidade relativa",
     "Quanto vapor de água o ar contém em relação ao máximo que ele comportaria naquela "
     "temperatura. Ar quente comporta mais vapor, então, com a mesma quantidade de vapor, a "
     "umidade relativa cai quando a temperatura sobe."),
    ("Gráfico de pontos (dispersão)",
     "Cada ponto é um dia. A posição na horizontal mostra a temperatura média do dia e, na "
     "vertical, a umidade média. Se os pontos formam uma faixa inclinada, as duas medidas "
     "variam juntas."),
    ("Correlação",
     "Um número entre −1 e +1 que resume o quanto duas medidas variam juntas. Perto de 0, "
     "não há relação visível; perto de +1, uma sobe quando a outra sobe; perto de −1, uma "
     "sobe quando a outra desce. Correlação não prova que uma coisa causa a outra."),
    ("Internação hospitalar (SIH/SUS)",
     "Entrada de uma pessoa em um hospital para ficar internada, paga pelo SUS e registrada no "
     "Sistema de Informações Hospitalares. Não inclui consultas, atendimentos de urgência que "
     "não resultaram em internação nem hospitais particulares pagos por planos de saúde."),
    ("CID (Classificação Internacional de Doenças)",
     "Código que identifica a doença principal de cada internação. O grupo I00–I99 reúne as "
     "doenças do coração e da circulação (por exemplo, infarto e insuficiência cardíaca); o "
     "grupo J00–J99 reúne as doenças respiratórias (por exemplo, pneumonia e asma)."),
    ("Valor esperado",
     "Quantas internações costumam ocorrer em dias parecidos: o mesmo mês, do mesmo ano e do "
     "mesmo dia da semana. Comparar com o esperado evita confundir calor com outras coisas, como "
     "o frio do inverno, o aumento geral de internações ao longo dos anos ou o fim de semana."),
    ("Intervalo de 95%",
     "Faixa de valores compatível com o resultado, dada a variação normal dos dados. Se a faixa "
     "inclui o zero, a diferença encontrada pode ser apenas acaso e não se pode afirmar que "
     "existe diferença."),
]

CONCLUSAO_LIMITES = (
    "**O que estes resultados não permitem concluir:**\n"
    "- Os dados de temperatura descrevem o calor da **região**, e não a temperatura dentro das "
    "casas de Heliópolis.\n"
    "- Os gráficos de temperatura não medem sintomas, sono ou qualquer outro efeito na saúde "
    "das pessoas.\n"
    "- A seção de internações usa dados da **cidade inteira** e apenas do SUS. Ela não mostra o "
    "que acontece com os moradores de Heliópolis e não prova que o calor causa (ou não causa) "
    "internações.\n"
    "- Cinco anos de dados mostram o que aconteceu, mas não bastam para afirmar que o calor "
    "está aumentando ou diminuindo.\n"
    "- A correlação entre calor e umidade descreve um padrão do tempo, e não uma causa.\n\n"
    "Para responder como o calor afeta a saúde e a qualidade de vida dos moradores de "
    "Heliópolis, o próximo passo é obter dados do próprio território, como atendimentos de "
    "urgência e da atenção primária, nos mesmos dias."
)

# ---------------------------------------------------------------------------
# 1b. TEXTOS FIXOS DA SEÇÃO DE INTERNAÇÕES
# ---------------------------------------------------------------------------

SAUDE_TITULO = "Calor e internações hospitalares (cidade de São Paulo)"

SAUDE_INTRO = (
    "**A pergunta desta seção:** nos dias quentes, houve mais (ou menos) internações do que o "
    "normal? Os dados de saúde são do **SIH/SUS**, o sistema de informações hospitalares do "
    "Ministério da Saúde, e contam as internações de **moradores da cidade de São Paulo "
    "inteira**, de 2021 a 2025, por doenças do coração e da circulação e por doenças "
    "respiratórias. **Não são dados de Heliópolis:** o bairro tem poucos moradores perto do "
    "total da cidade, e o número de internações por dia seria pequeno demais para uma análise "
    "confiável. Os dias quentes são os definidos pelo limiar escolhido acima."
)

SAUDE_COMO_LER = (
    "**Como ler a tabela e o gráfico.** Cada dia quente é comparado com o que seria esperado: a "
    "média dos dias não quentes daquele mesmo mês, ano e dia da semana. Assim, o inverno (quando há mais doenças "
    "respiratórias), o aumento geral de internações ao longo dos anos e o fim de semana (quando "
    "há menos internações programadas) não distorcem a comparação. A coluna **Diferença** mostra "
    "quanto as internações dos dias quentes ficaram acima (+) ou abaixo (−) do esperado. O "
    "**intervalo de 95%** é a faixa de valores compatível com o resultado: se ele inclui o "
    "zero, não dá para afirmar que há diferença."
)

SAUDE_LIMITES = (
    "**Limites desta comparação:**\n"
    "- Só entram internações pagas pelo **SUS**, e apenas casos graves o bastante para internar. "
    "Atendimentos em UBS e UPA que não internaram, hospitais particulares e sintomas leves ficam "
    "de fora.\n"
    "- O calor usado é o da **região** (ERA5), e não o que cada pessoa viveu em casa, na rua ou "
    "no trabalho.\n"
    "- A data usada é a da **internação**, e não a do início dos sintomas.\n"
    "- É uma **associação**, e não uma relação de causa e efeito.\n"
    "- Ao mudar o limiar, você testa várias definições de dia quente. Um resultado que aparece "
    "só em um valor do limiar pode ser acaso."
)

SAUDE_FONTE_DETALHE = (
    "**Fonte:** SIH/SUS, arquivos de \"AIH Reduzida\" (RD) do estado de São Paulo, publicados pelo "
    "DATASUS. Cada linha original é uma internação; aqui guardamos apenas contagens por dia.\n\n"
    "**Filtros:** moradores da cidade de São Paulo (código IBGE 355030); somente a AIH normal "
    "(as AIH de continuação são o mesmo caso e não entram, para não contar duas vezes); doença "
    "principal nos grupos I00–I99 e J00–J99; data da internação entre 01/01/2021 e 31/12/2025.\n\n"
    "**Atraso de registro:** as internações chegam aos arquivos com atraso (cerca de 60% no mês "
    "da internação e 99% em até três meses). Usamos arquivos publicados até agosto de 2026, "
    "então o período de 2021 a 2025 está completo.\n\n"
    "**Privacidade:** a tabela usada no painel contém apenas o número de internações por dia, "
    "grupo de doença e faixa de idade. Não há nomes, CEPs, hospitais nem qualquer dado "
    "individual.\n\n"
    "Fontes: [DATASUS, transferência de arquivos](https://datasus.saude.gov.br/transferencia-de-arquivos/) · "
    "[PySUS, biblioteca de acesso aos dados](https://github.com/AlertaDengue/PySUS)."
)

SAUDE_SEM_DADOS = (
    "A tabela de internações (dados_saude/internacoes_diarias_sp.csv) não foi encontrada. "
    "A seção de saúde fica indisponível, e o restante do painel continua funcionando."
)

# ---------------------------------------------------------------------------
# 2. TEXTOS QUE ACOMPANHAM OS NÚMEROS
# ---------------------------------------------------------------------------

_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
# Abaixo disso o resultado da correlação é instável demais para ser comentado.
MINIMO_DIAS_CORRELACAO = 30


def _mes_ano(data):
    """Transforma uma data em "mar/2023", sem depender do idioma do computador."""
    return f"{_MESES[data.month - 1]}/{data.year}"


def _data(data):
    """Formata uma data como dia/mês/ano."""
    return data.strftime("%d/%m/%Y")


def descrever_correlacao(r):
    """Traduz o coeficiente de correlação (de −1 a +1) em palavras."""
    if pd.isna(r):
        return None
    forca = abs(r)
    if forca < 0.1:
        return "praticamente nenhuma relação"
    if forca < 0.3:
        nivel = "fraca"
    elif forca < 0.5:
        nivel = "moderada"
    elif forca < 0.7:
        nivel = "forte"
    else:
        nivel = "muito forte"
    sentido = "positiva (as duas medidas sobem juntas)" if r > 0 else \
        "negativa (quando a temperatura sobe, a umidade tende a cair)"
    return f"relação {nivel} e {sentido}"


def frase_correlacao(r, dias):
    """Resume a relação entre temperatura média e umidade média dos dias."""
    if dias < MINIMO_DIAS_CORRELACAO or pd.isna(r):
        return ("Há poucos dias com temperatura e umidade válidas neste recorte "
                f"({dias}) para resumir a relação entre as duas medidas. "
                "Selecione \"Todo o período\" para ter mais dias.")
    descricao = descrever_correlacao(r)
    frase = (f"Em {numero(dias, 0)} dias, o coeficiente de correlação entre temperatura média e "
             f"umidade média foi {numero(r, 2)}. Isso indica {descricao}.")
    if r <= -0.1:
        frase += (" Isso é esperado: o ar mais quente comporta mais vapor de água, então a "
                  "umidade relativa tende a ser menor nos dias mais quentes.")
    frase += " Correlação descreve um padrão, não uma causa."
    return frase


def leitura_evolucao(diario):
    """Descreve o gráfico "Temperatura ao longo do tempo"."""
    maximas = diario["temp_max_c"].dropna()
    if maximas.empty:
        return "Não há dias válidos neste recorte para descrever a temperatura."
    if len(diario) > 370:
        # Mesma regra do gráfico: em períodos longos ele mostra médias mensais.
        mensal = diario["temp_max_c"].resample("MS").mean().dropna()
        return (f"Entre os meses mostrados, a máxima diária média foi mais alta em "
                f"{_mes_ano(mensal.idxmax())} ({numero(mensal.max())} °C) e mais baixa em "
                f"{_mes_ano(mensal.idxmin())} ({numero(mensal.min())} °C). Quanto mais alta a "
                "linha vermelha, mais quente ficou nas horas de pico daquele mês.")
    dia_quente = maximas.idxmax()
    return (f"O dia mais quente do recorte foi {_data(dia_quente)}, com máxima de "
            f"{numero(maximas.max())} °C. A distância entre a linha vermelha (máxima) e a azul "
            "(mínima) mostra o quanto a temperatura varia ao longo de cada dia.")


def leitura_frequencia(anual, limiar):
    """Descreve o gráfico "Frequência de dias quentes"."""
    anual = anual.dropna(subset=["dias_quentes_pct"])
    if anual.empty:
        return "Não há dias válidos neste recorte para calcular a frequência de dias quentes."
    if len(anual) == 1:
        ano = anual.index[0]
        linha = anual.iloc[0]
        return (f"Em {ano}, {numero(linha.dias_quentes_pct)}% dos dias válidos tiveram máxima de "
                f"{limiar:g} °C ou mais ({int(linha.dias_quentes)} de {int(linha.dias_validos)} dias).")
    mais, menos = anual.dias_quentes_pct.idxmax(), anual.dias_quentes_pct.idxmin()
    texto = (f"Com o limiar de {limiar:g} °C, {mais} teve a maior proporção de dias quentes "
             f"({numero(anual.dias_quentes_pct[mais])}%) e {menos} a menor "
             f"({numero(anual.dias_quentes_pct[menos])}%). Essa comparação descreve o que "
             "aconteceu em cada ano, mas poucos anos não bastam para dizer que o calor está "
             "aumentando ou diminuindo.")
    if not anual.ano_completo_no_recorte.all():
        texto += " Anos com menos dias no recorte devem ser comparados com cuidado."
    return texto


def leitura_horario(perfil):
    """Descreve o gráfico "Calor por horário" a partir da temperatura média de cada hora."""
    perfil = perfil.dropna()
    if perfil.empty:
        return "Não há dados suficientes neste recorte para descrever o perfil por horário."
    return (f"Em média, o horário mais quente é por volta das {perfil.idxmax()}h "
            f"({numero(perfil.max())} °C) e o mais frio, por volta das {perfil.idxmin()}h "
            f"({numero(perfil.min())} °C). São as horas em que o ambiente da região está mais "
            "quente; a exposição de cada pessoa depende de onde ela está (em casa, na rua ou "
            "no trabalho) e não é medida aqui.")


def leitura_noite(noites):
    """Descreve o gráfico "Temperatura à noite"."""
    medias = noites["temp_noturna_media_c"].dropna()
    if medias.empty:
        return "Não há noites completas e válidas neste recorte."
    return (f"Nas {numero(len(medias), 0)} noites válidas, a temperatura média entre 22h e 5h59 "
            f"foi de {numero(medias.mean())} °C, variando de {numero(medias.min())} °C a "
            f"{numero(medias.max())} °C entre as noites. Em geral, noites quentes dão menos "
            "alívio depois de um dia de calor. O painel não mede sono nem a temperatura dentro "
            "das casas.")


def leitura_umidade(r, dias):
    """Descreve o gráfico "Calor e umidade" (um ponto por dia)."""
    return frase_correlacao(r, dias)


def leitura_episodios(episodios, limiar):
    """Descreve a tabela de sequências de calor persistente."""
    if episodios.empty:
        return (f"Com o limiar de {limiar:g} °C, nenhuma sequência de três dias seguidos foi "
                "encontrada neste recorte. Se reduzir o limiar, sequências mais curtas de calor "
                "podem aparecer.")
    mais_longa = episodios.sort_values(["duracao_dias", "inicio"], ascending=[False, True]).iloc[0]
    return (f"Foram encontradas {len(episodios)} sequências de calor. A mais longa durou "
            f"{int(mais_longa.duracao_dias)} dias, de {_data(mais_longa.inicio)} a "
            f"{_data(mais_longa.fim)}, com máxima de {numero(mais_longa.maior_temperatura_c)} °C.")


def _pct_com_sinal(valor):
    """Formata uma variação em % com sinal explícito (+1,2% ou −0,7%)."""
    sinal = "+" if valor > 0 else "−" if valor < 0 else ""
    return f"{sinal}{numero(abs(valor))}%"


def leitura_saude(tabela, limiar):
    """Descreve a comparação entre dias quentes e internações (tabela de saude.comparar_todos)."""
    conclusivos = tabela[tabela.conclusivo] if not tabela.empty else tabela
    if conclusivos.empty:
        return (f"Com o limiar de {limiar:g} °C, este recorte não tem dias quentes (ou dias de "
                f"comparação) com dados de internação em número suficiente: são necessários pelo "
                f"menos {MINIMO_DIAS_QUENTES}. Escolha \"Todo o período\" ou reduza o limiar.")
    dias = int(conclusivos.dias_quentes.iloc[0])
    diferem = conclusivos[(conclusivos.ic_inf_pct > 0) | (conclusivos.ic_sup_pct < 0)]
    faixa = (f"de {_pct_com_sinal(conclusivos.variacao_pct.min())} a "
             f"{_pct_com_sinal(conclusivos.variacao_pct.max())}")
    if diferem.empty:
        texto = (f"Com o limiar de {limiar:g} °C, houve {numero(dias, 0)} dias quentes. Nas "
                 f"{len(conclusivos)} comparações, a diferença nas internações desses dias ficou "
                 f"{faixa} em relação ao esperado, e o intervalo de 95% inclui o zero em todas. "
                 "Ou seja: não encontramos diferença nas internações dos dias quentes. Mas o "
                 f"intervalo chega a {_pct_com_sinal(conclusivos.ic_sup_pct.max())}, então um "
                 "aumento pequeno não pode ser descartado.")
    else:
        itens = "; ".join(
            f"{linha.grupo.lower()} ({linha.idade.lower()}): {_pct_com_sinal(linha.variacao_pct)}, "
            f"com intervalo de {_pct_com_sinal(linha.ic_inf_pct)} a {_pct_com_sinal(linha.ic_sup_pct)}"
            for linha in diferem.itertuples())
        texto = (f"Com o limiar de {limiar:g} °C, houve {numero(dias, 0)} dias quentes. Nas "
                 f"{len(conclusivos)} comparações, a diferença ficou {faixa} em relação ao "
                 f"esperado. O intervalo de 95% não inclui o zero em: {itens}. Como foram feitas "
                 "várias comparações e o limiar pode ser alterado, uma diferença isolada pode ser "
                 "acaso; mesmo que seja real, ela é pequena e não prova causa.")
    return texto + (" Isso não quer dizer que o calor não afete a saúde: estes dados só enxergam "
                    "internações pelo SUS na cidade inteira.")


def leitura_faixas(tabela):
    """Descreve o gráfico de internações por faixa de temperatura (tabela de saude.comparar_por_faixas)."""
    conclusivos = tabela[tabela.conclusivo] if not tabela.empty else tabela
    if conclusivos.empty:
        return ("Este recorte não tem dias suficientes em cada faixa de temperatura para comparar. "
                "Escolha \"Todo o período\".")
    frases = []
    for grupo, parte in conclusivos.groupby("grupo", sort=False):
        mais, menos = parte.loc[parte.variacao_pct.idxmax()], parte.loc[parte.variacao_pct.idxmin()]
        frases.append(f"em {grupo.lower()}, a faixa com mais internações em relação ao esperado foi "
                      f"{mais.faixa} ({_pct_com_sinal(mais.variacao_pct)}) e a com menos foi "
                      f"{menos.faixa} ({_pct_com_sinal(menos.variacao_pct)})")
    return ("; ".join(frases).capitalize() + ". Faixas cujo intervalo de 95% inclui o zero não "
            "mostram diferença clara. Este gráfico não depende do limiar escolhido acima. Nas faixas "
            "mais frias e mais quentes há menos dias, então os resultados são mais incertos. São "
            "diferenças pequenas e não provam causa.")


def conclusoes(diario, noites, episodios, perfil, limiar, r, dias_correlacao):
    """Monta a lista de conclusões do recorte e do limiar atualmente selecionados.

    Cada item repete, em linguagem simples, o que os gráficos acima mostram. Nada
    aqui é calculado de novo: os valores vêm das mesmas tabelas dos gráficos.
    """
    validos = int(diario.dia_valido.sum())
    if not validos:
        return ["Não há dias válidos suficientes neste recorte para tirar conclusões."]
    itens = []
    quentes = int(diario.dia_quente.sum())
    itens.append(f"**Intensidade:** a maior temperatura foi {numero(diario.temp_max_c.max())} °C, e a "
                 f"máxima média dos dias foi {numero(diario.temp_max_c.mean())} °C.")
    itens.append(f"**Frequência:** com o limiar de {limiar:g} °C, {numero(quentes, 0)} de "
                 f"{numero(validos, 0)} dias válidos ({numero(quentes / validos * 100)}%) foram quentes.")
    if episodios.empty:
        itens.append("**Persistência:** nenhuma sequência de três dias ou mais com calor foi encontrada.")
    else:
        itens.append(f"**Persistência:** houve {len(episodios)} sequências de calor de três dias ou "
                     f"mais; a mais longa durou {int(episodios.duracao_dias.max())} dias.")
    horarios_validos = perfil.dropna()
    if not horarios_validos.empty:
        itens.append(f"**Horário:** em média, o calor é maior por volta das {horarios_validos.idxmax()}h "
                     f"({numero(horarios_validos.max())} °C).")
    noites_validas = noites["temp_noturna_media_c"].dropna()
    if not noites_validas.empty:
        itens.append(f"**Noite:** a temperatura média entre 22h e 5h59 foi {numero(noites_validas.mean())} °C.")
    itens.append(f"**Calor e umidade:** {frase_correlacao(r, dias_correlacao)}")
    return itens
