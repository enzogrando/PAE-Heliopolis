"""Análise exploratória de exposição ao calor no contexto de Heliópolis.

Não há medições locais de Heliópolis. As referências regionais descrevem o ambiente e
não são atribuídas às casas ou moradores. A seção "Calor e internações" usa dados de saúde
da cidade de São Paulo inteira (SIH/SUS), e não do bairro.

Como ler este arquivo (para quem não programa):
    Este é o arquivo que monta a PÁGINA que o usuário vê (usa a biblioteca Streamlit).
    Ele não faz as contas estatísticas: pede os resultados prontos a analise.py e os
    dados a dados.py, e só os desenha na tela. A ordem em que a página aparece é a
    ordem das chamadas dentro da função main(), no final do arquivo:
        1. título e avisos        2. fontes dos dados           3. período e limiar
        4. cartões e gráficos     5. sequências de calor        6. calor e internações
        7. conclusões             8. glossário e notas finais   9. arquitetura do sistema
    Os textos explicativos longos ficam em interpretacao.py.
"""
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from analise import (correlacao_calor_umidade, episodios_quentes, indicadores_diarios,
                     indicadores_noturnos, perfil_horario, resumo_anual)
from apoio import numero
from saude import GRUPOS, RECORTES, carregar_internacoes, comparar_por_faixas, comparar_todos
from arquitetura_projeto import (INTRODUCAO, REQUISICOES, ETL, FUNCIONAIS,
    NAO_FUNCIONAIS, FUTURO, LIMITE, IMAGEM_ARQUITETURA)
from dados import (ErroDados, FIM_ESTUDO, FUSO, INICIO_ESTUDO,
                   buscar_open_meteo, carregar_json, recortar_periodo)
from interpretacao import (CONCLUSAO_LIMITES, FONTES_DETALHE, FONTES_RESUMO, GLOSSARIO,
                           LIMIAR_MUDA, LIMIAR_NAO_MUDA, LIMIAR_TEXTO, LIMIAR_TITULO,
                           conclusoes, leitura_episodios, leitura_evolucao,
                           leitura_frequencia, leitura_horario, leitura_noite,
                           leitura_faixas, leitura_saude, leitura_umidade, SAUDE_COMO_LER, SAUDE_FONTE_DETALHE,
                           SAUDE_INTRO, SAUDE_LIMITES, SAUDE_SEM_DADOS, SAUDE_TITULO)

# Arquivo com a série ERA5 já salva no computador (tem prioridade sobre a internet).
BASE_LOCAL = Path(__file__).parent / "dados_locais" / "heliopolis_open_meteo.json"
# Um dia (ou uma noite) só conta se pelo menos 90% das horas tiverem temperatura medida.
COBERTURA = 0.90
# Uma "sequência de calor" exige pelo menos 3 dias seguidos acima do limiar.
MINIMO_DIAS = 3


@st.cache_data(ttl=86400, max_entries=6, show_spinner=False)
def carregar_online(inicio, fim):
    """Consulta o Open-Meteo pela internet.

    O resultado fica guardado (cache) por 24 horas, para não repetir a mesma
    consulta toda vez que o usuário mexe em um filtro da página.
    """
    return buscar_open_meteo(inicio, fim)


# Mesma cor para o mesmo grupo de doença em todos os gráficos de internações.
CORES_GRUPOS = dict(zip(GRUPOS.values(), ["#d94832", "#287b9c"]))
MESES = "['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']"
TITULO_DIFERENCA = "Diferença em relação ao esperado (%)"


def grafico_linhas(serie, cores, altura, mensal):
    """Linhas ao longo do tempo com os meses em português.

    O st.line_chart escreve os meses em inglês (April, July...) e não deixa trocar, por isso
    este gráfico usa o Altair. "serie" tem as datas no índice e uma coluna por linha;
    "mensal" diz se cada ponto é um mês (rótulos "abr 2024") ou um dia (rótulos "15 abr").
    """
    rotulo = (f"{MESES}[month(datum.value)] + ' ' + year(datum.value)" if mensal else
              f"timeFormat(datum.value, '%d') + ' ' + {MESES}[month(datum.value)]")
    nomes = list(serie.columns)
    longa = serie.rename_axis("Data").reset_index().melt("Data", var_name="Medida", value_name="Valor")
    grafico = alt.Chart(longa).mark_line().encode(
        x=alt.X("Data:T", title=None, axis=alt.Axis(labelExpr=rotulo, labelOverlap=True)),
        y=alt.Y("Valor:Q", title="Temperatura (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color("Medida:N", scale=alt.Scale(domain=nomes, range=cores),
                        legend=alt.Legend(title=None, orient="bottom") if len(nomes) > 1 else None),
        tooltip=[alt.Tooltip("Data:T", format="%d/%m/%Y"), alt.Tooltip("Medida:N"),
                 alt.Tooltip("Valor:Q", format=".1f", title="°C")],
    ).properties(height=altura)
    st.altair_chart(grafico, width="stretch")


