from datetime import datetime
from pathlib import Path

import pytest

REPORTS_DIR = Path(__file__).parent / "reports"


@pytest.fixture(autouse=True)
def backtest_report(request, capsys):
    """
    Save what each backtest prints into reports/<exchange>/<test name>_<date>_<time>.txt.
    Written even when the test fails. With -s, the output is still shown in the terminal.
    """
    started_at = datetime.now()
    yield
    output = capsys.readouterr().out
    if not output.strip():
        return

    exchange = request.node.path.parent.name  # "coinbase" or "binance"
    path = REPORTS_DIR / exchange / f"{request.node.name}_{started_at:%Y-%m-%d_%H%M%S}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"# {request.node.nodeid}\n# Run at {started_at:%Y-%m-%d %H:%M:%S}\n"
    path.write_text(header + output)
    print(f"Report    : {path.relative_to(request.config.rootpath)}")
