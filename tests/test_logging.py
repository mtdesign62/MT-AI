from mt_ai.config import AppPaths
from mt_ai.logging_config import configure_logging, get_logger


def test_logging_creates_rotating_log_file(tmp_path):
    paths = AppPaths(
        root=tmp_path,
        models=tmp_path / "models",
        projects=tmp_path / "projects",
        cache=tmp_path / "cache",
        logs=tmp_path / "logs",
        settings=tmp_path / "settings.json",
    ).ensure()
    log_file = configure_logging(paths)
    get_logger("test").warning("diagnostic-test")
    for handler in get_logger().handlers:
        handler.flush()
    assert log_file.exists()
    assert "diagnostic-test" in log_file.read_text(encoding="utf-8")
