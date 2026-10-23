"""Inicia o dashboard: python -m streamlit run app.py.

Este é o ponto de partida do programa: ele só chama a função main() do arquivo
painel.py, que monta a página. Não há cálculo nem coleta de dados aqui.
"""
from painel import main

if __name__ == "__main__":
    main()
