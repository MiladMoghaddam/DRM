import sys
if len(sys.argv) != 2:
	print 'Error : No input list (cpulistX) or wrong number of input'
	sys.exit(0)

input_list= sys.argv[1]
DVFS_list=input_list.split(',')

#DVFS_list = ['FREQ_1GHz0','FREQ_1GHz1','FREQ_500MHz2','FREQ_2GHz3']
#................................................................................................
#..................................stats.txt.....................................................
#................................................................................................

READ_STATS_FILE = open("./stats.txt", 'r')
WRITE_STATS_FILE = open("./stats_DVFS.txt", 'w')

num_stats=0
for line in READ_STATS_FILE:
	if 'Begin Simulation Statistics' in line:
		num_stats+=1
print 'num_stats = %s' %num_stats
READ_STATS_FILE.close()


READ_STATS_FILE = open("./stats.txt", 'r')
cur_num_stats=0
for line in READ_STATS_FILE:
	if 'Begin Simulation Statistics' in line:	
		cur_num_stats+=1
	if (cur_num_stats==num_stats):
		CORE='NONE'
		for i in xrange (0,len(DVFS_list)):
			if DVFS_list[i] in line:
				CORE= DVFS_list[i]
				CORE_index=i
		if CORE!='NONE':
			if '.kern' not in line:		
				WRITE_STATS_FILE.write( line.replace (CORE,'cpu%s'%CORE_index))
		elif 'cpu' in line:			
			if ('cpufreq' in line) or ('cpu_voltage_domain' in line) or ('cpu_clk_domain' in line):
				WRITE_STATS_FILE.write( line)
			if '.kern.' in line:
				WRITE_STATS_FILE.write( line)
		else:
			if 'FREQ_' not in line:
				WRITE_STATS_FILE.write( line)
#................................................................................................
#..................................config.ini....................................................
#................................................................................................
READFILE = open("./config.ini", 'r')
WRITEFILE = open("./config_DVFS.ini", 'w')
remove_line=0

CORE='NONE'
for line in READFILE:
	for i in xrange (0,len(DVFS_list)):
		if DVFS_list[i] in line:
			CORE= DVFS_list[i]
			CORE_index=i

	if '[system.cpu' in line:
		if ('[system.cpu_' not in line) :
			remove_line=1
	if 'FREQ_' in line:
		if  CORE not in line:
			remove_line=1 
	if ('[system.cpu_clk_domain' in line) or ('[system.disk' in line) or ('[system.cpufreq' in line) or ('[system.clk_domain' in line):
			remove_line=0		 
#	if CORE!='NONE':
	if('[system.%s'%CORE in line):
			remove_line=0

	if remove_line==0:				
		if 'children=FREQ' in line:
			children= line.split(' ')
			WRITEFILE.write('children=')
			for i in xrange(0,len(children)-1):
				if 'FREQ_' not in children[i]: 		
					WRITEFILE.write( '%s ' %children[i] )
			if 'FREQ_' not in children[len(children)-1]:
					WRITEFILE.write( '%s' %children[len(children)-1] )
		elif CORE in line:
			WRITEFILE.write( line.replace (CORE,'cpu%s'%CORE_index))
		else:		
			WRITEFILE.write(line)
READFILE.close()
WRITEFILE.close()
#................................................................................................
#..................................router.txt....................................................
#................................................................................................

READ_ROUTER_FILE = open("./router.txt", 'r')
WRITE_ROUTER_FILE = open("./router_new.txt", 'w')
num_stats=0
current_stats=0
for line in READ_ROUTER_FILE:
	if 'Dynamic_Power_router[0]:' in line:
		num_stats+=1	
#print num_stats
READ_ROUTER_FILE = open("./router.txt", 'r')
for line in READ_ROUTER_FILE:		
	if 'Dynamic_Power_router[0]:' in line:
		current_stats+=1
	if current_stats==num_stats:
		WRITE_ROUTER_FILE.write(line)

READ_ROUTER_FILE.close()
WRITE_ROUTER_FILE.close()





