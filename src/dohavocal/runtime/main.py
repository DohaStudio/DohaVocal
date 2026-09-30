"""Explicit local development composition; paths are trusted operator input only."""

import argparse
from pathlib import Path


def main() -> None:
    import uvicorn

    from dohavocal.api.app import create_app
    from dohavocal.config import RuntimeSettings
    from dohavocal.domain.errors import VocalRuntimeError

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runtime-mode", choices=("memory", "sqlite"), default="memory"
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--initialize-database", action="store_true")
    args = parser.parse_args()
    try:
        app = create_app(
            settings=RuntimeSettings(
                runtime_mode=args.runtime_mode,
                database_path=args.database,
                initialize_database=args.initialize_database,
            )
        )
    except VocalRuntimeError:
        parser.exit(
            2, "Runtime storage configuration or integrity validation failed.\n"
        )
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
