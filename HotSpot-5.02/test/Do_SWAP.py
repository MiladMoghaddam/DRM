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
WRITE_FILE = open("./power_65nm_swapped_sorted.xml", 'w') 
Data=[[0 for x1 in range(50)] for x2 in range(64)]

counter=0

found = 0
prev_line=""
for line in READ_FILE:
                for core_number in range (0,64):
                    if  (('"system.core%s.dcache"'%core_number in line)):           
						found = 1
						counter = 0
						core_found=core_number
                if found==1:                 
   						Data[core_found][counter]=line
						counter+=1

                if ("</component>" in line) and ("</component>" in prev_line):
						found = 0
                prev_line=line


READ_FILE = open("./power_65nm_sorted.xml",'r')    
line_counter=-1 #to skip copied lines
found=0
for line in READ_FILE:
			for core_number in range (0,64):
				if  (('"system.core%s.dcache"'%core_number in line)):
					found=1
					for counter in range(0,34):
						renamed=Data[int(SWAP_list[core_number])][counter]
						if "core%s"%int(SWAP_list[core_number]) in renamed:	
							renamed=string.replace(renamed,"core%s"%int(SWAP_list[core_number]),"core%s"%core_number)
						WRITE_FILE.write(renamed)	

			if found==1:
						line_counter+=1
						if line_counter==34:
							line_counter=-1
							found=0
			if line_counter==-1:
				WRITE_FILE.write(line)



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



	

