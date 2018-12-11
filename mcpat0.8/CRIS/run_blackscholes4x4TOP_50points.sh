#!/bin/bash

dir_gem5=/home/alex/gem5
dir_work=$dir_gem5/work
dir_m5out=$dir_gem5/work/m5out
dir_mcpat=$dir_gem5/mcpat0.8
dir_hotspot=$dir_gem5/HotSpot-5.02
dir_rest=$dir_gem5/REST

# executables and scripts:
py_script_gem5_post_processing=$dir_work/gem5_post_processing_1234.py
py_script_gem5_2_mcpat=$dir_work/gem5_2_mcpat_parse_2012.py
exe_mcpat=$dir_mcpat/mcpat
py_script_mcpat_2_hotspot=$dir_work/mcpat_2_hotspot_parse_2012.py
exe_hotspot=$dir_hotspot/hotspot
exe_rest=$dir_rest/REST

# parameters:
MY_NUM_DUMP_POINTS=50
my_benchmark=scripts/blackscholes_16c_simsmall.rcS
my_nxn="4x4"
my_router_location="TOP"
my_maxtick=2635786688000

# folder where everything is moved at the end of this benchmark run;
my_final_m5out_folder=$dir_work/m5out_blackscholes_4x4TOP_50points

# files:
# files used during HotSpot run;
file_config=$dir_hotspot/ev6cluster${my_nxn}.config
file_floorplan=$dir_hotspot/ev6cluster${my_nxn}${my_router_location}.flp



cd $dir_gem5



echo "\n================================================================================"
echo "\n"
echo "\n Run gem5 on $my_benchmark (done once only)"
echo "\n During this run we dump stats $MY_NUM_DUMP_POINTS times"
#EXAMPLE: ./build/ALPHA_FS/gem5.opt configs/example/ruby_fs.py --num-cpus=4 --num-dirs=4 --num-l2=4 --mesh-rows=2 --garnet=fixed --topology=Mesh --script=scripts/blackscholes_4c_simsmall.rcS --maxtick=2635786688000
./build/ALPHA_FS/gem5.opt configs/example/ruby_fs.py --num-cpus=16 --num-dirs=16 --num-l2=16 --mesh-rows=4 --garnet=fixed --topology=Mesh --script=$my_benchmark --maxtick=$my_maxtick
echo "\n Done!";



cp -r m5out work/
cd $dir_work



echo "\n================================================================================"
echo "\n"
echo "\n Run script gem5_post_processing_1234 to generate stats{i}.txt and ruby{i}.stats, i=1,2,3..$MY_NUM_DUMP_POINTS, files from stats.txt and ruby.stats output files"
#EXAMPLE: python gem5_post_processing_1234.py
$py_script_gem5_post_processing
echo "\n Done!";



# at this time, we have all MY_NUM_DUMP_POINT files stats{i}.txt and ruby{i}.stats
# take each such pair of files through the flow to estimate MTTF with REST
# this MTTF evaluation methodology is done MY_NUM_DUMP_POINT times
# in this way we generate all points of our reliability trace
echo "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
echo "\n"
echo "\n Run MTTF evaluation methodology (i.e., REST flow) $MY_NUM_DUMP_POINTS times"
echo "\n"



