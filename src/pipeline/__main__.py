"""`python -m src.pipeline [config.yaml]`: validate a config file and print which components it switches on.

Loads no model and contacts no server.
"""
import sys
import warnings

from src.config.app_config import load_config
from src.pipeline.describe import format_pipeline


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    path = args[0] if args else None
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        try:
            config = load_config(path)
        except (OSError, ValueError) as exc:
            print(f"Invalid configuration: {exc}", file=sys.stderr)
            return 1
    print(format_pipeline(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
