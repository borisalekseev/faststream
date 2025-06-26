import pytest

from tests.cli.conftest import FastStreamCLIFactory, GenerateTemplateFactory
from tests.marks import skip_windows


@pytest.mark.slow()
@skip_windows
@pytest.mark.parametrize(
    ("app_import"),
    (
        pytest.param(
            "from faststream import FastStream",
            id="default_app",
        ),
        pytest.param(
            "from faststream.asgi import AsgiFastStream",
            id="asgi_app",
        ),
    ),
)
@pytest.mark.parametrize(
    ("log_strings", "cli_options"),
    (
        pytest.param(
            ["Worker id is None"],
            [],
            id="single_worker",
        ),
        pytest.param(
            ["Worker id is 0", "Worker id is 1"],
            ["--workers", "2"],
            id="many_workers",
        ),
    ),
)
def test_worker_id_parameter_exists(
    generate_template: GenerateTemplateFactory,
    faststream_cli: FastStreamCLIFactory,
    app_import: str,
    log_strings: list[str],
    cli_options: list[str],
) -> None:
    app_code = f"""
    import logging

    {app_import} as FastStreamApp
    from faststream.nats import NatsBroker

    logger = logging.getLogger("faststream")

    broker = NatsBroker()
    app = FastStreamApp(broker)

    @app.on_startup
    def print_log_level(worker_id):
        logger.critical("Worker id is %s", worker_id)
    """

    with (
        generate_template(app_code) as app_path,
        faststream_cli(
            "faststream",
            "run",
            f"{app_path.stem}:app",
            *cli_options,
        ) as cli,
    ):
        assert all(cli.wait_for_stderr(log_string, timeout=4) for log_string in log_strings)