def dados_barras(tabela, coluna, eixo_x):
    """Prepara as linhas conclusivas de uma tabela de comparação para o gráfico de barras.

    Cada linha vira uma barra: a diferença em % e o intervalo de 95% (inferior e superior).
    "coluna" é a coluna da tabela que vai para o eixo X (a idade ou a faixa de temperatura).
    """
    t = tabela[tabela.conclusivo]
    return pd.DataFrame({
        eixo_x: t[coluna].to_numpy(), "Grupo": t.grupo.to_numpy(), "Diferença (%)": t.variacao_pct.to_numpy(),
        "Inferior": t.ic_inf_pct.to_numpy(), "Superior": t.ic_sup_pct.to_numpy(),
        "Intervalo de 95% (%)": [f"{numero(i)} a {numero(s)}" for i, s in zip(t.ic_inf_pct, t.ic_sup_pct)]})


def barras_agrupadas(dados, eixo_x, categorias, altura):
    """Barras lado a lado (uma cor por grupo de doença) com o intervalo de 95% em cada barra.

    O st.bar_chart não deixa escolher o ângulo dos nomes nem desenhar barras de erro, por isso este
    gráfico usa o Altair. "dados" vem de dados_barras e "categorias" é a ordem dos nomes no eixo X.
    A linha com marcas em cada barra é o intervalo de 95%: se ela cruza o zero, não há diferença clara.
    """
    grupos = list(CORES_GRUPOS)
    base = alt.Chart(dados).encode(
        x=alt.X(f"{eixo_x}:N", sort=categorias, title=eixo_x, axis=alt.Axis(labelAngle=0, labelLimit=0)),
        xOffset=alt.XOffset("Grupo:N", sort=grupos))
    barras = base.mark_bar().encode(
        y=alt.Y("Diferença (%):Q", title=TITULO_DIFERENCA),
        color=alt.Color("Grupo:N", scale=alt.Scale(domain=grupos, range=list(CORES_GRUPOS.values())),
                        legend=alt.Legend(title=None, orient="bottom", labelLimit=0)),
        tooltip=[eixo_x, "Grupo", alt.Tooltip("Diferença (%):Q", format=".1f"), "Intervalo de 95% (%)"])
    cinza = "#9aa0a6"
    linha = base.mark_rule(color=cinza, strokeWidth=3).encode(
        y=alt.Y("Inferior:Q", title=TITULO_DIFERENCA), y2="Superior:Q")
    marca_inferior = base.mark_tick(color=cinza, size=14, thickness=3).encode(y=alt.Y("Inferior:Q", title=TITULO_DIFERENCA))
    marca_superior = base.mark_tick(color=cinza, size=14, thickness=3).encode(y=alt.Y("Superior:Q", title=TITULO_DIFERENCA))
    st.altair_chart(alt.layer(barras, linha, marca_inferior, marca_superior).properties(height=altura), width="stretch")
    st.caption("As barras mostram a diferença em relação ao esperado. A linha em cada barra é o intervalo de 95%: "
               "se ela cruza o zero, não dá para afirmar que há diferença.")


