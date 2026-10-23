"""Testes da seção "Calor e internações": leitura da tabela, comparação e textos.

Os valores artificiais deste arquivo existem SOMENTE para testar o comportamento do
código. O aplicativo nunca os carrega: ele lê dados_saude/internacoes_diarias_sp.csv.
"""

from datetime import date
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from interpretacao import SAUDE_TITULO, leitura_faixas, leitura_saude
from saude import (BASE_SAUDE, FAIXAS_TEMPERATURA, MINIMO_DIAS_QUENTES, carregar_internacoes,
                   comparar_dias_quentes, comparar_por_faixas, comparar_todos, serie_diaria)
from test_interpretacao import conjunto_de, horarios_sazonais
from test_relatorio import conjunto_exemplo

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def diario_artificial(dias_quentes=0.2, semente=1):
    """Dois anos de dias válidos; uma fração deles marcada como quente, ao acaso."""
    indice = pd.date_range("2021-01-01", "2022-12-31", name="data")
    quente = pd.Series(np.random.default_rng(semente).random(len(indice)) < dias_quentes,
                       index=indice).astype("boolean")
    return pd.DataFrame({"dia_valido": True, "dia_quente": quente}, index=indice)


def internacoes_artificiais(diario, efeito=0.0, semente=2):
    """Internações com padrão de dia da semana e de mês, e um aumento só nos dias quentes."""
    rng = np.random.default_rng(semente)
    base = 400 * (1 - 0.3 * (diario.index.dayofweek >= 5)) * (1 + 0.2 * np.cos(2 * np.pi * diario.index.month / 12))
    contagem = rng.poisson(base * (1 + efeito * diario.dia_quente.astype(float)))
    return pd.Series(contagem, index=diario.index)


class TestComparacao(unittest.TestCase):
    def test_detecta_aumento_real_nos_dias_quentes(self):
        diario = diario_artificial()
        resultado = comparar_dias_quentes(diario, internacoes_artificiais(diario, efeito=0.20))
        self.assertTrue(resultado["conclusivo"])
        self.assertAlmostEqual(resultado["variacao_pct"], 20, delta=3)
        self.assertGreater(resultado["ic_inf_pct"], 0)
        self.assertLess(resultado["ic_inf_pct"], resultado["variacao_pct"])
        self.assertLess(resultado["variacao_pct"], resultado["ic_sup_pct"])

    def test_sem_efeito_o_intervalo_inclui_zero(self):
        diario = diario_artificial()
        resultado = comparar_dias_quentes(diario, internacoes_artificiais(diario, efeito=0.0))
        self.assertTrue(resultado["conclusivo"])
        self.assertLess(abs(resultado["variacao_pct"]), 3)
        self.assertLessEqual(resultado["ic_inf_pct"], 0)
        self.assertGreaterEqual(resultado["ic_sup_pct"], 0)

    def test_padrao_de_fim_de_semana_nao_vira_efeito_do_calor(self):
        # Dias quentes só em sábados: sem o ajuste por dia da semana, pareceriam ter menos internações.
        diario = diario_artificial(dias_quentes=0.0)
        sorteio = np.random.default_rng(3).random(len(diario)) < 0.6
        diario["dia_quente"] = pd.Series((diario.index.dayofweek == 5) & sorteio, index=diario.index).astype("boolean")
        resultado = comparar_dias_quentes(diario, internacoes_artificiais(diario, efeito=0.0))
        self.assertLess(resultado["media_quentes"], resultado["media_demais"] * 0.85)
        self.assertLess(abs(resultado["variacao_pct"]), 4)

    def test_poucos_dias_quentes_nao_gera_conclusao(self):
        diario = diario_artificial(dias_quentes=0.0)
        diario.loc[diario.index[:MINIMO_DIAS_QUENTES - 1], "dia_quente"] = True
        resultado = comparar_dias_quentes(diario, internacoes_artificiais(diario))
        self.assertFalse(resultado["conclusivo"])
        self.assertEqual(resultado["dias_quentes"], MINIMO_DIAS_QUENTES - 1)
        self.assertTrue(np.isnan(resultado["variacao_pct"]))

    def test_dias_invalidos_ficam_de_fora(self):
        diario = diario_artificial()
        serie = internacoes_artificiais(diario)
        diario.loc[diario.index[:100], "dia_valido"] = False
        diario.loc[diario.index[:100], "dia_quente"] = pd.NA
        resultado = comparar_dias_quentes(diario, serie)
        self.assertEqual(resultado["dias_quentes"] + resultado["dias_comparacao"], len(diario) - 100)

    def test_periodo_sem_dados_de_saude_nao_quebra(self):
        diario = diario_artificial()
        vazia = pd.Series(dtype=float, index=pd.DatetimeIndex([], name="data"))
        resultado = comparar_dias_quentes(diario, vazia)
        self.assertFalse(resultado["conclusivo"])
        self.assertEqual(resultado["dias_quentes"], 0)

    def test_resultado_e_reprodutivel(self):
        diario = diario_artificial()
        serie = internacoes_artificiais(diario, efeito=0.1)
        self.assertEqual(comparar_dias_quentes(diario, serie), comparar_dias_quentes(diario, serie))


