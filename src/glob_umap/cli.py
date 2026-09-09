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

    audit_parser = commands.add_parser("audit", help="audit loaded raw catalogues")
    audit_parser.add_argument("--config", required=True)

    records_parser = commands.add_parser(
        "records", help="populate normalized catalogue records"
    )
    records_parser.add_argument("--config", required=True)

    match_parser = commands.add_parser(
        "match", help="generate all configured sky-match candidates"
    )
    match_parser.add_argument("--config", required=True)

    funnel_parser = commands.add_parser(
        "funnel", help="count each configured sample-preparation stage"
    )
    funnel_parser.add_argument("--config", required=True)

    sample_parser = commands.add_parser(
        "sample", help="materialize a configured machine-learning population"
    )
    sample_parser.add_argument("--config", required=True)
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
            from psycopg import Error as DatabaseError

            try:
                ingest(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(f"PostgreSQL load failed: {error}") from error
        elif args.command == "audit":
            from glob_umap.audit import audit_raw
            from psycopg import Error as DatabaseError

            try:
                audit_raw(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(f"PostgreSQL audit failed: {error}") from error
        elif args.command == "records":
            from glob_umap.record import populate_records
            from psycopg import Error as DatabaseError

            try:
                populate_records(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(
                    f"PostgreSQL record normalization failed: {error}"
                ) from error
        elif args.command == "match":
            from glob_umap.match import match_catalogues
            from psycopg import Error as DatabaseError

            try:
                match_catalogues(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(f"PostgreSQL crossmatch failed: {error}") from error
        elif args.command == "funnel":
            from glob_umap.funnel import build_funnel
            from psycopg import Error as DatabaseError

            try:
                build_funnel(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(f"PostgreSQL sample funnel failed: {error}") from error
        elif args.command == "sample":
            from glob_umap.sample import materialize_sample
            from psycopg import Error as DatabaseError

            try:
                materialize_sample(args.config, report=print)
            except DatabaseError as error:
                raise RuntimeError(
                    f"PostgreSQL sample materialization failed: {error}"
                ) from error
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"glob-umap: error: {error}") from None
