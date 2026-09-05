import argparse
from collections.abc import Sequence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glob-umap")
    commands = parser.add_subparsers(dest="command", required=True)

    check_parser = commands.add_parser(
        "preflight", help="verify raw catalogues without changing the database"
    )
    check_parser.add_argument("--config", required=True)

    ingest_parser = commands.add_parser("ingest", help="load raw catalogues")
    ingest_parser.add_argument("--config", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preflight":
            from glob_umap.check import check_dataset

            config, results = check_dataset(args.config)
            print(f"Dataset: {config.name}")
            for result in results:
                print(
                    f"OK  {result.name}: {result.row_count} rows, "
                    f"sha256 {result.sha256}"
                )
        elif args.command == "ingest":
            from glob_umap.ingest import ingest

            ingest(args.config)
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"glob-umap: error: {error}") from None
