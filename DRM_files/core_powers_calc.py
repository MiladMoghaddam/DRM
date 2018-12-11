import sys
old_power = [0.0 for x in range(100)] #100 is max number of cores
new_power = [0.0 for x in range(100)]
def DVS_coefficient (num_core,DVFS_list):        
        if '500M' in DVFS_list[num_core]:
                coefficient = 0.5 #0.53 #V=0.8
        if '800M' in DVFS_list[num_core]:
                coefficient = 0.5 #0.57 #V=0.83
        if '1G' in DVFS_list[num_core]:
                coefficient = 0.5 #0.6 #V=0.85
        if '1100M' in DVFS_list[num_core]:
                coefficient = 0.5 #0.64 #V=0.88
        if '1200M' in DVFS_list[num_core]:
                coefficient = 0.5 #0.67 #V=0.9
        if '1300M' in DVFS_list[num_core]:
                coefficient = 0.5 #0.70 #V=0.92
        if '1400M' in DVFS_list[num_core]:
                coefficient = 0.53 #V =.8#0.74 #V=0.95
        if '1500M' in DVFS_list[num_core]:
                coefficient = 0.56 #V=.82#0.78 #V=0.97
        if '1600M' in DVFS_list[num_core]:
                coefficient = 0.6 #V=0.85#0.82 #V=1
        if '1700M' in DVFS_list[num_core]:
                coefficient = 0.67 #V=0.9 #0.86 #V=1.02
        if '1800M' in DVFS_list[num_core]:
                coefficient = 0.74 #V=.95 #0.91 #V=1.05
        if '1900M' in DVFS_list[num_core]:
                coefficient = 0.87 #V=1.03#0.95 #V=1.07
        if '2G' in DVFS_list[num_core]:
                coefficient = 1 #V=1.1
        return coefficient       


READ_FILE = open("./mcpatout.txt",'r') 
WRITE_FILE = open("./DVFS_core_powers.txt",'w')
key=0
processor_key=0
counter=-1
if len(sys.argv) != 2:
	print"ERROR: exit"
	exit(1)
else:
	input_list=sys.argv[1]
	core_list=input_list.split(",")

	
for line in READ_FILE:
	if "Processor:" in line:
		processor_key=1
	if "Total Cores:" in line:
		processor_key=0
	if processor_key==1:
		if "Runtime Dynamic" in line:
			temp=line.split(" = ")
			power=temp[1].split(" ")
			old_total_processor_power = power[0]
			WRITE_FILE.write ("old_total_processor_power = %s\n"%old_total_processor_power)	




	if "Core:" in line:
		key=1
		counter=counter+1

	if "Instruction Fetch Unit:" in line:
		key=0

	if key==1:
		if "Runtime Dynamic" in line:
			temp=line.split(" = ")
			power=temp[1].split(" ")
			old_power[counter]=float(power[0])
			new_power[counter]=float(power[0])*float(DVS_coefficient(counter,core_list))
			print old_power[counter]
			print new_power[counter]
			WRITE_FILE.write("Old_power[%s]= %s ...... New_Power[%s]= %s ...... CPU = %s ... coefficient = %s\n"%(counter,old_power[counter],counter,new_power[counter],core_list[counter],DVS_coefficient(counter,core_list)))

old_power_sum = 0.0
new_power_sum = 0.0	
for i in xrange (0,len(old_power)):
	old_power_sum = old_power[i] + old_power_sum
 	new_power_sum = new_power[i] + new_power_sum
WRITE_FILE.write ("\n\nold_power_sum= %s"%old_power_sum)
WRITE_FILE.write ("\nnew_power_sum= %s"%new_power_sum)
WRITE_FILE.write ("\nnew/old = %s"%(new_power_sum/old_power_sum))

WRITE_FILE.write ("\n\nold_total_processor_power= %s"%old_total_processor_power)
new_total_processor_power = new_power_sum + (float(old_total_processor_power)-old_power_sum)
WRITE_FILE.write ("\nnew_total_processor_power= %s"%new_total_processor_power)
WRITE_FILE.write ("\nnew/old = %s"%(new_total_processor_power/float(old_total_processor_power)))

