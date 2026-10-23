"""Testes dos textos explicativos e dos cálculos de apoio ao dashboard.

Os valores artificiais deste arquivo existem SOMENTE para testar o comportamento do
código. Eles nunca são carregados automaticamente pelo aplicativo.
"""

from datetime import date
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from analise import (correlacao_calor_umidade, episodios_quentes, indicadores_diarios,
                     indicadores_noturnos, perfil_horario, resumo_anual)
from dados import FUSO, VARIAVEIS, grade_horaria, montar_conjunto
from interpretacao import (conclusoes, descrever_correlacao, frase_correlacao,
                           leitura_episodios, leitura_evolucao, leitura_frequencia,
                           leitura_horario, leitura_noite, leitura_umidade)
from test_relatorio import conjunto_exemplo, exemplo

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def horarios_sazonais(inicio=date(2021, 1, 1), fim=date(2022, 12, 31)):
    """Dois anos com verão mais quente, tarde mais quente e umidade inversa à temperatura."""
    indice = grade_horaria(inicio, fim)
    local = indice.tz_convert(FUSO)
    dia_do_ano = np.asarray(local.dayofyear)
    hora = np.asarray(local.hour)
    temperatura = 22 + 5 * np.cos(2 * np.pi * (dia_do_ano - 20) / 365) + 4 * np.sin(2 * np.pi * (hora - 9) / 24)
    umidade = np.clip(95 - 2.5 * (temperatura - 15), 5, 100)
    return pd.DataFrame({"temperatura_c": temperatura, "umidade_pct": umidade,
                         "vento_ms": 2.0, "radiacao_wm2": 100.0, "precipitacao_mm": 0.0}, index=indice)


def conjunto_de(horarios, inicio, fim):
    """Empacota uma tabela horária no mesmo formato da resposta do Open-Meteo."""
    resposta = {"latitude": -23.5, "longitude": -46.5, "hourly_units": {"time": "unixtime"},
                "hourly": {"time": [int(t.timestamp()) for t in horarios.index]}}
    for campo, (coluna, unidade, _) in VARIAVEIS.items():
        resposta["hourly"][campo] = horarios[coluna].tolist()
        resposta["hourly_units"][campo] = unidade
    meta = {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "modelo": "era5",
            "latitude_solicitada": -23.615, "longitude_solicitada": -46.590,
            "coletado_em_utc": "2022-12-31T00:00:00+00:00"}
    return montar_conjunto(resposta, meta)


class TestCalculosDeApoio(unittest.TestCase):
    def test_perfil_horario_e_a_media_de_cada_hora_local(self):
        horarios = exemplo()
        horarios.iloc[:, horarios.columns.get_loc("temperatura_c")] = range(len(horarios))
        perfil = perfil_horario(horarios)
        local = horarios.tz_convert(FUSO)
        esperado = local.temperatura_c.groupby(local.index.hour).mean()
        self.assertEqual(list(perfil.index), list(range(24)))
        pd.testing.assert_series_equal(perfil, esperado, check_names=False)

    def test_correlacao_negativa_e_contagem_de_dias(self):
        diario = indicadores_diarios(horarios_sazonais())
        r, dias = correlacao_calor_umidade(diario)
        self.assertEqual(dias, int(diario.dia_valido.sum()))
        self.assertLess(r, -0.99)

    def test_correlacao_sem_dias_suficientes_nao_vira_zero(self):
        diario = indicadores_diarios(exemplo(date(2024, 1, 1), date(2024, 1, 1)))
        r, dias = correlacao_calor_umidade(diario)
        self.assertEqual(dias, 1)
        self.assertTrue(pd.isna(r))
        # Temperatura constante: a correlação não existe e também não deve virar zero.
        r, dias = correlacao_calor_umidade(indicadores_diarios(exemplo()))
        self.assertEqual(dias, 5)
        self.assertTrue(pd.isna(r))


