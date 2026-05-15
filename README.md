# INSTALLATION
## Environment variables required to work:
- "R_HOME" - path to R folder
- "R_HOME_DIR" - same as R_HOME, but required by R executable
### Installation
1. Python 3.13+
2. Install UV `pip install uv`
3. Install project dependencies `uv sync`

### Distribution
Run `./venv/bin/pyinstaller console.spec` it will build executable `RConsole` in `dist` folder

