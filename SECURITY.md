# Privacy and demonstration scope

This is an independently developed research software project integrating with the BioBeat API. BioBeat did not develop this application. The original neutral waveform icon is part of this project.

The portfolio demonstration uses only deterministic synthetic measurements and the fictional device ID `DEMO-001`. Use the guided `run_demo.py` launcher or `python main.py --demo` for automatic loading; no API credentials are needed and this mode makes no API requests.

Live integration requires separately authorized BioBeat API access. Do not commit credentials, real device or participant identifiers, recordings, generated plot HTML, logs, or filled configuration files. CSV exports and temporary plots can contain sensitive information during live use.

The public portfolio should be created from a reviewed source snapshot with fresh Git history. Never import research repository branches, tags, old executables, or its private audit inventory. A new repository does not erase copies already published elsewhere.

Automated tests use mocked requests. Demo screenshots and CSV exports use synthetic data only. Live API compatibility and platform-specific executable distribution require separate verification. This project is for research data exploration, not certified medical use or clinical decision support.

When reporting a bug, use synthetic examples. Do not attach live responses, credentials, participant data, device identifiers, or sensitive logs to public issues.

The synthetic recording captures application-owned widgets and export dialogs only. The launcher offers dependency setup in the local `.venv` after confirmation; noninteractive installation requires `--setup`. CI uses mocked/synthetic inputs only, and its WebEngine sandbox adjustment is confined to an ephemeral virtual display job.
