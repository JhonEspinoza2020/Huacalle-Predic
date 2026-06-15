import os

# Desactiva login obligatorio en la suite existente de pytest.
os.environ.setdefault("PREDICTEDU_AUTH", "0")
