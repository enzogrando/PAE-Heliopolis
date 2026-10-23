"""Coleta e leitura dos dados. Dependências externas: somente Pandas.

A conexão HTTP usa urllib, que já vem com o Python. Nenhum dado fictício é
inserido se a API falhar: o erro é apresentado para quem estiver usando o painel.

Como ler este arquivo (para quem não programa):
    Aqui ficam as funções que OBTÊM e ORGANIZAM os dados de temperatura, umidade,
    vento, radiação e chuva. O caminho é sempre o mesmo:
      1. buscar_open_meteo pede os dados ao Open-Meteo pela internet (ou
         carregar_json lê um arquivo salvo, com o mesmo formato);
      2. interpretar_api confere se a resposta está completa e correta;
      3. limpar_horarios organiza uma linha por hora e marca como "vazio" o que faltar ou
         for impossível (por exemplo, umidade acima de 100%), sem inventar valores;
      4. montar_conjunto junta a tabela, o relatório de qualidade e a origem dos dados
         em um único pacote, que a página usa.
    Os horários são guardados em UTC (horário universal) e só são convertidos para o
    horário de São Paulo na hora de agrupar em dias ou mostrar na tela.
"""

from datetime import date, datetime, timedelta, timezone
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


# Fuso horário usado para definir o que é "um dia" e "uma noite" em Heliópolis.
FUSO = "America/Sao_Paulo"
# Últimos cinco anos completos na definição deste estudo (outubro de 2026).
# Fixamos o intervalo para que o relatório continue reproduzível no futuro.
INICIO_ESTUDO = date(2021, 1, 1)
FIM_ESTUDO = date(2025, 12, 31)
# Endereço (URL) do serviço do Open-Meteo que entrega o histórico do tempo (base ERA5).
ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
# Ponto aproximado de consulta, e não centroide oficial nem estação instalada.
LATITUDE = -23.615
LONGITUDE = -46.590
# Variáveis pedidas ao Open-Meteo: nome na API -> (nome usado no projeto, unidade, descrição).
VARIAVEIS = {
    "temperature_2m": ("temperatura_c", "°C", "Temperatura do ar a 2 m"),
    "relative_humidity_2m": ("umidade_pct", "%", "Umidade relativa a 2 m"),
    "wind_speed_10m": ("vento_ms", "m/s", "Vento a 10 m"),
    "shortwave_radiation": ("radiacao_wm2", "W/m²", "Radiação solar: média da hora anterior"),
    "precipitation": ("precipitacao_mm", "mm", "Precipitação: acumulado da hora anterior"),
}


class ErroDados(ValueError):
    """Mensagem de erro que pode ser mostrada diretamente no dashboard.

    É um tipo de erro próprio do projeto: quando algo dá errado com os dados, o texto
    do erro é escrito para o usuário ler, e a página o exibe em vez de travar.
    """


def validar_periodo(inicio: date, fim: date) -> None:
    """Impede períodos invertidos ou grandes demais para o relatório inicial."""
    if inicio > fim:
        raise ErroDados("A data inicial deve ser anterior ou igual à data final.")
    if inicio < date(1940, 1, 1) or (fim - inicio).days > 366 * 15:
        raise ErroDados("Escolha até 15 anos de dados, a partir de 1940.")


def grade_horaria(inicio: date, fim: date) -> pd.DatetimeIndex:
    """Cria todas as horas esperadas, respeitando o antigo horário de verão.

    Guardamos os instantes em UTC para distinguir horas locais repetidas. Só
    convertemos para São Paulo ao agrupar os dias ou apresentar os resultados.
    """
    validar_periodo(inicio, fim)
    # Primeiro instante: meia-noite local do dia inicial. Último: meia-noite local do dia
    # seguinte ao final (não incluída). Ambos são convertidos para UTC logo abaixo.
    primeiro = pd.Timestamp(inicio).tz_localize(FUSO, nonexistent="shift_forward")
    limite = pd.Timestamp(fim + timedelta(days=1)).tz_localize(
        FUSO, nonexistent="shift_forward"
    )
    return pd.date_range(primeiro.tz_convert("UTC"), limite.tz_convert("UTC"),
                         freq="h", inclusive="left", name="data_hora_utc")


