import os


def test_setup_ollama_script_contains_models():
    """
    Verifica que el script setup_ollama.sh esté configurado para descargar
    los modelos requeridos: phi3 y mxbai-embed-large.
    """
    # Ruta al script setup_ollama.sh (asumiendo que se ejecuta desde la raíz del proyecto o ajustando la ruta)
    # Desde zyrabit-brain-api/api-rag/tests/../../../../setup_ollama.sh

    # Ajustar la ruta base dependiendo de dónde se ejecute pytest
    # Si se ejecuta desde zyrabit-brain-api/api-rag/
    script_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../setup_ollama.sh"))

    if not os.path.exists(script_path):
        # Intentar ruta alternativa si estamos en la raíz del repo
        script_path = os.path.abspath("setup_ollama.sh")

    assert os.path.exists(
        script_path), f"No se encontró setup_ollama.sh en {script_path}"

    with open(script_path, "r") as f:
        content = f.read()

    # Verificar que los modelos estén en la lista de descarga
    assert "phi3" in content, "El modelo 'phi3' no está en setup_ollama.sh"
    assert "mxbai-embed-large" in content, "El modelo 'mxbai-embed-large' no está en setup_ollama.sh"

    # Verificar que estén definidos en la variable MODELS_TO_PULL
    # Esto es una verificación más estricta
    assert 'MODELS_TO_PULL=("phi3" "mxbai-embed-large")' in content or \
           'MODELS_TO_PULL=("mxbai-embed-large" "phi3")' in content, \
           "La definición de MODELS_TO_PULL no coincide con lo esperado"
