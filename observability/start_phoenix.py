"""
Start a local Arize Phoenix server on http://localhost:6006.

Usage:
    python -m observability.start_phoenix
    # or
    python observability/start_phoenix.py
"""

import phoenix as px


def main() -> None:
    # Launch Phoenix to receive traces from your app.
    #
    # If you prefer the CLI, you can instead run:
    #   phoenix serve
    #
    # But for your project, a Python entrypoint is convenient.
    session = px.launch_app()
    url = session.url if hasattr(session, "url") else "http://localhost:6006"
    print(f"✅ Phoenix is running. Open {url} in your browser.")


if __name__ == "__main__":
    main()
