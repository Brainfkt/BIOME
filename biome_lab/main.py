from __future__ import annotations


def main() -> None:
    try:
        from biome_lab.config.defaults import create_default_preset
        from biome_lab.ui.app import BiomeLabApp
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        raise SystemExit(
            "Missing dependency '%s'. Install the project with: python -m pip install -e \".[dev]\""
            % missing
        )

    preset = create_default_preset()
    app = BiomeLabApp(preset)
    app.run()


if __name__ == "__main__":
    main()
