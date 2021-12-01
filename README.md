This is an old project I used as part of my bachelor thesis. (No support!)

It uses the bandwith definitions of the Austrian telecom regulator RTR GmbH to perform a LTE CellSearch on all bandwiths.
Furthermore, it performs a recording on the broadcast channel of the cell for later (MIB/SIB) processing.

You need a [HackRF One SDR](https://greatscottgadgets.com/hackrf/one/) with the latest firmware.



# Requirements
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