def iniciar_base():
    """Obtém a série de temperaturas e a guarda na sessão, sem expor operações de manutenção ao leitor.

    A "sessão" (st.session_state) é a memória da página enquanto ela está aberta.
    O caminho é este:
      1. Se a série já está na sessão, só a recorta para o período do estudo (2021–2025).
      2. Se não está e esta é a primeira tentativa, lê o arquivo salvo no computador
         (dados_locais/heliopolis_open_meteo.json). Se o arquivo não existir, consulta a
         internet. Em ambos os casos, recorta para o período do estudo.
      3. Se algo der errado, a série é descartada e a mensagem de erro é guardada na sessão.
    A tentativa inicial é marcada para que uma falha não se repita a cada filtro.
    """
    try:
        if "conjunto" in st.session_state:
            st.session_state["conjunto"] = recortar_periodo(st.session_state["conjunto"])
        elif not st.session_state.get("carga_inicial_tentada"):
            st.session_state["carga_inicial_tentada"] = True
            conjunto = carregar_json(BASE_LOCAL.read_bytes()) if BASE_LOCAL.is_file() else carregar_online(INICIO_ESTUDO, FIM_ESTUDO)
            st.session_state["conjunto"] = recortar_periodo(conjunto)
    except (ErroDados, OSError) as erro:
        st.session_state.pop("conjunto", None)
        st.session_state["erro_inicial"] = str(erro)


def recortar_base(conjunto, ano):
    """Todas as perguntas da página usam o mesmo recorte temporal.

    Recebe o conjunto de dados e o ano escolhido no filtro "Período" e devolve o
    conjunto restrito a esse ano. Se a escolha for "Todo o período", devolve tudo.
    """
    if ano == "Todo o período":
        return conjunto
    # "local" guarda os horários da série convertidos para o fuso de São Paulo,
    # porque o ano do usuário é o ano no horário local, e não em UTC.
    local = conjunto["horarios"].index.tz_convert(FUSO)
    # "datas" guarda só os horários que pertencem ao ano escolhido.
    datas = local[local.year == int(ano)]
    # Recorta a série entre o primeiro e o último dia encontrados nesse ano.
    return recortar_periodo(conjunto, datas.min().date(), datas.max().date())


def mostrar_fontes():
    """Explica de onde vêm os dados, em linguagem simples, antes de qualquer gráfico."""
    with st.container(border=True):
        st.markdown(FONTES_RESUMO)
        with st.expander("Saiba mais sobre a fonte e seus limites"):
            st.markdown(FONTES_DETALHE)


def mostrar_controles(original):
    """Mostra o filtro de período e o controle do limiar, ocupando toda a largura da página.

    Devolve dois valores: o período escolhido (um ano ou "Todo o período") e o limiar
    de temperatura que define o que conta como "dia quente". Todo o resto da página
    é recalculado a partir dessas duas escolhas.
    """
    # Lista de anos disponíveis na série, no horário de São Paulo.
    anos = original["horarios"].index.tz_convert(FUSO).year.unique()
    opcoes = ["Todo o período", *map(str, sorted(anos))]
    # Se o período guardado na sessão deixou de existir, volta para "Todo o período".
    if st.session_state.get("periodo", opcoes[0]) not in opcoes:
        st.session_state["periodo"] = opcoes[0]
    # O filtro de período fica em uma coluna estreita para não esticar demais.
    seletor, _ = st.columns([1, 2])
    ano = seletor.selectbox("Período", opcoes, key="periodo")
    with st.container(border=True):
        st.subheader(LIMIAR_TITULO)
        st.write(LIMIAR_TEXTO)
        limiar = st.slider("Temperatura de referência para explorar o calor (°C)", 25.0, 40.0, 30.0, 0.5, key="limiar")
        st.markdown(f"Com o valor escolhido, um dia é contado como **quente** quando a "
                    f"temperatura máxima for de **{limiar:g} °C ou mais**.")
        muda, nao_muda = st.columns(2)
        muda.markdown(LIMIAR_MUDA)
        nao_muda.markdown(LIMIAR_NAO_MUDA)
    return ano, limiar


