#!/bin/bash
declare -i NUM_CORES=16

dir_gem5=/home/milad/gem5
#dir_DVFS=$dir_gem5/DVFS
#dir_m5out=$dir_gem5/work/m5out
#dir_mcpat=$dir_gem5/mcpat0.8
#dir_hotspot=$dir_gem5/HotSpot-5.02
#dir_rest=$dir_gem5/REST

dir_hotspot=/home/milad/gem5/HotSpot-5.02
my_nxn="4x4"
my_router_location="TOP"
file_config=$dir_hotspot/ev6cluster${my_nxn}.config
file_floorplan=$dir_hotspot/ev6cluster${my_nxn}${my_router_location}.flp
#file_floorplan=$dir_hotspot/floorplan/ev6_2x2_TOP.flp

filename="/home/milad/gem5/DRM/run_info/info"
SWAPLIST=NULL
while read line;
do   
    CPULIST=$SWAPLIST
    echo $line
    SWAPLIST="${line#* }"
    INUM="${line% *}"
done < $filename
echo "INUM= $INUM"
echo "CPULIST= $CPULIST"
echo "SWAPLIST= $SWAPLIST"
previous_INUM=$(($INUM-1))  

mkdir $dir_gem5/DRM/interval_$INUM 
mkdir $dir_gem5/DRM/preprocessing
cp $dir_gem5/m5out/*  $dir_gem5/DRM/preprocessing
cd $dir_gem5/DRM/preprocessing/
cp $dir_gem5/DRM_files/DRM_preprocessing.py $dir_gem5/DRM/preprocessing

python DRM_preprocessing.py $CPULIST

cp $dir_gem5/DRM/preprocessing/config_DVFS.ini $dir_gem5/DRM/interval_$INUM/config.ini
cp $dir_gem5/DRM/preprocessing/stats_DVFS.txt $dir_gem5/DRM/interval_$INUM/stats.txt

cp $dir_gem5/DRM/preprocessing/router_new.txt $dir_gem5/DRM/interval_$INUM/router.txt
cp $dir_gem5/DRM_files/Gem5_Mcpat_milad_DRM.py $dir_gem5/DRM/interval_$INUM
cd $dir_gem5/DRM/interval_$INUM
python Gem5_Mcpat_milad_DRM.py

cp $dir_gem5/DRM_files/Do_SWAP.py $dir_gem5/DRM/interval_$INUM
cd $dir_gem5/DRM/interval_$INUM
python Do_SWAP.py $SWAPLIST #swap correction for ruby

cd $dir_gem5/mcpat0.8
./mcpat -infile $dir_gem5/DRM/interval_$INUM/power_65nm_swapped_sorted.xml -outfile  $dir_gem5/DRM/interval_$INUM/power_mcpat.ptrace -print_level 6 >$dir_gem5/DRM/interval_$INUM/mcpatout.txt

cp $dir_gem5/DVFS_files/core_powers_calc.py $dir_gem5/DVFS/interval_$INUM
cd $dir_gem5/DVFS/interval_$INUM
python core_powers_calc.py $CPULIST

cp $dir_gem5/DRM_files/Mcpat_to_Hotspot_accumulative.py $dir_gem5/DRM/interval_$INUM
cd $dir_gem5/DRM/interval_$INUM
#The input file would be the accumulative_power_file from the previous intervals
#it produces power.ptrace (interval power) accumulative_power.ptrace (accumulative power)
python Mcpat_to_Hotspot_accumulative.py  ACCUMULATIVE=YES $dir_gem5/DRM/interval_$previous_INUM/accumulative_power.ptrace $INUM $CPULIST

#Temperture for just the interval_power using power.ptrace
cd $dir_gem5/HotSpot-5.02
./hotspot -c $file_config -f $file_floorplan -p $dir_gem5/DRM/interval_$INUM/power.ptrace  -steady_file $dir_gem5/DRM/interval_$INUM/T_NotNormalized.steady -model_type grid -grid_steady_file $dir_gem5/DRM/interval_$INUM/grid_NotNormalized.steady

#Temperture for accumulative_power using accumulative_power.ptrace
./hotspot -c $file_config -f $file_floorplan -p $dir_gem5/DRM/interval_$INUM/accumulative_power.ptrace  -steady_file $dir_gem5/DRM/interval_$INUM/accumulative_T_NotNormalized.steady -model_type grid -grid_steady_file $dir_gem5/DRM/interval_$INUM/accumulative_grid_NotNormalized.steady

#normalizing temperature
cp $dir_gem5/DRM_files/normalize_T.py $dir_gem5/DRM/interval_$INUM
cd $dir_gem5/DRM/interval_$INUM
python ./normalize_T.py #produces T.steady grid.steady and also accumulative ones

cd $dir_gem5/DRM/HotSpot-5.02
./grid_thermal_map.pl $file_floorplan $dir_gem5/DRM/interval_$INUM/grid.steady  > $dir_gem5/DRM/interval_$INUM/grid.svg
convert -font Helvetica svg:grid.svg grid.pdf

./grid_thermal_map.pl $file_floorplan $dir_gem5/DRM/interval_$INUM/accumulative_grid.steady  > $dir_gem5/DRM/interval_$INUM/accumulative_grid.svg
convert -font Helvetica svg:accumulative_grid.svg accumulative_grid.pdf


#calculating temperatore for each core
cp $dir_gem5/DRM_files/temp_calc.py $dir_gem5/DRM/interval_$INUM
cd $dir_gem5/DRM/interval_$INUM
python temp_calc.py $file_floorplan ./T.steady ./temperture.txt

#REST
cd $dir_gem5/REST
# MTTF for just the interval, using T.steady
./REST $file_floorplan $dir_gem5/DRM/interval_$INUM/T.steady -o $dir_gem5/DRM/interval_$INUM/MTTF_system_per_interval.txt -V 1.1 -freq $CPULIST

mkdir $dir_gem5/DRM/interval_$INUM/MTTF_per_core_per_interval
for ((i=0 ; i<$NUM_CORES ; i++))
do
    echo " REST for core$i"
    ./REST $dir_hotspot/floorplan_per_core_TOP/ev6_core$i.flp $dir_gem5/DRM/interval_$INUM/T.steady -o $dir_gem5/DRM/interval_$INUM/MTTF_per_core_per_interval/MTTFcore$i.txt -V 1.1 -freq $CPULIST
done


cd $dir_gem5/REST
# MTTF accumulstive, using accumulative_T.steady
./REST $file_floorplan $dir_gem5/DRM/interval_$INUM/accumulative_T.steady -o $dir_gem5/DRM/interval_$INUM/accumulative_MTTF_system.txt -V 1.1 -freq $CPULIST

mkdir $dir_gem5/DRM/interval_$INUM/accumulative_MTTF_per_core
for ((i=0 ; i<$NUM_CORES ; i++))
do
    echo " REST for core$i"
    ./REST $dir_hotspot/floorplan_per_core_TOP/ev6_core$i.flp $dir_gem5/DRM/interval_$INUM/accumulative_T.steady -o $dir_gem5/DRM/interval_$INUM/accumulative_MTTF_per_core/MTTFcore$i.txt -V 1.1 -freq $CPULIST
done
