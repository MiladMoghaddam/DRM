import sys
DIR_GEM5="/home/milad/gem5"
print "Usage:\n"
print "python temp_calc.py floorplan.flp T.steady temperture.txt"
if len(sys.argv) ==4:
	FLP_FILE=sys.argv[1]
	STEADY_FILE=sys.argv[2]
	TEMPERATURE_FILE=sys.argv[3]
	
elif len(sys.argv) != 4:
	FLP_FILE="%s/HotSpot-5.02/ev6cluster4x4TOP.flp"%DIR_GEM5
	STEADY_FILE="./T.steady"
	TEMPERATURE_FILE="./temperature.txt"

FLP=open("%s"%FLP_FILE,"r")
STEADY=open("%s"%STEADY_FILE,"r")
TEMPERATURE=open("%s"%TEMPERATURE_FILE,"w")

FLP.readline()
FLP.readline()
for line in FLP:
	components=line.split(" ")
temp=components[0].split("_")
num_cores=int(temp[0])+1
#print num_cores
	
areaSum=[0.0 for i in range(100)]
TempInArea=[0.0 for i in range(100)]

for number in range(0,num_cores):
	FLP=open("%s"%FLP_FILE,"r")
	STEADY=open("%s"%STEADY_FILE,"r")

	FLP.readline()
	FLP.readline()
	if number==0:
		core_number="00"
	elif number==1:
		core_number="01"
	elif number==2:
		core_number="02"
	elif number==3:
		core_number="03"
	elif number==4:
		core_number="04"
	elif number==5:
		core_number="05"
	elif number==6:
		core_number="06"
	elif number==7:
		core_number="07"
	elif number==8:
		core_number="08"
	elif number==9:
		core_number="09"
	else:
		core_number=str(number)
	
	#print "%s"%core_number
	
	for line in FLP:
		steady_line=STEADY.readline()
		temp=steady_line.split("	")
		component_temp=temp[1]


		components=line.split("\t")
		#print "components=%s"%components
		
		if core_number in components[0]:
#				print line
				for i in xrange (0,5):
#					print ("%s=%s"%(i,components[i]))
					area=float(components[1])*float(components[2])
				TempInArea[int(core_number)]=TempInArea[int(core_number)]+float(component_temp)*area
				areaSum[int(core_number)]=areaSum[int(core_number)]+area
#				print "area=%f temp=%f TempInArea=%f areaSum=%f temp=%f"%(area,float(component_temp),TempInArea[int(core_number)],areaSum[int(core_number)],TempInArea[int(core_number)]/areaSum[int(core_number)])	


for i in range(0,num_cores):
	print "%s %0.2f"%(i,float(TempInArea[i]/areaSum[i]))
	TEMPERATURE.write("%s %0.2f\n"%(i,float(TempInArea[i]/areaSum[i])))
	