def mostrar_exposicao(diario, noites, episodios, limiar):
    """Desenha os quatro cartões de resumo e os gráficos de intensidade e frequência do calor.

    Recebe as tabelas já calculadas por analise.py: "diario" (uma linha por dia),
    "noites" (uma linha por noite), "episodios" (sequências de calor) e o limiar escolhido.
    """
    # Primeiro conta quantos dias são válidos e quantos deles foram quentes.
    validos = int(diario.dia_valido.sum())
    quentes = int(diario.dia_quente.sum()) if validos else float("nan")
    # Os quatro cartões do topo. Quando não há dado, aparece um travessão (—), nunca zero.
    cartoes = st.columns(4)
    cartoes[0].metric("Maior temperatura horária", numero(diario.temp_max_c.max(), sufixo=" °C"))
    cartoes[1].metric(f"Dias com máxima ≥ {limiar:g} °C", numero(quentes, 0))
    cartoes[2].metric("Sequências de calor", numero(len(episodios) if validos else float("nan"), 0))
    cartoes[3].metric("Temperatura média noturna", numero(noites.temp_noturna_media_c.mean(), sufixo=" °C"))
    st.caption(f"Contexto regional ERA5 · {validos:,} de {len(diario):,} dias válidos · "
               f"{int(noites.noite_valida.sum()):,} noites válidas · sequências de pelo menos três dias com máxima ≥ limiar.")
    if not validos:
        st.warning("Dados insuficientes para analisar a exposição diária neste período.")
    esquerda, direita = st.columns([2, 1])
    # Gráfico da esquerda: temperatura máxima, média e mínima ao longo do tempo.
    with esquerda, st.container(border=True, height="stretch"):
        st.markdown("**Temperatura ao longo do tempo**")
        serie = diario[["temp_max_c", "temp_media_c", "temp_min_c"]]
        # A agregação mensal facilita ler os cinco anos. Os cartões e episódios
        # continuam usando os valores diários, preservando os extremos.
        longo = len(diario) > 370
        if longo:
            serie = serie.resample("MS").mean()
        grafico_linhas(serie.rename(columns={"temp_max_c": "Máxima (°C)",
            "temp_media_c": "Média (°C)", "temp_min_c": "Mínima (°C)"}),
            ["#d94832", "#d99b25", "#287b9c"], 240, mensal=longo)
        st.caption(("Médias mensais das máximas, médias e mínimas diárias. " if longo else
                    "Máximas, médias e mínimas dos registros horários de cada dia. ") +
                   "Permite explorar a intensidade e a sazonalidade do calor regional.")
        st.markdown("**O que isso significa:** " + leitura_evolucao(diario))
    # Gráfico da direita: porcentagem de dias quentes em cada ano (depende do limiar).
    with direita, st.container(border=True, height="stretch"):
        st.markdown("**Frequência de dias quentes**")
        anual = resumo_anual(diario)
        visual = anual[["dias_quentes_pct"]].rename(columns={"dias_quentes_pct": "Dias com calor (%)"})
        visual.index = visual.index.astype(str)
        st.bar_chart(visual, color="#dc8532", height=240)
        st.caption("Percentual dos dias válidos com máxima ≥ limiar. Comparação descritiva entre anos; cinco anos não estabelecem uma tendência climática.")
        st.markdown("**O que isso significa:** " + leitura_frequencia(anual, limiar))


def mostrar_rotina(perfil, diario, noites, r, dias_correlacao):
    """Descreve o ambiente térmico, sem substituir observações de sono ou sintomas.

    Desenha três gráficos lado a lado: calor por horário do dia, temperatura à noite
    e a relação entre calor e umidade. "perfil" é a temperatura média de cada hora;
    "r" e "dias_correlacao" resumem a relação calor-umidade (calculada em analise.py).
    """
    hora_col, noite_col, umidade_col = st.columns(3)
    # Gráfico 1: temperatura média em cada hora do dia (0h a 23h).
    with hora_col, st.container(border=True, height="stretch"):
        st.markdown("**Calor por horário**")
        st.line_chart(perfil.rename("Temperatura (°C)"), color="#d99b25", height=220)
        st.caption("Temperatura média em cada hora do dia. Ajuda a identificar os horários de maior calor no contexto da rotina dos moradores.")
        st.markdown("**O que isso significa:** " + leitura_horario(perfil))
    # Gráfico 2: temperatura média das noites (22h às 5h59).
    with noite_col, st.container(border=True, height="stretch"):
        st.markdown("**Temperatura à noite**")
        serie = noites[["temp_noturna_media_c"]].rename(columns={"temp_noturna_media_c": "Temperatura noturna (°C)"})
        # Com muitas noites, o gráfico mostra a média de cada mês para ficar legível.
        mensal = len(serie) > 370
        if mensal:
            serie = serie.resample("MS").mean()
            legenda = "Médias mensais das noites válidas"
        else:
            legenda = "Médias das noites válidas"
        grafico_linhas(serie, ["#287b9c"], 220, mensal=mensal)
        st.caption(legenda + " · 22h–05h59. Caracteriza o período de descanso, sem medir a qualidade do sono.")
        st.markdown("**O que isso significa:** " + leitura_noite(noites))
    # Gráfico 3: cada ponto é um dia, com sua temperatura média e sua umidade média.
    with umidade_col, st.container(border=True, height="stretch"):
        st.markdown("**Calor e umidade**")
        # Cada ponto é um dia com cobertura suficiente nas duas variáveis.
        # Mostramos todo o conjunto para explorar a relação, sem selecionar
        # apenas dias quentes e esconder o restante da distribuição.
        pontos = diario.loc[diario.dia_valido, ["temp_media_c", "umidade_pct"]].dropna().rename(
            columns={"temp_media_c": "Temperatura (°C)", "umidade_pct": "Umidade (%)"})
        if pontos.empty:
            st.info("Não há dias com cobertura suficiente de temperatura e umidade neste recorte.")
        else:
            # Os eixos começam perto dos valores reais (não em zero), para os pontos não ficarem espremidos.
            st.altair_chart(alt.Chart(pontos).mark_circle(size=45, opacity=0.6, color="#287b9c").encode(
                x=alt.X("Temperatura (°C):Q", scale=alt.Scale(zero=False)),
                y=alt.Y("Umidade (%):Q", scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("Temperatura (°C):Q", format=".1f"), alt.Tooltip("Umidade (%):Q", format=".0f")],
            ).properties(height=220), width="stretch")
            st.caption("Cada ponto representa as médias de um dia. Explora a relação entre calor e umidade; não é sensação térmica nem índice de estresse térmico.")
            st.markdown("**O que isso significa:** " + leitura_umidade(r, dias_correlacao))


