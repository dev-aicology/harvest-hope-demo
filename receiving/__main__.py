"""Start a loopback-only local demonstrator."""
import uvicorn

from receiving.app import create_app
from receiving.config import Settings
from receiving.photos import purge_expired


def main():
    settings = Settings.from_env()
    app = create_app(settings)
    purge_expired(app.state.workflow)
    display_host = f"[{settings.host}]" if ":" in settings.host else settings.host
    print(f"Synthetic-data demo: http://{display_host}:{settings.port} — no live warehouse writes.")
    uvicorn.run(app, host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__":
    main()