def limpar_horarios(tabela: pd.DataFrame, inicio: date, fim: date):
    """Sinaliza valores inválidos e preserva lacunas, sem interpolar extremos."""
    tabela = tabela.copy()
    # Conta e remove horários repetidos, mantendo a primeira leitura de cada um.
    duplicatas = int(tabela.index.duplicated().sum())
    tabela = tabela.loc[~tabela.index.duplicated(keep="first")].sort_index()
    # Reorganiza a tabela para ter uma linha para CADA hora esperada do período:
    # horas sem leitura aparecem como vazio (NaN) em vez de desaparecerem.
    tabela = tabela.reindex(grade_horaria(inicio, fim))
    # São limites amplos de consistência, não limites de risco à saúde.
    limites = {
        "temperatura_c": (-90, 65), "umidade_pct": (0, 100),
        "vento_ms": (0, 150), "radiacao_wm2": (0, 1600),
        "precipitacao_mm": (0, 1000),
    }
    # Para cada variável: marca como vazio o que está fora do limite e registra a qualidade
    # (quantas horas válidas, ausentes e fora dos limites, e a cobertura em %).
    qualidade = []
    for coluna, (minimo, maximo) in limites.items():
        if coluna not in tabela:
            tabela[coluna] = float("nan")
        valores = pd.to_numeric(tabela[coluna], errors="coerce")
        invalidos = valores.notna() & ~valores.between(minimo, maximo)
        tabela[coluna] = valores.mask(invalidos)
        qualidade.append({
            "variavel": coluna, "horas_esperadas": len(tabela),
            "horas_validas": int(tabela[coluna].notna().sum()),
            "horas_ausentes_ou_invalidas": int(tabela[coluna].isna().sum()),
            "valores_fora_dos_limites": int(invalidos.sum()),
            "cobertura_pct": round(tabela[coluna].notna().mean() * 100, 2),
        })
    return tabela, pd.DataFrame(qualidade), duplicatas


def interpretar_api(resposta: dict, inicio: date, fim: date):
    """Valida o contrato da API antes de transformar o JSON em uma tabela."""
    if not isinstance(resposta, dict) or resposta.get("error"):
        raise ErroDados("A resposta não contém uma série válida do Open-Meteo.")
    # A resposta da API vem em JSON: "hourly" traz as listas de valores hora a hora e
    # "hourly_units" traz as unidades de cada lista.
    horas = resposta.get("hourly", {})
    unidades = resposta.get("hourly_units", {})
    if not isinstance(horas, dict) or not isinstance(horas.get("time"), list) or not horas["time"]:
        raise ErroDados("A resposta não contém observações horárias.")
    try:
        # O pedido usa unixtime para evitar offsets fixos durante o horário de verão.
        if unidades.get("time") != "unixtime":
            raise ErroDados("O arquivo deve usar timestamps Unix, como a exportação deste painel.")
        # Converte os horários (números Unix) em datas e cria uma tabela indexada por elas.
        indice = pd.to_datetime(horas["time"], unit="s", utc=True, errors="raise")
        tabela = pd.DataFrame(index=indice)
        for campo, (coluna, unidade, _) in VARIAVEIS.items():
            if campo not in horas or unidades.get(campo) != unidade:
                raise ErroDados(f"Campo ausente ou unidade inesperada: {campo} ({unidade}).")
            tabela[coluna] = horas[campo]
    except (ValueError, TypeError, OverflowError) as erro:
        raise ErroDados(f"Não foi possível interpretar a série: {erro}") from erro
    # Limpa a tabela e, se nem uma temperatura válida sobrar, interrompe com uma mensagem clara.
    tabela, qualidade, duplicatas = limpar_horarios(tabela, inicio, fim)
    if not tabela.temperatura_c.notna().any():
        raise ErroDados("Não há temperaturas válidas no período escolhido.")
    return tabela, qualidade, duplicatas


def montar_conjunto(resposta: dict, metadados: dict):
    """Reúne dados, auditoria e origem em um único objeto para a interface."""
    try:
        inicio = date.fromisoformat(metadados["inicio"])
        fim = date.fromisoformat(metadados["fim"])
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroDados("Metadados sem datas válidas de início e fim.") from erro
    tabela, qualidade, duplicatas = interpretar_api(resposta, inicio, fim)
    return {"horarios": tabela, "qualidade": qualidade,
            "duplicatas": duplicatas, "metadados": metadados, "resposta_api": resposta}


def recortar_periodo(conjunto, inicio=INICIO_ESTUDO, fim=FIM_ESTUDO):
    """Restringe dados e exportações ao intervalo, sem baixar novamente.

    Em palavras simples: recebe o conjunto de dados e devolve outro com apenas os dias
    entre "inicio" e "fim". É a função que a página usa para mostrar um ano específico.

    Mantemos os valores originais e a URL da coleta. O JSON também é recortado,
    para que o download não leve anos que ficaram fora da análise. Datas UTC
    são comparadas com as fronteiras locais: a madrugada UTC de 01/01/2026
    ainda contém horas de 31/12/2025 em São Paulo.
    """
    validar_periodo(inicio, fim)
    meta = conjunto["metadados"]
    # O intervalo pedido nunca ultrapassa o que a base realmente contém.
    inicio = max(inicio, date.fromisoformat(meta["inicio"]))
    fim = min(fim, date.fromisoformat(meta["fim"]))
    if inicio > fim:
        raise ErroDados("A base não contém dados no período do estudo (2021–2025).")
    if inicio.isoformat() == meta["inicio"] and fim.isoformat() == meta["fim"]:
        return conjunto
    # Chegando aqui, o intervalo pedido é menor que o da base: mantemos só as horas que
    # caem dentro dele (preservando os valores) e montamos um novo conjunto com elas.
    grade = grade_horaria(inicio, fim)
    resposta = conjunto["resposta_api"]
    instantes = pd.to_datetime(resposta["hourly"]["time"], unit="s", utc=True)
    dentro = (instantes >= grade[0]) & (instantes <= grade[-1])
    posicoes = [i for i, incluir in enumerate(dentro) if incluir]
    resposta_recortada = {**resposta, "hourly": {
        campo: [valores[i] for i in posicoes] for campo, valores in resposta["hourly"].items()
    }}
    metadados = {**meta, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
                "tratamento_temporal": "Resposta da API recortada ao período local indicado; valores preservados."}
    return montar_conjunto(resposta_recortada, metadados)


