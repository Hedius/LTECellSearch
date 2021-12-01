#!/bin/bash
git submodule update --init

# itpp
sudo dnf install -y cmake blas-devel fftw-devel lapack-devel
cd itpp && mkdir build && cd build && \
cmake .. && make && sudo make install

# Hackrf libs & utils
sudo dnf install -y hackrf hackrf-devel hackrf-static hackrf-doc


# LTE-Cell-Scanner
sudo dnf install -y boost-devel boost-thread boost-system ncurses-devel
cd ../../LTE-Cell-Scaner && mkdir build && cd build && \
cmake ../ -DUSE_HACKRF=1 && make && sudo make install


# libitpp.so.8 => not found
# broken link for CellSearch
# existing libs
# /usr/local/lib/libitpp.so.8.2.1
# /usr/local/lib/libitpp.so.8
# /usr/local/lib/libitpp.so
sudo ln -sf /usr/local/lib/libitpp.so.8.2.1 /usr/lib64/libitpp.so.8


# GNU Radio
sudo dnf install -y gnuradio gnuradio-devel gnuradio-doc gnuradio-examples python3-gnuradio

# UHD - actually not needed for hackrf
sudo dnf install -y uhd uhd-devel


sudo dnf install -y log4cpp-devel mpir-devel gmp-devel gr-osmosdr-devel mbedtls-devel