def mostrar_persistencia(episodios, limiar):
    """Lista os períodos de calor persistente (3 dias seguidos ou mais) em uma tabela."""
    st.markdown("**Quando o calor persistiu por vários dias?**")
    if episodios.empty:
        st.write("Nenhuma sequência de três dias ou mais identificada neste recorte.")
    else:
        # Ordena das sequências mais longas para as mais curtas e formata as datas.
        tabela = episodios.sort_values(["duracao_dias", "inicio"], ascending=[False, True]).copy()
        tabela["inicio"] = tabela.inicio.dt.strftime("%d/%m/%Y")
        tabela["fim"] = tabela.fim.dt.strftime("%d/%m/%Y")
        tabela = tabela.rename(columns={"inicio": "Início", "fim": "Fim", "duracao_dias": "Duração (dias)",
            "maior_temperatura_c": "Maior temperatura (°C)", "media_das_maximas_c": "Média das máximas (°C)",
            "toca_borda_da_consulta": "Pode continuar fora do recorte"})
        st.dataframe(tabela.round(1), hide_index=True, width="stretch")
    st.caption(f"Máxima ≥ {limiar:g} °C em pelo menos três dias consecutivos; dias inválidos interrompem a sequência. "
               "Critério exploratório, não uma definição oficial de onda de calor.")
    st.markdown("**O que isso significa:** " + leitura_episodios(episodios, limiar))


@st.cache_data(show_spinner=False)
def carregar_saude():
    """Lê a tabela de internações (pequena) uma vez e a guarda em cache."""
    return carregar_internacoes()


