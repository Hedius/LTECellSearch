#!/bin/bash

workdir=/home/qcsuper/Software/LTE-Cell-Scanner/build/src

# go into the workdir
cd $workdir

# create work directories
export_dir=CellSearch_Results

# ask for the parameters
if [ $# -eq 2 ]
then
    start_frequency=$1
    end_frequency=$2
else
    read -p "Pls enter the start frequency: " start_frequency
    read -p "Pls enter the end frequency: " end_frequency
fi

# print
echo "New Scan: Start: $start_frequency End: $end_frequency"

scanName=CellScan_${start_frequency}_to_${end_frequency}
log_dir=$export_dir/$scanName
rm -fr $log_dir

mkdir -p $export_dir $log_dir

#
echo Starting Scan:
./CellSearch -s $start_frequency -e $end_frequency -d $log_dir -r | tee ${log_dir}/${scanName}_results.txt
