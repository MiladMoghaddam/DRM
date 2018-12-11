import string
import sys

if len(sys.argv) != 2:
	print 'Error : No input list (SwaplistX) or wrong number of input'
	sys.exit(0)

input_list= sys.argv[1]
SWAP_list=input_list.split(',')

#SWAP_list=['15','3','2','0','6','5','4','7','8','14','10','13','12','11','9','1']

################ POWER_65n.XML ###########################
READ_FILE = open("./power_65nm_sorted.xml",'r')       
WRITE_FILE = open("./power_65nm_temp.xml", 'w') 
renamed="NONE"
selected_core_number ='none'
skip=0
for line in READ_FILE :
			#######core##########
			skip=0
			for core_number in range (0,10):
				if  ( (('core%s.'%core_number in line)) or (('core%s"'%core_number in line)) ) and skip==0:
					
						line=string.replace(line,"core%s"%core_number,"core%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			for core_number in range (10,64):
				if  (('core%s'%core_number in line)) and skip==0:
						line=string.replace(line,"core%s"%core_number,"core%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			#######L1Directory##########
			for core_number in range (0,10):
				if  (('L1Directory%s"'%core_number in line)) and skip==0:
					
						line=string.replace(line,"L1Directory%s"%core_number,"L1Directory%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			for core_number in range (10,64):
				if  (('L1Directory%s'%core_number in line)) and skip==0:
						line=string.replace(line,"L1Directory%s"%core_number,"L1Directory%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			#######L2##########
			for core_number in range (0,10):
				if  (('L2%s"'%core_number in line)) and skip==0:
					
						line=string.replace(line,"L2%s"%core_number,"L2%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			for core_number in range (10,64):
				if  (('L2%s'%core_number in line)) and skip==0:
						print "core_number= %s"%core_number
						line=string.replace(line,"L2%s"%core_number,"L2%s"%int(SWAP_list[core_number]) )
						WRITE_FILE.write(line)
						skip=1

			if  skip==0:
					WRITE_FILE.write(line)	

################################################
#here we are going to sort our template swapped file

WRITE_FILE = open("./power_65nm_swapped_sorted.xml", 'w')
########### start ##############
READ_FILE = open("./power_65nm_temp.xml", 'r')
write = 1
for line in READ_FILE:
                if  (('busy_cycles' in line)) and write ==1:           
							WRITE_FILE.write(line)
							write = 0
                if write==1:                 
                        WRITE_FILE.write(line) 

################################################
write = 0
prev_line=""
############# core ######################
for core_number in range (0,10):
	READ_FILE = open("./power_65nm_temp.xml",'r') 
	for line in READ_FILE:
                if  (('"system.core%s"'%core_number in line)):           
                         write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line) and ("</component>" in prev_line):
                        write = 0
                prev_line=line

write = 0
prev_line=""
for core_number in range (10,100):
	READ_FILE = open("./power_65nm_temp.xml",'r') 
	for line in READ_FILE:
                if  (('"system.core%s"'%core_number in line)):           
                         write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line) and ("</component>" in prev_line):
                        write = 0
                prev_line=line

########## L1Directory ############
write = 0
prev_line=""
for core_number in range (0,100):
	READ_FILE = open("./power_65nm_temp.xml",'r') 
	for line in READ_FILE:
                if  (('"system.L1Directory%s"'%core_number in line)):
                        write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line

########## L2 ##################

write = 0
prev_line=""
for core_number in range (0,100):
	READ_FILE = open("./power_65nm_temp.xml",'r') 
	for line in READ_FILE:
                if  (('"system.L2%s"'%core_number in line)):
                        write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line


########### rest ##############
READ_FILE = open("./power_65nm_temp.xml", 'r')
write = 0
for line in READ_FILE:
                if  (('"system.mem"' in line)):
                        write = 1
                if write==1:                 
                        WRITE_FILE.write(line)  


############################################








################## ROUTER ######################
READ_FILE = open("./router.txt",'r') 
WRITE_FILE = open("./router_swapped.txt", 'w') 
for line in READ_FILE:
#			WRITE_FILE.write(line)
			for core_number in range (0,64):
				if  ("[%s]"%core_number in line):
					WRITE_FILE.write(string.replace(line,"[%s]"%core_number,"[%s]"%int(SWAP_list[core_number])))

WRITE_FILE = open("./router_swapped_sorted.txt", 'w')
for core_number in range (0,64):
	READ_FILE = open("./router_swapped.txt",'r') 
	for line in READ_FILE:
			if ("[%s]"%core_number in line):
				WRITE_FILE.write(line)



	