def mostrar_saude(diario, limiar):
    """Seção "Calor e internações": compara os dias quentes com as internações da cidade de São Paulo.

    Usa os mesmos dias quentes do restante da página (período e limiar escolhidos acima).
    Os dados de saúde são da cidade inteira e só do SUS, e a seção deixa isso claro.
    """
    st.subheader(SAUDE_TITULO)
    internacoes = carregar_saude()
    if internacoes is None:
        st.info(SAUDE_SEM_DADOS)
        return
    st.markdown(SAUDE_INTRO)
    tabela = comparar_todos(diario, internacoes)
    # Os blocos ficam um embaixo do outro, cada um com a largura toda da página.
    # Bloco 1 · gráfico: quanto as internações dos dias quentes diferem do esperado, em %.
    with st.container(border=True):
        st.markdown("**Internações nos dias quentes, comparadas ao esperado**")
        conclusivos = tabela[tabela.conclusivo]
        if conclusivos.empty:
            st.info("Dias quentes insuficientes neste recorte para comparar.")
        else:
            # Um grupo de barras por faixa de idade, uma cor por doença, com o intervalo de 95% em cada barra.
            barras_agrupadas(dados_barras(conclusivos, "idade", "Idade"), "Idade", list(RECORTES), altura=420)
        st.markdown("Barras perto de zero indicam que os dias quentes tiveram um número de internações "
                    "parecido com o esperado para o mesmo mês, ano e dia da semana.")
        st.markdown("**O que isso significa:** " + leitura_saude(tabela, limiar))
    # Bloco 2 · gráfico: as internações em cada faixa de temperatura (não depende do limiar).
    faixas = comparar_por_faixas(diario, internacoes)
    with st.container(border=True):
        st.markdown("**Internações por faixa de temperatura máxima, comparadas ao esperado**")
        validas = faixas[faixas.conclusivo]
        if validas.empty:
            st.info("Dias insuficientes neste recorte para comparar as faixas de temperatura.")
        else:
            # Todas as faixas ficam no eixo, da mais fria à mais quente; as sem dias suficientes ficam sem barra.
            ordem_faixas = list(faixas.drop_duplicates("faixa").sort_values("ordem").faixa)
            barras_agrupadas(dados_barras(faixas, "faixa", "Temperatura máxima do dia"),
                             "Temperatura máxima do dia", ordem_faixas, altura=420)
        st.markdown("Cada barra compara os dias daquela faixa de temperatura com o esperado para o mesmo "
                    "mês, ano e dia da semana. Faixas sem barra não têm dias suficientes para comparar.")
        st.markdown("**O que isso significa:** " + leitura_faixas(faixas))
        with st.expander("Ver os números por faixa"):
            st.dataframe(pd.DataFrame({
                "Grupo": faixas.grupo, "Temperatura máxima": faixas.faixa, "Dias": faixas.dias_quentes,
                "Diferença (%)": [numero(v) if c else "—" for v, c in zip(faixas.variacao_pct, faixas.conclusivo)],
                "Intervalo de 95% (%)": [f"{numero(i)} a {numero(s)}" if c else "—" for i, s, c in
                                         zip(faixas.ic_inf_pct, faixas.ic_sup_pct, faixas.conclusivo)]}),
                hide_index=True, width="stretch", height="content")
    # Bloco 3 · tabela: os números do bloco 1, com o intervalo de 95%.
    with st.container(border=True):
        st.markdown("**Números da comparação de dias quentes**")
        mostra = pd.DataFrame({
            "Grupo": tabela.grupo, "Idade": tabela.idade, "Dias quentes": tabela.dias_quentes,
            "Internações/dia (dias quentes)": [numero(v) for v in tabela.media_quentes],
            "Internações/dia (demais dias)": [numero(v) for v in tabela.media_demais],
            "Diferença (%)": [numero(v) if c else "—" for v, c in zip(tabela.variacao_pct, tabela.conclusivo)],
            "Intervalo de 95% (%)": [f"{numero(i)} a {numero(s)}" if c else "—" for i, s, c in
                                     zip(tabela.ic_inf_pct, tabela.ic_sup_pct, tabela.conclusivo)]})
        # height="content": a tabela tem a altura das suas linhas, sem barra de rolagem vertical.
        st.dataframe(mostra, hide_index=True, width="stretch", height="content")
    with st.expander("Como ler esta comparação"):
        st.markdown(SAUDE_COMO_LER)
    st.info(SAUDE_LIMITES)
    with st.expander("Fonte dos dados de saúde, filtros e privacidade"):
        st.markdown(SAUDE_FONTE_DETALHE)


def mostrar_conclusoes(diario, noites, episodios, perfil, limiar, r, dias_correlacao):
    """Resume o que os gráficos mostram para o período e o limiar escolhidos, e o que eles não permitem concluir."""
    st.subheader("Conclusões")
    st.caption("Resumo em linguagem simples do período e do limiar escolhidos acima. "
               "O texto muda quando você altera esses controles.")
    for item in conclusoes(diario, noites, episodios, perfil, limiar, r, dias_correlacao):
        st.markdown(f"- {item}")
    st.info(CONCLUSAO_LIMITES)


def mostrar_glossario():
    """Explica os termos de estatística e de clima usados na página."""
    with st.expander("Glossário: o que significam os termos usados aqui"):
        for termo, explicacao in GLOSSARIO:
            st.markdown(f"**{termo}.** {explicacao}")


