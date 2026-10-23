"""Gera a mesma análise pela linha de comando, sem abrir o dashboard.

Exemplo:
    python gerar_relatorio.py --inicio 2021-01-01 --fim 2025-12-31

A primeira execução consulta a internet. Os arquivos resultantes ficam em
dados_locais/ (ou na pasta --saida). Uma nova execução substitui esses arquivos.
Para repetir a análise offline, use --arquivo caminho/heliopolis_open_meteo.json.
O arquivo será recortado ao intervalo --inicio/--fim, por padrão 2021–2025.
"""

import argparse
from datetime import date
import json
from pathlib import Path

from analise import (episodios_quentes, gerar_relatorio, indicadores_diarios,
                     indicadores_noturnos, resumo_anual)
from dados import (ErroDados, FIM_ESTUDO, INICIO_ESTUDO, buscar_open_meteo,
                   carregar_json, exportar_json, recortar_periodo)


def main():
    # Define as opções que podem ser digitadas no terminal (--inicio, --fim, --saida, --arquivo).
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=date.fromisoformat, default=INICIO_ESTUDO)
    parser.add_argument("--fim", type=date.fromisoformat, default=FIM_ESTUDO)
    parser.add_argument("--saida", type=Path, default=Path(__file__).parent / "dados_locais")
    parser.add_argument("--arquivo", type=Path, help="JSON salvo, recortado ao período solicitado")
    argumentos = parser.parse_args()
    # Obtém os dados: de um arquivo salvo, se --arquivo foi informado; senão, da internet.
    try:
        conjunto = (carregar_json(argumentos.arquivo.read_bytes()) if argumentos.arquivo
                    else buscar_open_meteo(argumentos.inicio, argumentos.fim))
        conjunto = recortar_periodo(conjunto, argumentos.inicio, argumentos.fim)
    except (ErroDados, OSError) as erro:
        parser.exit(1, f"Não foi possível gerar o relatório: {erro}\n")
    # Critérios fixos deste script: dia quente com 30 °C ou mais, sequência de 3 dias e
    # cobertura mínima de 90% (o painel permite mudar o limiar; este script, não).
    limiar, minimo, cobertura = 30.0, 3, 0.9
    diario = indicadores_diarios(conjunto["horarios"], limiar, cobertura)
    noites = indicadores_noturnos(conjunto["horarios"], cobertura)
    episodios = episodios_quentes(diario, minimo)
    # Salva os resultados na pasta de saída: o JSON de origem, uma tabela CSV para cada
    # análise, o relatório em texto e os parâmetros usados.
    argumentos.saida.mkdir(parents=True, exist_ok=True)
    (argumentos.saida / "heliopolis_open_meteo.json").write_bytes(exportar_json(conjunto))
    for nome, tabela in {"serie_horaria": conjunto["horarios"], "serie_diaria": diario,
                        "serie_noturna": noites, "episodios": episodios,
                        "resumo_anual": resumo_anual(diario), "qualidade": conjunto["qualidade"]}.items():
        tabela.to_csv(argumentos.saida / f"{nome}.csv", sep=";", decimal=",", encoding="utf-8-sig")
    relatorio = gerar_relatorio(conjunto, diario, noites, episodios, limiar, minimo, cobertura)
    (argumentos.saida / "relatorio_inicial.txt").write_text(relatorio, encoding="utf-8-sig")
    parametros = {"limiar_c": limiar, "minimo_dias": minimo, "cobertura_minima": cobertura,
                   "metadados": conjunto["metadados"]}
    (argumentos.saida / "parametros.json").write_text(
        json.dumps(parametros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Relatório salvo em: {argumentos.saida.resolve()}")
    print(f"Horas: {len(conjunto['horarios'])}; dias válidos: {int(diario.dia_valido.sum())}; episódios: {len(episodios)}")


if __name__ == "__main__":
    main()