class TestTextos(unittest.TestCase):
    def tabela(self, efeito):
        diario = diario_artificial()
        linhas = pd.DataFrame({"idade": ["Todas as idades"],
                               **{k: [v] for k, v in comparar_dias_quentes(
                                   diario, internacoes_artificiais(diario, efeito=efeito)).items()}})
        linhas.insert(0, "grupo", "Doenças respiratórias")
        return linhas

    def test_sem_diferenca_texto_diz_que_nao_encontrou(self):
        texto = leitura_saude(self.tabela(0.0), 30.0)
        self.assertIn("não encontramos diferença", texto)
        self.assertIn("não quer dizer que o calor não afete a saúde", texto)

    def test_com_diferenca_texto_alerta_sobre_acaso_e_causa(self):
        texto = leitura_saude(self.tabela(0.20), 30.0)
        self.assertIn("não inclui o zero", texto)
        self.assertIn("não prova causa", texto)
        self.assertNotIn("causa internações", texto)

    def test_sem_dias_suficientes_orienta_o_usuario(self):
        diario = diario_artificial(dias_quentes=0.0)
        tabela = comparar_todos(diario, pd.DataFrame({"data": diario.index, "grupo_cid": "I00-I99",
                                                      "faixa_etaria": "65+", "n_internacoes": 10}))
        self.assertIn("Escolha \"Todo o período\" ou reduza o limiar", leitura_saude(tabela, 38.0))


class TestBaseDeSaude(unittest.TestCase):
    def test_tabela_do_projeto_esta_completa_e_sem_dados_pessoais(self):
        tabela = carregar_internacoes()
        self.assertIsNotNone(tabela)
        self.assertEqual(list(tabela.columns), ["data", "grupo_cid", "faixa_etaria", "n_internacoes"])
        self.assertEqual(tabela.data.min(), pd.Timestamp("2021-01-01"))
        self.assertEqual(tabela.data.max(), pd.Timestamp("2025-12-31"))
        self.assertEqual(len(tabela), 1826 * 2 * 4)
        self.assertFalse(tabela.duplicated(["data", "grupo_cid", "faixa_etaria"]).any())
        self.assertTrue((tabela.n_internacoes >= 0).all())
        self.assertEqual(set(tabela.grupo_cid), {"I00-I99", "J00-J99"})

    def test_serie_diaria_soma_as_faixas_escolhidas(self):
        tabela = carregar_internacoes()
        todas = serie_diaria(tabela, "I00-I99", ["0-14", "15-64", "65+", "sem idade"])
        idosos = serie_diaria(tabela, "I00-I99", ["65+"])
        self.assertEqual(len(todas), 1826)
        self.assertTrue((todas >= idosos).all())

    def test_arquivo_ausente_devolve_none(self):
        self.assertIsNone(carregar_internacoes(BASE_SAUDE.with_name("nao_existe.csv")))


class TestFaixasDeTemperatura(unittest.TestCase):
    def diario_com_temperatura(self):
        diario = diario_artificial(dias_quentes=0.0)
        dia_do_ano = np.asarray(diario.index.dayofyear)
        ruido = np.random.default_rng(5).normal(0, 2.5, len(diario))
        diario["temp_max_c"] = 25 + 6 * np.cos(2 * np.pi * (dia_do_ano - 20) / 365) + ruido
        return diario

    def test_faixas_cobrem_todos_os_dias_validos_sem_sobrepor(self):
        diario = self.diario_com_temperatura()
        faixas = comparar_por_faixas(diario, pd.DataFrame({
            "data": diario.index, "grupo_cid": "I00-I99", "faixa_etaria": "65+", "n_internacoes": 100}))
        parte = faixas[faixas.grupo == "Doenças do coração e da circulação"]
        self.assertEqual(int(parte.dias_quentes.sum()), len(diario))
        self.assertEqual(list(parte.ordem), list(range(len(FAIXAS_TEMPERATURA))))

    def test_aumento_so_na_faixa_mais_quente_aparece_so_nela(self):
        diario = self.diario_com_temperatura()
        diario["dia_quente"] = diario.temp_max_c >= 30
        n = internacoes_artificiais(diario.assign(dia_quente=diario.temp_max_c >= 30), efeito=0.15)
        tabela = pd.DataFrame({"data": diario.index, "grupo_cid": "I00-I99", "faixa_etaria": "65+",
                               "n_internacoes": n.to_numpy()})
        faixas = comparar_por_faixas(diario, tabela)
        parte = faixas[faixas.grupo == "Doenças do coração e da circulação"].set_index("faixa")
        self.assertGreater(parte.loc["30 °C ou mais", "ic_inf_pct"], 5)
        self.assertLess(abs(parte.loc["20 a 24 °C", "variacao_pct"]), 5)

    def test_texto_das_faixas_cita_maior_e_menor(self):
        diario = self.diario_com_temperatura()
        tabela = pd.DataFrame({"data": diario.index, "grupo_cid": "J00-J99", "faixa_etaria": "65+",
                               "n_internacoes": 50})
        texto = leitura_faixas(comparar_por_faixas(diario, tabela))
        self.assertIn("não depende do limiar", texto)
        self.assertIn("não provam causa", texto)

    def test_painel_com_dois_anos_desenha_o_grafico_por_faixa(self):
        conjunto = conjunto_de(horarios_sazonais(), date(2021, 1, 1), date(2022, 12, 31))
        painel = AppTest.from_file(APP, default_timeout=60)
        painel.session_state["conjunto"] = conjunto
        painel.run()
        self.assertFalse(painel.exception)
        self.assertTrue(any("Ver os números por faixa" in e.label for e in painel.expander))
        self.assertEqual(len(painel.metric), 4)
        painel.slider(key="limiar").set_value(26.0).run()
        self.assertFalse(painel.exception)


class TestSecaoNoPainel(unittest.TestCase):
    def test_secao_aparece_sem_erro_e_sem_novos_cartoes(self):
        painel = AppTest.from_file(APP, default_timeout=60)
        painel.session_state["conjunto"] = conjunto_exemplo()
        painel.run()
        self.assertFalse(painel.exception)
        self.assertTrue(any(SAUDE_TITULO in t.value for t in painel.subheader))
        self.assertEqual(len(painel.metric), 4)


if __name__ == "__main__":
    unittest.main()