def mostrar_arquitetura():
    """Apresenta os requisitos e o fluxo técnico, no final da página, depois das análises do estudo."""
    st.subheader("Engenharia de software e arquitetura")
    st.write(INTRODUCAO)
    st.image(str(IMAGEM_ARQUITETURA), caption="Arquitetura implementada: API REST externa, ETL em memória e apresentação no Streamlit.")
    st.write(REQUISICOES)
    st.write(ETL)
    funcionais, qualidade = st.columns(2)
    with funcionais:
        st.markdown("**Requisitos funcionais — o que o sistema faz**")
        for codigo, titulo, descricao in FUNCIONAIS:
            st.markdown(f"**{codigo} · {titulo}:** {descricao}")
    with qualidade:
        st.markdown("**Requisitos não funcionais — como o sistema deve operar**")
        for codigo, titulo, descricao in NAO_FUNCIONAIS:
            st.markdown(f"**{codigo} · {titulo}:** {descricao}")
    st.caption(FUTURO)
    st.caption(LIMITE)


def main():
    """Monta a página inteira, de cima para baixo, na ordem em que o usuário a vê."""
    st.set_page_config(page_title="Heliópolis | Estresse térmico", page_icon="☀️", layout="wide")
    st.title("Heliópolis · Estresse térmico")
    st.write("Análise exploratória da exposição ao calor para o estudo da saúde e da qualidade de vida dos moradores.")
    st.caption("2021–2025 · Contexto ambiental regional de Heliópolis")
    st.caption("Quer saber como o sistema foi construído? A seção \"Engenharia de software e arquitetura\" está no final da página.")
    st.info("Análise preliminar: as medições do Observatório De Olho na Quebrada não estão disponíveis para o projeto. "
            "Sem essa base e sem dados de saúde ou qualidade de vida do próprio bairro, os resultados descrevem "
            "o calor regional; não medem impactos nos moradores nem temperaturas dentro das moradias. "
            "Os únicos dados de saúde usados são internações da cidade de São Paulo inteira (seção \"Calor e internações\").")
    mostrar_fontes()
    # Obtém a série de temperaturas (do arquivo salvo ou da internet).
    iniciar_base()
    if "conjunto" not in st.session_state:
        st.error("A série ambiental está indisponível. Não é possível apresentar a análise neste momento.")
        return
    original = st.session_state["conjunto"]
    # Período e limiar escolhidos pelo usuário.
    ano, limiar = mostrar_controles(original)
    # A partir daqui, tudo é recalculado com essas duas escolhas.
    conjunto = recortar_base(original, ano)
    horarios = conjunto["horarios"]
    # Resultados por dia, por noite e por sequência de calor (contas em analise.py).
    diario = indicadores_diarios(horarios, limiar, COBERTURA)
    noites = indicadores_noturnos(horarios, COBERTURA)
    episodios = episodios_quentes(diario, MINIMO_DIAS)
    # Temperatura média por hora do dia e relação entre calor e umidade.
    perfil = perfil_horario(horarios)
    r, dias_correlacao = correlacao_calor_umidade(diario)
    inicio = date.fromisoformat(conjunto["metadados"]["inicio"]).strftime("%d/%m/%Y")
    fim = date.fromisoformat(conjunto["metadados"]["fim"]).strftime("%d/%m/%Y")
    st.caption(f"{inicio} a {fim} · A referência selecionada é um limiar analítico, não um limite de risco à saúde.")
    mostrar_exposicao(diario, noites, episodios, limiar)
    mostrar_rotina(perfil, diario, noites, r, dias_correlacao)
    with st.expander("Explorar sequências de calor persistente"):
        mostrar_persistencia(episodios, limiar)
    mostrar_saude(diario, limiar)
    mostrar_conclusoes(diario, noites, episodios, perfil, limiar, r, dias_correlacao)
    mostrar_glossario()
    st.caption("Leitura dos resultados: dias e noites exigem pelo menos 90% das horas de temperatura; "
               "noites parciais são excluídas. Máximas vêm de amostras horárias. Lacunas permanecem ausentes. "
               "ERA5 representa uma grade regional (~25 km), não medições dentro de Heliópolis.")
    st.caption("Fonte meteorológica: [Open-Meteo / Copernicus ERA5](https://open-meteo.com/en/docs/historical-weather-api).")
    mostrar_arquitetura()


if __name__ == "__main__":
    main()
