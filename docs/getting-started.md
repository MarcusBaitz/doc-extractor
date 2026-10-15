# Getting started

Substrakt is set up and started with one command. Setup is scripted for
Linux and WSL2 (Ubuntu 24.04); Windows and macOS builds are the target
platforms, but their developer setup is not scripted yet.

## Requirements

- Ubuntu 24.04 or WSL2 with Ubuntu 24.04, `sudo` rights once
- Node.js with `npm`
- Git with [Git LFS](https://git-lfs.com/) for the evaluation corpus
- About 1 GB of disk space for tools and model weights
- No GPU. The target machine is a standard laptop with 16 GB RAM.

## Install and start

```bash
git clone https://github.com/MarcusBaitz/doc-extractor.git
cd doc-extractor
git lfs install --local
npm start
```

`npm start` runs three steps (`scripts/start.sh`):

1. **`scripts/setup-dev.sh`** installs the Tauri system packages (webkit2gtk
   4.1 and others) with one `sudo` prompt, then Rust via rustup and
   [uv](https://docs.astral.sh/uv/) into your home directory, and runs
   `npm ci` and `uv sync --all-groups`.
2. **`scripts/fetch-models.sh`** downloads the model weights into `models/`
   and checks each file against a pinned SHA-256: Tesseract `deu` and `eng`
   from `tessdata_best` 4.1.0, and granite-docling-258M as GGUF.
3. The app starts. Under WSL2 it starts through `scripts/dev-wsl.sh`.

Later runs skip setup as long as the lock files and setup scripts are
unchanged. `npm start -- --fresh` forces a new setup; `npm run setup` sets up
without starting.

**Downloads happen only here.** The running application fetches nothing:
no models, fonts, updates or telemetry.

## WSL2

Use `npm run app:wsl` instead of `npm run app`. WSLg passes no GPU to
WebKitGTK; without the four switches in `scripts/dev-wsl.sh`, Mesa reports
errors and the window does not render reliably. On a regular Linux desktop
`npm run app` is enough.

## First steps in the app

The interface has four places:

| Place | Question it answers |
|---|---|
| Übersicht (Overview) | Is everything running? Do I need to do anything? |
| Prüfen (Review) | These documents were not unambiguous. |
| Vorlagen (Templates) | Which kinds of documents does the program know? |
| Einstellungen (Settings) | Behaviour, privacy, technical details |

To teach Substrakt a new kind of document, go to **Vorlagen → Neue Vorlage**.
The assistant asks for a sample document, the values to extract, shows the
result and returns you to everyday use. German is the default interface
language. Choose **Einstellungen → Sprache** to switch to English; in English,
the same choice is under **Settings → Language**.

To try it without real documents, generate the synthetic test corpus:

```bash
npm run corpus        # writes PDFs to corpus/out/
```

Never put real documents into the repository. `corpus/echt/` is ignored by Git
for local real-world tests.

## Next

- [Architecture](architecture/README.md): how the three processes work together
- [Configuration](configuration.md): operating modes, policy file, directories
- [Development](development.md): commands, tests and project layout