for i_point in `seq 1 $MY_NUM_DUMP_POINTS`
do

    echo "\n================================================================================"
    echo "\n"
    echo "\n Run script gem5_2_mcpat to generate power_gem5_${i_point}.xml file from stats${i_point}.txt and ruby${i_point}.stats files"
    #EXAMPLE: python gem5_2_mcpat_parse_2012.py -s stats1.txt -C config.ini -r ruby1.stats -p power_gem5_1.xml -F m5out
    stats_file_i=stats${i_point}.txt
    ruby_file_i=ruby${i_point}.stats
    power_file_i=power_gem5_${i_point}.xml
    $py_script_gem5_2_mcpat -s $stats_file_i -C config.ini -r $ruby_file_i -p $power_file_i -F m5out
    echo "\n Done!";

    echo "\n================================================================================"
    echo "\n"
    echo "\n Run McPAT tool to generate initial power_mcpat_${i_point}.ptrace file"
    #EXAMPLE: ../mcpat0.8/mcpat -infile m5out/power_gem5_1.xml -outfile m5out/power_mcpat_1.ptrace -print_level 6
    power_file_i=$dir_m5out/power_gem5_${i_point}.xml
    ptrace_file_i=$dir_m5out/power_mcpat_${i_point}.ptrace
    $exe_mcpat -infile $power_file_i -outfile $ptrace_file_i -print_level 6
    echo "\n Done!";

    echo "\n================================================================================"
    echo "\n"
    echo "\n Run script mcpat_2_hotspot to generate power_mcpat_complete_${i_point}.ptrace file"
    #EXAMPLE: mcpat_2_hotspot_parse_2012.py -w m5out -r ruby1.stats -m power_mcpat_1.ptrace -o power_mcpat_complete_1.ptrace
    ruby_file_i=ruby${i_point}.stats
    ptrace_file_i=$dir_m5out/power_mcpat_${i_point}.ptrace
    file_complete_ptrace_i=$dir_m5out/power_mcpat_complete_${i_point}.ptrace 
    $py_script_mcpat_2_hotspot -w m5out -r $ruby_file_i -m $ptrace_file_i -o $file_complete_ptrace_i
    echo "\n Done!";

    echo "\n================================================================================"
    echo "\n"
    echo "\n Run HotSpot to generate temperatures file";
    #EXAMPLE: ../HotSpot-5.02/hotspot -c ../HotSpot-5.02/ev6cluster4x4.config -f ../HotSpot-5.02/ev6cluster4x4RIGHT.flp -p m5out/power_mcpat_complete_1.ptrace -steady_file m5out/ev6cluster4x4RIGHT_1.steady -model_type grid
    file_complete_ptrace_i=$dir_m5out/power_mcpat_complete_${i_point}.ptrace
    file_T_steady_i=$dir_m5out/ev6cluster${my_nxn}${my_router_location}_${i_point}.steady
    if [ $i_point == 1 ]; then
        # first run of HotSpot is simply done without the --init_file option;
        $exe_hotspot -c $file_config -f $file_floorplan -p $file_complete_ptrace_i -steady_file $file_T_steady_i -model_type grid
    else
        # starting with the second dump point use the previous run of HotSpot 
        # as starting temperature-point; in this way we get a "true" run for the
        # current dump-point;
        #EXAMPLE: ../HotSpot-5.02/hotspot -c ../HotSpot-5.02/ev6cluster4x4.config -f ../HotSpot-5.02/ev6cluster4x4RIGHT.flp -p m5out/power_mcpat_complete_2.ptrace -steady_file m5out/ev6cluster4x4RIGHT_2.steady -model_type grid -init_file m5out/ev6cluster4x4RIGHT_1.steady
        i_point_minus_1=$(($i_point-1))
        file_T_steady_i_minus_1=$dir_m5out/ev6cluster${my_nxn}${my_router_location}_${i_point_minus_1}.steady
        $exe_hotspot -c $file_config -f $file_floorplan -p $file_complete_ptrace_i -steady_file $file_T_steady_i -model_type grid -init_file $file_T_steady_i_minus_1
    fi
    echo "\n Done!";

    echo "\n================================================================================"
    echo "\n"
    echo "\n Run REST to estimate MTTF"
    #EXAMPLE: ../REST/REST ../HotSpot-5.02/ev6cluster2x2RIGHT.flp m5out/ev6cluster2x2RIGHT_1.steady -o m5out/rest_mttf_result_1.txt
    file_T_steady_i=$dir_m5out/ev6cluster${my_nxn}${my_router_location}_${i_point}.steady
    file_mttf_result_i=$dir_m5out/rest_mttf_result_${i_point}.txt
    $exe_rest $file_floorplan $file_T_steady_i -o $file_mttf_result_i
    echo "\n Done!";

done



echo "\n================================================================================"
echo "\n"
echo "\n Backup the entire m5out/ folder of this benchmark's run"
mv m5out $my_final_m5out_folder
echo "\n Done!";


cd $dir_work


echo "\n All done!";
