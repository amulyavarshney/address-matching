"""ASGI entrypoint. Prefer importing the library via `app` for embedding."""

from dotenv import load_dotenv

load_dotenv()

from app.factory import create_app  # noqa: E402

app = create_app(apply_env=True)

if __name__ == "__main__":
    import uvicorn

    host = app.state.matcher_config.get("api_host", "0.0.0.0")
    port = int(app.state.matcher_config.get("api_port", 8000))
    uvicorn.run(app, host=host, port=port)
