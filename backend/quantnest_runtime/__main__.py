"""Launch QuantNest services as a module, directory, or Python script."""
if not __package__:
    import sys
    from pathlib import Path

    backend_directory = str(Path(__file__).resolve().parents[1])
    if backend_directory not in sys.path:
        sys.path.insert(0, backend_directory)

from quantnest_runtime.cli import main


if __name__ == "__main__":
    main()
