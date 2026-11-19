# Cloudy Launcher (CLY)

A personal, open-source **Minecraft launcher for Windows**, together with a 3D
desktop pet and a local AI translation assistant. Built with Python and PySide6.

> **Language note:** This English README is the concise project guide. The
> detailed development log and user manual are maintained in Chinese — see
> [`README.md`](README.md) and [`说明文档.md`](说明文档.md).

---

## Components

The repository contains three decoupled sub-projects:

| Component | Directory | Current version | Description |
| --- | --- | --- | --- |
| **Cloudy Launcher** | `cloud_launcher/` | `1.2.0` | The main launcher: game downloads, accounts, modpacks, Java management, themes and skins. |
| **Desktop Pet** | `desktop_pet/` | `1.1.0` | A frameless, always-on-top 3D companion rendered with a real GPU pipeline. |
| **Xiaoyun AI** | `xiaoyun_ai/` | `1.1.0` | A standalone program that scans English language files and builds an in-game Simplified Chinese resource pack using a fully local model. |

## Features

### Cloudy Launcher

- **Game download & launch** — search and download vanilla games, mods,
  modpacks, shaders, resource packs and data packs; multi-threaded downloads;
  premium (Microsoft) and offline accounts; version isolation; automatic Java
  detection and game launch.
- **Modloader detection** — recognises Forge, NeoForge, Fabric and OptiFine,
  together with the real underlying Minecraft version, directly from the
  version JSON's library coordinates and main class. External modpacks dropped
  in manually are no longer mislabeled as "vanilla".
- **Smart Java management** — picks the Java major version required by each
  game version and can download a missing runtime automatically, switching
  between TUNA / Huawei Cloud mirrors (China) and Adoptium (global).
- **Modpack import & export** — CurseForge, MultiMC/Prism, MCBBS, local
  import and Modrinth `.mrpack`, with several export formats.
- **Personalization & skins** — custom logo, display name, wallpaper and
  frosted-glass themes; premium accounts sync their official skin, while
  offline accounts can import a local skin (built-in Steve / Alex included).

### Desktop Pet

- A 3D character whose head follows the mouse while the body stays still.
- Idle animations (wave, clap, eat, jump, cheer, yawn, dance, pet the dog),
  a hunger level, speech bubbles and emotion particles (hearts, notes,
  question marks, "Zzz").
- A tamed wolf companion that walks in, can be fed and petted, then leaves on
  its own; long idle periods lead to yawning and sleep.
- Feature toggles live only in the launcher; the pet itself has no settings
  UI and can only be launched through the launcher.

### Xiaoyun AI

- Scans the English language files inside the loaded Minecraft instance and
  translates them into Simplified Chinese **entirely on the local machine**.
- Produces a resource pack that can be enabled in-game; entries that already
  have a `zh_cn` translation are skipped one by one, and the job can be
  cancelled at any time.
- The released executable ships with the model and the inference engine
  bundled, so it works out of the box — no manual model selection and no
  network connection required.
- Every translation is clearly labeled as machine-generated.

## Tech stack

- **Python 3.13**
- **PySide6 6.12** — `QOpenGLWidget` for real GPU 3D rendering, QtMultimedia
  for background music
- **PyInstaller** for single-file executables
- **llama.cpp** (`llama-server`) as the local inference engine
- **DeepSeek-R1-Distill-Qwen-1.5B** (Q4_K_M quantisation) as the bundled model

## Project structure

```
Cloudy-Launcher/
├── main.py                 # Launcher entry point
├── requirements.txt        # Runtime dependencies
├── build.spec              # PyInstaller config for the launcher
├── build.bat               # One-click build script
├── LICENSE                 # GNU GPL v3
├── NOTICE.md               # Third-party licenses and attributions
├── README.md / README_EN.md
├── 说明文档.md              # Chinese user manual
├── cloud_launcher/         # Main launcher source
│   ├── ui/                 # Windows, widgets, themes, cards
│   ├── resources/          # Logos, icons, block renders, default skins
│   └── ...                 # Auth, downloads, loaders, Java, config, ...
├── desktop_pet/            # Desktop pet source
│   ├── pet_build.spec
│   └── ...
└── xiaoyun_ai/             # Xiaoyun AI source
    ├── ai_build.spec       # Bundles the model and engine at build time
    ├── bundled/            # Build-only: models/ + llama/ (not in git/source zip)
    └── ...
```

## Requirements

- Windows (the build and released binaries target Windows)
- Python 3.13 and the dependencies in `requirements.txt`
- A GPU is not required; the 1.5B model is sized for ordinary laptops and runs
  on the CPU.

## Run from source

```bat
pip install -r requirements.txt
python main.py
```

## Build executables

Launcher:

```bat
build.bat
:: equivalent to:
pyinstaller --noconfirm --clean build.spec
```

The artifact is written to `dist\云朵启动器.exe`.

Xiaoyun AI is built from inside the `xiaoyun_ai/` directory:

```bat
pyinstaller --noconfirm --clean ai_build.spec
```

The `bundled/` directory is **not** included in the source archive or in git.
To reproduce the out-of-the-box build, place the files before packaging:

- `xiaoyun_ai/bundled/models/model.gguf` — the quantised
  DeepSeek-R1-Distill-Qwen-1.5B model
- `xiaoyun_ai/bundled/llama/` — the `llama-server` executable and its
  accompanying DLLs

At runtime the packaged app resolves the model and engine from its own bundle;
if they are missing or damaged it reports that the installation may be corrupt.

## Machine translation disclaimer

**AI machine translation; it may be inaccurate and is provided for reference
only.** The generated resource pack is a machine-assisted translation, not a
professional human translation.

## License and third-party notices

- All project source code is released under the **GNU General Public License
  v3.0** (`GPL-3.0-or-later`); see [`LICENSE`](LICENSE). Each source file
  carries an SPDX header with the copyright notice `Copyright (C) 2026 小鱼`.
- The bundled model is **DeepSeek-R1-Distill-Qwen-1.5B** (MIT), based on
  **Qwen2.5** (Apache 2.0); local inference uses **llama.cpp** (MIT).
- **PySide6 / Qt** is used under the LGPL. Full runtime and build dependency
  attributions are listed in [`NOTICE.md`](NOTICE.md).

## Trademark notice

Minecraft and the in-game textures are trademarks and copyrighted assets of
Mojang Synergies AB / Microsoft. This is an independent, third-party hobby
project and is not affiliated with or endorsed by Mojang or Microsoft.

## Links

- GitHub repository: <https://github.com/Hiru-ru/Cloudy-Launcher>
- Release v1.1.0: <https://github.com/Hiru-ru/Cloudy-Launcher/releases/tag/v1.1.0>
- Quark drive (Chinese page): <https://pan.quark.cn/s/4aa803618cd0> — code `Xr9h`
- Baidu drive (Chinese page): <https://pan.baidu.com/s/1IMLRJI02QDNStaO479wetw?pwd=426e> — code `426e`
- AFDiAn support page (Chinese): <https://ifdian.net/a/stfluogea>
