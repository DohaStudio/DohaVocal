"""Local development entry point for the Fake foundation runtime."""


def main() -> None:
    import uvicorn

    uvicorn.run("dohavocal.api.app:app", host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
