# DRM
-------------------------------------------------------------------------------------
 DRM TOOL
-------------------------------------------------------------------------------------
The DRM tool is a dynamic lifetime reliability management tool for chip multiprocessors
(CMPs).it gives you the option to use thread migration and dynamic voltage and frequency
 scaling (DVFS) as the two primary techniques to change the CMP operation with the goal
 of increasing the lifetime reliability of the overall system to the desired target with
 minimal performance degradation.

For more information please take a look at the following papers:
(Please cite them if you use them in your work)
  - M.G. Moghaddam and C. Ababei, “Dynamic lifetime reliability management for chip 
    multiprocessors,” IEEE Trans. on Multiscale Computing Systems, 2018.
  - M.G. Moghaddam, A. Yamamoto, and C. Ababei, “Investigation of DVFS based dynamic 
    reliability management for chip multiprocessors,” IEEE Int. Workshop on Dependable
    Many-Core Computing (DMCC), 2015
-------------------------------------------------------------------------------------
Developed by: Milad Ghorbani Moghaddam, Dr. Cristinel Ababei

milad.ghorbanimoghaddam@marquette.edu

cristinel.ababei@marquette.edu

Marquette University

-------------------------------------------------------------------------------------
This tool is developed on top of the gem5 simulator. The main directory here contains
 all the codes and stuff needed for running our proposed DRM on gem5.
Before building the gem5 with rubby (gem5 files exists here), make sure to make the 
mcpat, the hotpot and the REST tools inside the gem5 directory and change the gem5 
directories inside configs/example/Simulation.py and also inside 
DRM_files/flow_for_interval_16cores.sh and DRM_files/flow_for_interval_64cores.sh 
and DRM_files/temp_calc.py

running the DRM tool is easy. you just need to run gem5 as usual
This is an example of running the DRM for 16 cpus on a 4x4 mesh noc.

build/ALPHA/gem5.opt configs/example/fs_DRM.py  --script=run_scripts/bodytrack_16c_simsmall.rcS\
 --num-cpus=16 --num-dir=16 --caches --l2cache --num-l2caches=16 --ruby --garnet=fixed\
 --topology=Mesh --mesh-row=4 --kernel=/home/milad/gem5/full_system_images_ALPHA/binaries/vmlinux_2.6.27-gcc_4.3.4\
 --disk-image=/home/milad/gem5/full_system_images_ALPHA/disks/linux-parsec-2-1-m5-with-test-inputs.img

This tool is made so that it can support the detailed CPU as well.
There is a control panel in the Simulation.py that you can control the process with.
First of all you need to boot the gem5 with Timing_Cpu=1 and then with ROI_Time_Calc=1
 to find and set the ROI_start_tick_estimation and ROI_tick_duration_estimation
 (can be found in stats.txt) and the MTTF_refrence(which is given in DRM/info) value
s in the Simulation.py to initialize the DRM engine.
You can choose the number of samplings by changing the NUM_INTERVALS.
Setting the DVFS_Technique=1 or Thread_Migration_Technique=1 starts the DRM process.
 you can check the results in DRM/ file. info shows the overal information about the
 whole process. if you want to have detailed information you can check inside
 the DRM/interval_* to see plenty of information about the run.