def buscar_open_meteo(inicio: date, fim: date, latitude=LATITUDE, longitude=LONGITUDE):
    """Busca dados reais de um único modelo (ERA5), sem misturar versões.

    Em palavras simples: monta o endereço de consulta (coordenadas, período, variáveis e
    modelo), envia o pedido ao Open-Meteo, recebe o JSON e o transforma em um conjunto de
    dados. Se a internet ou a API falharem, devolve uma mensagem de erro clara, sem dados falsos.
    """
    validar_periodo(inicio, fim)
    hoje_local = pd.Timestamp.now(tz=FUSO).date()
    if fim > hoje_local - timedelta(days=7):
        raise ErroDados("Deixe pelo menos sete dias entre o fim da consulta e hoje.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ErroDados("Coordenadas inválidas.")
    grade = grade_horaria(inicio, fim)
    # Parâmetros da consulta: onde (latitude/longitude), quando, o quê (variáveis), com qual
    # modelo (ERA5) e em quais unidades. Esses parâmetros ficam registrados na URL de origem.
    parametros = {
        "latitude": latitude, "longitude": longitude,
        "start_date": grade[0].date().isoformat(),
        "end_date": grade[-1].date().isoformat(),
        "hourly": ",".join(VARIAVEIS), "models": "era5",
        "timezone": "UTC", "timeformat": "unixtime",
        "temperature_unit": "celsius", "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
    }
    url = ENDPOINT + "?" + urlencode(parametros)
    pedido = Request(url, headers={"User-Agent": "HeliopolisPesquisa/1.0"})
    try:
        with urlopen(pedido, timeout=60) as conexao:
            resposta = json.load(conexao)
    except HTTPError as erro:
        if erro.code == 429:
            raise ErroDados("Limite de consultas atingido. Aguarde ou carregue um JSON salvo.") from erro
        raise ErroDados(f"A API respondeu com HTTP {erro.code}. Tente novamente mais tarde.") from erro
    except (URLError, TimeoutError, OSError, ValueError) as erro:
        raise ErroDados("Não foi possível acessar a API. Verifique a conexão ou carregue um JSON salvo.") from erro
    # Metadados: registram de onde vieram os dados e quando foram coletados (rastreabilidade).
    metadados = {
        "fonte": "Open-Meteo / Copernicus ERA5", "modelo": "era5",
        "resolucao": "0,25 grau (aproximadamente 25 km)",
        "inicio": inicio.isoformat(), "fim": fim.isoformat(),
        "latitude_solicitada": latitude, "longitude_solicitada": longitude,
        "latitude_retornada": resposta.get("latitude"),
        "longitude_retornada": resposta.get("longitude"),
        "elevacao_retornada_m": resposta.get("elevation"),
        "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
        "fuso_analise": FUSO, "url_consulta": url,
        "documentacao": "https://open-meteo.com/en/docs/historical-weather-api",
    }
    return montar_conjunto(resposta, metadados)


def exportar_json(conjunto: dict) -> bytes:
    """Salva os valores de origem e seus metadados para reabrir sem internet."""
    return json.dumps({"versao": 1, "metadados": conjunto["metadados"],
                       "resposta_api": conjunto["resposta_api"]},
                      ensure_ascii=False, indent=2).encode("utf-8")


def carregar_json(conteudo: bytes):
    """Aceita o formato exportado pelo painel, sem executar conteúdo do arquivo."""
    try:
        arquivo = json.loads(conteudo)
        if not isinstance(arquivo, dict) or arquivo.get("versao") != 1:
            raise ErroDados("Use um JSON exportado por este dashboard (versão 1).")
        meta = arquivo["metadados"]
        if not isinstance(meta, dict) or meta.get("modelo") != "era5":
            raise ErroDados("O arquivo deve identificar o modelo ERA5.")
        return montar_conjunto(arquivo["resposta_api"], meta)
    except (KeyError, TypeError, UnicodeError, ValueError) as erro:
        raise ErroDados(f"Arquivo JSON inválido: {erro}") from erro
