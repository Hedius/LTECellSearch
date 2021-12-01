#!/bin/bash


workdir=/home/qcsuper/Software/qcsuper

# go into the workdir
cd $workdir

# create work directories
export_dir=Export
dir_pcap=$export_dir/1_pcap
dir_geo=$export_dir/2_geo_dump
dir_dlf=$export_dir/3_dlf
dir_stdout=$export_dir/4_stdout

mkdir -p $export_dir $dir_pcap $dir_geo $dir_dlf $dir_stdout

# ask for the file name
if [ $# -eq 1 ]
then
    name=$1
else
    read -p "Pls enter the name: " name
fi

# print
echo "Name for the dumps: $name"


#
echo Starting qcsuper:
# --adb \
./qcsuper.py \
	--usb-modem /dev/ttyUSB0 \
	--pcap-dump $dir_pcap/$name.pcap \
	--json-geo-dump $dir_geo/$name.json \
	--dlf-dump $dir_dlf/$name.dlf \
	--decoded-sibs-dump \
	--reassemble-sibs \
	--decrypt-nas \
	--include-ip-traffic \
	| tee $dir_stdout/$name.log
