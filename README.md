This is an old project I used as part of my bachelor thesis. (No support!)

The main tool is **LTESnifferRunner.py**. Check the Config folder and adjust the settings as needed.

The code itself is wrapper for the HackRF and LTECellSearch command line tools.

This tool performs a search on the known 4G bandwidths and performs then a recording of the PBCH channels.

It uses the bandwith definitions of the Austrian telecom regulator RTR GmbH to map frequencies to one of the 3 Austrian providers (3, Magenta, A1).

You can then use 4G suite of MATLAB for extracting the MIB/SIB of the LTE cells.

# Requirements
You need a [HackRF One SDR](https://greatscottgadgets.com/hackrf/one/) with the latest firmware.
* HackRFOne
* libblas
* libitpp
* libfftw3
* libboost
* libhackrfone
* libncurses
* HackRFOne command line tools
* LTECellSearch command line tool

A simple setup script is below.

# Usage
```
usage: LTESnifferRunner.py [-h] [-c CONFIG_FILE] [-vc] [-f] [-l {debug,info,warning,error,critical}] [--disable-log-stdout] [--disable-log-file] [--log-syslog]

Simple tool for automation of LTE/4G cell searches and information gathering using HackRF + LTE-Cell-Scanner + MATLAB.

options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config CONFIG_FILE
                        Optional name of a custom config file. The file has to be in the folder 1_Config!Default: settings.toml
  -vc, --validate-config
                        Only validate the config.
  -f, --fast-scan       Perform a fast scan and only scan known cells.

Logging:
  Logging configuration. All arguments are optional.

  -l {debug,info,warning,error,critical}, --loglevel {debug,info,warning,error,critical}
                        Loglevel (Default: Debug)
  --disable-log-stdout  Enable logging to stdout. (Default: True)
  --disable-log-file    Enable logging to files. (Default: True)
  --log-syslog          Enable logging to syslog. (Default: False)
```

# Setup
1. Install the python dependencies (use a venv!) `pip3 install -r requirements.txt`
2. Clone all submodules.
3. Use the code below to install/compile all needed libs (blas, fftw3, itpp, boost, hackrf, ncurses), + LTE-Cell-Scanner. (debian 10)
```sh
#!/bin/bash
git submodule update --init
sudo apt install hackrf cmake libblas-dev liblapack-dev fftw3-dev -y
cd itpp
mkdir build
cd build
cmake ..
make
sudo make install
cd ../../LTE-Cell-Scanner
mkdir build
cd build
sudo apt install libboost-dev libboost-thread-dev libboost-system-dev libncurses-dev libhackrf-dev
cmake ../ -DUSE_HACKRF=1
make
sudo make install


# open lte
sudo apt install gnuradio-dev gr-osmosdr libuhd-dev libbladerf-dev pkg-config libmbedtls-dev swig
```

# License
* GPLv3
