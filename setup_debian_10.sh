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