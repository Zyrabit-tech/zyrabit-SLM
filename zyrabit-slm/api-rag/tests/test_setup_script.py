import os


def test_zyra_up_defaults_to_qwen_family():
    script_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../zyra-up.sh"))

    if not os.path.exists(script_path):
        script_path = os.path.abspath("zyra-up.sh")

    assert os.path.exists(script_path), f"zyra-up.sh not found in {script_path}"

    with open(script_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "qwen2.5:7b" in content
    assert "qwen2.5:1.5b" in content
    assert "nvidia-smi" in content
    assert "Darwin" in content
    assert 'COMMANDS=("install")' in content
    assert "run_doctor()" in content
    assert "install)" in content
    assert "doctor)" in content
