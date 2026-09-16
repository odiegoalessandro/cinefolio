"""Permite iniciar o Cinefolio com ``python -m server``."""

from server.main import main

# __main__.py é um arquivo especial: quando existe, permite rodar o pacote
# diretamente com "python -m server" (sem precisar saber o nome exato do
# arquivo main.py por dentro). É aqui que essa "porta de entrada" chama
# a função main() de verdade.
main()
