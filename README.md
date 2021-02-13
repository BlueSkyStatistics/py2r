### Requirements
- [R 3.x](https://cran.r-project.org/bin/windows/base/old/) Better to install from CRAN than from Brew, as brew is limited version
- [python3.7](https://www.python.org/downloads/release/python-374/)
- [rpy2](https://rpy2.bitbucket.io) (may be complicated to install on Windows)
- [pip](https://pip.pypa.io/en/stable/installing/) (Make sure you installing it for python3)

Within Python world it is recommended to use [virtual environment](https://docs.python.org/3/tutorial/venv.html) for development. Please consider using it to make your code transferable. 

##### Running Backend

_NOTE: This is Python3.7 project with legacy `rpy2==2.9.5` which is the latest version installable on Windows_

To run it you need install requirements using `pip`. Within the `py2rbackend` folder run: 

```bash
pip3 install -r requirements.txt
```

there are number of environment variables required to make it work - `PYTHONPATH, R_HOME, R_USER`

installation of requirements done only once.

Then to run enter `python3 console.py`. 

This is pretty much it now type into console something like
```bash
r {"cmd":"pi","eval": false}
```
and get a ton of R things in return!