class TestTextos(unittest.TestCase):
    def test_faixas_de_correlacao(self):
        self.assertIn("nenhuma relação", descrever_correlacao(0.05))
        self.assertIn("fraca", descrever_correlacao(0.2))
        self.assertIn("moderada", descrever_correlacao(-0.4))
        self.assertIn("forte", descrever_correlacao(0.6))
        self.assertIn("muito forte", descrever_correlacao(-0.9))
        self.assertIn("negativa", descrever_correlacao(-0.9))
        self.assertIn("positiva", descrever_correlacao(0.9))
        self.assertIsNone(descrever_correlacao(float("nan")))

    def test_frase_de_correlacao_usa_numeros_brasileiros_e_nao_afirma_causa(self):
        frase = frase_correlacao(-0.87, 1826)
        self.assertIn("1.826 dias", frase)
        self.assertIn("-0,87", frase)
        self.assertNotIn("0.87", frase)
        self.assertIn("não uma causa", frase)
        self.assertIn("esperado", frase)

    def test_poucos_dias_nao_geram_interpretacao_enganosa(self):
        frase = frase_correlacao(0.99, 5)
        self.assertIn("poucos dias", frase)
        self.assertNotIn("0,99", frase)
        self.assertIn("poucos dias", leitura_umidade(float("nan"), 0))

    def test_textos_dinamicos_citam_os_numeros_do_recorte(self):
        diario = indicadores_diarios(horarios_sazonais(), limiar=26.0)
        noites = indicadores_noturnos(horarios_sazonais())
        episodios = episodios_quentes(diario)
        anual = resumo_anual(diario)
        perfil = perfil_horario(horarios_sazonais())
        r, dias = correlacao_calor_umidade(diario)
        evolucao = leitura_evolucao(diario)
        self.assertRegex(evolucao, r"jan/20\d\d|fev/20\d\d|dez/20\d\d")
        self.assertIn("26 °C", leitura_frequencia(anual, 26.0))
        self.assertIn(f"{perfil.idxmax()}h", leitura_horario(perfil))
        self.assertIn("noites válidas", leitura_noite(noites))
        self.assertIn("sequências de calor", leitura_episodios(episodios, 26.0))
        textos = [evolucao, leitura_frequencia(anual, 26.0), leitura_horario(perfil),
                  leitura_noite(noites), leitura_episodios(episodios, 26.0),
                  *conclusoes(diario, noites, episodios, perfil, 26.0, r, dias)]
        for texto in textos:
            self.assertNotIn("nan", texto.lower())

    def test_periodo_curto_mostra_o_dia_mais_quente(self):
        diario = indicadores_diarios(exemplo())
        self.assertIn("01/01/2024", leitura_evolucao(diario))
        self.assertIn("32,0 °C", leitura_evolucao(diario))

    def test_sem_dias_validos_ou_sequencias_o_texto_diz_isso(self):
        horarios = exemplo()
        horarios["temperatura_c"] = float("nan")
        diario = indicadores_diarios(horarios)
        noites = indicadores_noturnos(horarios)
        self.assertIn("Não há dias válidos", leitura_evolucao(diario))
        self.assertIn("Não há noites", leitura_noite(noites))
        self.assertEqual(len(conclusoes(diario, noites, episodios_quentes(diario),
                                        perfil_horario(horarios), 30.0, float("nan"), 0)), 1)
        self.assertIn("nenhuma sequência", leitura_episodios(episodios_quentes(diario), 30.0))

    def test_frequencia_avisa_quando_ha_ano_incompleto(self):
        diario = indicadores_diarios(horarios_sazonais(date(2021, 1, 1), date(2022, 6, 30)), limiar=26.0)
        texto = leitura_frequencia(resumo_anual(diario), 26.0)
        self.assertIn("poucos anos não bastam", texto)
        self.assertIn("com cuidado", texto)


class TestInterface(unittest.TestCase):
    def test_slider_em_destaque_explica_o_que_muda_e_o_que_nao_muda(self):
        painel = AppTest.from_file(APP, default_timeout=30)
        painel.session_state["conjunto"] = conjunto_exemplo()
        painel.run()
        self.assertFalse(painel.exception)
        self.assertTrue(any("Defina o que é um dia quente" in s.value for s in painel.subheader))
        textos = " ".join(m.value for m in painel.markdown)
        self.assertIn("Muda quando você move o controle", textos)
        self.assertIn("Não muda", textos)
        self.assertIn("30 °C ou mais", textos)
        painel.slider(key="limiar").set_value(33.0).run()
        self.assertFalse(painel.exception)
        self.assertIn("33 °C ou mais", " ".join(m.value for m in painel.markdown))

    def test_pagina_tem_fontes_interpretacoes_conclusoes_e_glossario(self):
        painel = AppTest.from_file(APP, default_timeout=30)
        painel.session_state["conjunto"] = conjunto_exemplo()
        painel.run()
        self.assertFalse(painel.exception)
        markdown = " ".join(m.value for m in painel.markdown)
        self.assertIn("De onde vêm os dados?", markdown)
        self.assertIn("ERA5", markdown)
        # Um bloco "O que isso significa" por gráfico e tabela: 5 gráficos + sequências + 2 gráficos de internações.
        self.assertEqual(markdown.count("O que isso significa"), 8)
        self.assertTrue(any(s.value == "Conclusões" for s in painel.subheader))
        rotulos = [e.label for e in painel.expander]
        self.assertTrue(any("Glossário" in r for r in rotulos))
        self.assertTrue(any("fonte" in r.lower() for r in rotulos))
        self.assertTrue(any("não permitem concluir" in i.value for i in painel.info))

    def test_conclusoes_acompanham_o_limiar(self):
        painel = AppTest.from_file(APP, default_timeout=30)
        painel.session_state["conjunto"] = conjunto_exemplo()
        painel.run()
        self.assertIn("5 de 5 dias válidos (100,0%)", " ".join(m.value for m in painel.markdown))
        painel.slider(key="limiar").set_value(33.0).run()
        self.assertIn("0 de 5 dias válidos (0,0%)", " ".join(m.value for m in painel.markdown))

    def test_varios_anos_usam_textos_mensais_e_correlacao(self):
        conjunto = conjunto_de(horarios_sazonais(), date(2021, 1, 1), date(2022, 12, 31))
        painel = AppTest.from_file(APP, default_timeout=60)
        painel.session_state["conjunto"] = conjunto
        painel.run()
        self.assertFalse(painel.exception)
        markdown = " ".join(m.value for m in painel.markdown)
        self.assertIn("Entre os meses mostrados", markdown)
        self.assertIn("coeficiente de correlação", markdown)
        self.assertIn("relação muito forte e negativa", markdown)
        # Um único ano (365 dias) volta a ser mostrado dia a dia, como o gráfico.
        painel.selectbox(key="periodo").select("2022").run()
        self.assertFalse(painel.exception)
        markdown = " ".join(m.value for m in painel.markdown)
        self.assertNotIn("Entre os meses mostrados", markdown)
        self.assertIn("O dia mais quente do recorte foi", markdown)


if __name__ == "__main__":
    unittest.main()
