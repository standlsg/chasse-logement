from chasse_logement.cli import _ensure_config, main


def test_ensure_config_copies_baked_on_first_boot(tmp_path, monkeypatch):
    baked = tmp_path / "config.yaml"
    baked.write_text("budget: 1", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "data" / "config.yaml"
    assert _ensure_config(str(dest)) == str(dest)
    assert dest.read_text(encoding="utf-8") == "budget: 1"


def test_ensure_config_keeps_existing(tmp_path, monkeypatch):
    baked = tmp_path / "config.yaml"
    baked.write_text("budget: 1", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "data" / "config.yaml"
    dest.parent.mkdir()
    dest.write_text("budget: 2800", encoding="utf-8")
    _ensure_config(str(dest))
    assert dest.read_text(encoding="utf-8") == "budget: 2800"


def test_run_missing_config_returns_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["run", "--config", "nope.yaml"]) == 2
    assert "introuvable" in capsys.readouterr().err
