import sys
print "...................Mcpat to Hotspot..................."
print ".........Written by Milad Ghorbani Moghaddam.........."

#................................................................................................. 
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
#................................................................................................. 

accumulative_RUN=0
# needs one file from the previous interval containing the power of accumulated powers 
if len(sys.argv) == 5:
        if  sys.argv[1]=='ACCUMULATIVE=YES': 
                accumulative_power_file= sys.argv[2] #from the previous interval
                accumulative_RUN=1
                num_interval=sys.argv[3]
                input_list= sys.argv[4]
                DVFS_list=input_list.split(',')
                print 'Accumulative RUN'
        else :
                print 'Default RUN'
else:
     print 'ERROR: incorrect input'
     exit(1)   

#DVFS_list = ['FREQ_800MHz0','FREQ_1.5GHz1','FREQ_500MHz2','FREQ_2GHz3'] 
#.....................................................................................................
num_stats=0
current_stats=0
dynamic_router_power=[]
dynamic_router_power_list=[]

READ_ROUTER_FILE = open("./router_swapped_sorted.txt", 'r')
for line in READ_ROUTER_FILE:
	if 'Dynamic_Power_router[0]:' in line:
		num_stats+=1	
READ_ROUTER_FILE = open("./router_swapped_sorted.txt", 'r')
for line in READ_ROUTER_FILE:		
	if 'Dynamic_Power_router[0]:' in line:
		current_stats+=1
	if current_stats==num_stats:
		if 'Dynamic' in line:
			dynamic_router_power=line.split(' ')	
			dynamic_router_power_list.append(dynamic_router_power[1])
	
READ_ROUTER_FILE.close()		
#......................................................................................................
READ_FILE = open("./power_mcpat.ptrace", 'r')
WRITE_FILE = open("./power.ptrace", 'w')
router_index=0
split_array=[]
num_core = 0
element_counter=-1
for line in READ_FILE:
	if 'WARN' not in line:
		WRITE_FILE.write(line)
	else:
		split_array=line.split(' ')
#		print split_array
#		print len(split_array)
		for i in xrange(0 , len(split_array)-1):
                        print i
			if 'WARN' in split_array[i] : 
                                coefficient = DVS_coefficient (num_core,DVFS_list)
				#WRITE_FILE.write(dynamic_router_power_list[router_index])
				WRITE_FILE.write(str(float(coefficient)*float(dynamic_router_power_list[router_index])))
				WRITE_FILE.write(' ')
				router_index+=1			
			else:                                
                                element_counter+=1
                                if (element_counter ==31): # number of elements in the floorplan for each core, except the router
                                        num_core+=1
                                        element_counter=0
                                print 'element_counter = %s    num_core= %s real_element=%s' %(element_counter,num_core,i)
                                coefficient = DVS_coefficient (num_core,DVFS_list)                    
                                
                                print '%s * %s = %s'%(coefficient,split_array[i],str(float(coefficient)*float(split_array[i])) )
				WRITE_FILE.write(str(float(coefficient)*float(split_array[i])))
				WRITE_FILE.write(' ')
		WRITE_FILE.write( '\n')
READ_FILE.close()
WRITE_FILE.close()
#......................................................................................................
READ_FILE=open("./power.ptrace", 'r')
WRITE_FILE = open("./accumulative_power.ptrace", 'w')
#for line in READ_FILE:
#        WRITE_FILE.write(line)
line_1 = READ_FILE.next().strip()
WRITE_FILE.write(line_1)
line_2 = READ_FILE.next().strip()
WRITE_FILE.write('\n')
WRITE_FILE.write(line_2)
WRITE_FILE.write('\n')
READ_FILE.close()
WRITE_FILE.close()

if  accumulative_RUN== 1:
        print 'accumulative_RUN'
        READ_FILE_A = open("./power.ptrace", 'r')
        READ_FILE_B = open(accumulative_power_file, 'r')
        WRITE_FILE = open("./accumulative_power.ptrace", 'w')
        C=[]
        line_A_1 = READ_FILE_A.next().strip()
        line_A_2 = READ_FILE_A.next().strip()
        A=line_A_2.split(' ')
        line_B_1 = READ_FILE_B.next().strip()
        line_B_2 = READ_FILE_B.next().strip()
        B=line_B_2.split(' ')
        WRITE_FILE.write(line_A_1)
        WRITE_FILE.write('\n')
        for i in xrange (0,len(A)):
            P1=(float(A[i])*float(num_interval)+float(B[i])) /float(float(num_interval)+1)
            print A[i],B[i],P1
            C.append(str(P1)) #calculating average power
            WRITE_FILE.write(C[i])
            WRITE_FILE.write(' ')
        WRITE_FILE.write('\n')

        READ_FILE_A.close()
        READ_FILE_B.close()
        WRITE_FILE.close()

print 'END'

