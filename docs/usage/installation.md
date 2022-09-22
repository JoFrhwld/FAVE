# Installing FAVE 2

## Required software

FAVE sometimes requires other software libraries in order to work.
: - FAVE-align requires [SoX](http://sox.sourceforge.net/) and [HTK](https://htk.eng.cam.ac.uk/).
  - FAVE-extract requires [Praat](https://www.fon.hum.uva.nl/praat/).

You will need to manually install these if they are not already installed on your computer.

:::{warning}
Mac users: HTK might need slight modification before it works. See [this bug report](https://github.com/JoFrhwld/FAVE/issues/48).
:::

## Install with PIP

FAVE is available on the Python Package Index (PyPI) as `fave`. You can install it using:

```console
python3 -m pip install fave
```

### Other package managers

Work is ongoing to publish FAVE as a debian package, but no other package system is supported at the moment. If you would like to package FAVE for your system, please feel free to {doc}`contribute <../contributing>`!
