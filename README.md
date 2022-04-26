# INSTALLAION

Curenly we are running on latest version of rpy2

## Environment variables required to work:
- "R_HOME" - path to R folder
- "R_HOME_DIR" - same as R_HOME, but required by R executable

## Mac

### Installation
1. Python 3.7 - 3.8
2. Activate [venv](https://docs.python.org/3/library/venv.html) to play safe
3. install rpy2 `pip install rpy2==3.4.4 websockets==9.1`
4. install `pip install certifi==2021.10.8`
5. install `pip install urllib3==1.26.9`
6. install `pip install dulwich==0.20.35 --global-option="--pure"`
7. install `pip install paramiko==2.6.0`
8. For distribution you'd need to install pyinstaller `pip install pyinstaller==4.10`

### Distribution
Run `./venv/bin/pyinstaller console.spec` it will build executable `RConsole` in `dist` folder

