import os


def test_zyra_up_defaults_to_qwen_family():
    script_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../zyra.sh"))

    if not os.path.exists(script_path):
        script_path = os.path.abspath("zyra.sh")

    assert os.path.exists(script_path), f"zyra.sh not found in {script_path}"

    with open(script_path, "r", encoding="utf-8") as file:
        content = file.read()

    assert "qwen2.5:7b" in content
    assert "qwen2.5:3b" in content
    assert "nvidia-smi" in content
    assert "Darwin" in content
    assert "usage" in content
    assert "run_doctor()" in content
    assert "install)" in content
    assert "start)" in content
    assert "doctor)" in content
