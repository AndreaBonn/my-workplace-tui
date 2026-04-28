import sys
from pathlib import Path

from loguru import logger

from workspace_tui.app import MIN_COLUMNS, MIN_ROWS, WorkspaceTUI
from workspace_tui.config.settings import load_settings


def setup_logging() -> None:
    log_dir = str(Path("~/.local/share/workspace-tui/logs").expanduser())
    logger.remove()
    logger.add(
        f"{log_dir}/app.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
        level="DEBUG",
        serialize=True,
    )


def check_terminal_size() -> bool:
    try:
        import shutil

        columns, rows = shutil.get_terminal_size()
        if columns < MIN_COLUMNS or rows < MIN_ROWS:
            print(
                f"Terminale troppo piccolo: {columns}x{rows}. "
                f"Richiesto minimo {MIN_COLUMNS}x{MIN_ROWS}.",
                file=sys.stderr,
            )
            return False
    except Exception:
        pass
    return True


def main() -> None:
    setup_logging()
    logger.info("Avvio Workspace TUI")

    if not check_terminal_size():
        sys.exit(1)

    try:
        settings = load_settings()
    except Exception as exc:
        logger.error(f"Errore caricamento configurazione: {exc}")
        print(f"Errore configurazione: {exc}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write("\033]2;Workspace TUI\007")
    sys.stdout.flush()

    app = WorkspaceTUI(settings=settings)
    app.run()


if __name__ == "__main__":
    main()
