#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h> // #TIMESTAMP

#include <math.h>

#include "statistics.h"

// Definitions. Almost all pretty much free to change.
#define DEFAULT_ITERATIONS	(long int)100000
#define DEFAULT_BETA		(long double)1.64
#define DEFAULT_MTTF		(long double)30
#define DEFAULT_TEMP		(long double)300.0000
#define	DEFAULT_FAILURES	3
#define DEFAULT_OUTPUTFILE	"reliability.txt"
#define DEFAULT_DATFILE		"statistics.dat"
#define VERBOSE_OFF		0
#define	VERBOSE_ON		1
#define STARTING_REFERENCE	10000
#define	REFERENCE_FREQUENCY	2	// The less, the more frequent
#define	DEFAULT_VDD		(long double)1.1
#define	STANDARD_AREA		(long double)1e-6
#define	MAX_COL			10
//milad changes 
//just it is used for making a VddList
#define	MAX_NUM_CORES			100 // or any 

#define SECONDS_PER_DAY		(long double)86400
#define	SECONDS_PER_HOUR	(long double)3600
#define	SECONDS_PER_MINUTE	(long double)60		

#define	SANITY_CHECK_ERROR	-1

#define	NBTI			1
#define	TDDB			2


// Prints basic proper usage instruction to the user
void usage(int argc, char **argv) {

	printf("\nThis program calculates the MTTF of a SoC using the Monte Carlo method.\n\n");
	printf("Usage: %s <areafile/floorplan> <temperaturefile> [options]\n\n", argv[0]);
	printf("<areafile/floorplan>\tSpecifies the areas of the functional units\n");
	printf("\t\t\trefer to the README file\n\n");
	printf("<temperaturefile>\tSpecifies the temperatures of the functional units\n");
	printf("\t\t\trefer to the README file\n\n");
	printf("[-i N, --iterations N]\tUse N Monte Carlo iterations.\n");
	printf("\t\t\t(Default: N = %ld)\n\n", DEFAULT_ITERATIONS);
	printf("[-b B, --beta B]\tUse the shape parameter B for Weibull distributions\n");
	printf("\t\t\t(Default: B = %.4Lf)\n\n", DEFAULT_BETA);
	printf("[-l L, --lifetime L]\tAdjusts standard MTTF L (arb. units) that a 1mm x 1mm\n");
	printf("\t\t\tblock should have at a given temperature (see README)\n");
	printf("\t\t\t(Default: L = %.4Lf)\n\n", DEFAULT_MTTF);
	printf("[-t T, --temperature T]\tReference temperature for parameters,\n");
	printf("\t\t\tin degrees Kelvin. (Default: T = %.4LfK)\n\n", DEFAULT_TEMP);
	printf("[-f F, --failures F]\tFailure models to be considered (see README)\n");
	printf("\t\t\t(Default: F = %d)\n\n", DEFAULT_FAILURES);
	printf("[-o <file>]\t\tOutput file name.\n");
	printf("\t\t\t(Default is no output file)\n\n");
	printf("[-v, --verbose]\t\tVerbose on\n\n");
	printf("[-V V, --voltage V]\tVoltage V applied to the blocks, also used as CALBRATION voltage\n");
	printf("\t\t\t(Default: V = %.4LfV)\n\n", DEFAULT_VDD);
	printf("[-VL V1,V2,V3,...,Vn, --VddList V1,V2,V3,...,Vn]\tVoltages for each core\n\n");
	printf("[-freq fromGem5Flow --Frequency fromGem5Flow]\tVoltages for each core\n");
	printf("\t\t\t(Default: freq = 2GHz)\n\n");
	printf("[-d <file>]\t\tCSV file to save the data\n");
	printf("\t\t\t(Default is no CSV file)\n\n");
	printf("[-c <file>]\t\tConfiguration override file\n");
	printf("\t\t\t(Default is no Config. file)\n\n");
}
/*
long double Calculate_MTTF_NBTI(long double t, long double area){
}

*/

int main(int argc, char *argv[]) {

	long double alpha, beta, MTTF, x, xprime, stdtemp, vdd, width, height, average, temp;

	long double NBTIcalibration, TDDBcalibration;

	long int i, iterations, reference;

	int failuremodels, verbose;

	char blockname[NAME_BUFFER];

	//milad changes
	char* VddListString;
	char* freqListString;
	long double VddList[MAX_NUM_CORES];
	int VddListComponentCounter=-1;
	int freqListComponentCounter=-1;
	int num_cores;
	char* freqList[MAX_NUM_CORES];
	clock_t begin_time, end_time;   // To remove time, just don't use verbose or delete any line
					// with the comment #TIMESTAMP

	FILE *inputarea, *inputtemp, *output, *datfile, *configfile;

	block *firstblock, *currentblock, *endblock, *aux;

	// If the used does not provide sufficient data,
	// display proper usage
	if(argc < 3) {
		usage(argc,argv);
		return 0;
	}

	// Open the files. Check if they are really there
	inputarea = fopen(argv[1], "r");
	inputtemp = fopen(argv[2], "r");
	if(inputarea == NULL) {
		printf("Area file not found. Check paths.\n");
		usage(argc, argv);
		return 0;
	} else if(inputtemp == NULL) {
		printf("Temperature file not found. Check paths.\n");
		usage(argc, argv);
		return 0;
	}
	
	// Initiate parameters with deafult values
	beta = DEFAULT_BETA;
	iterations = DEFAULT_ITERATIONS;
	failuremodels = DEFAULT_FAILURES;
	MTTF = DEFAULT_MTTF;
	stdtemp = DEFAULT_TEMP;
	verbose = VERBOSE_OFF;
	reference = STARTING_REFERENCE;
	vdd = DEFAULT_VDD;
	output = NULL;
	datfile = NULL;
	configfile = NULL;
	//milad changes	
	for (int i=0;i<MAX_NUM_CORES;i++){
		VddList[i]=DEFAULT_VDD;
	}
	// Read options and substitute if necessary
	for(i = 3; i < argc ; i++) {
		if ((strcmp(argv[i], "-V") == 0) || (strcmp(argv[i], "--voltage") == 0)) {
			vdd = (long double)atof(argv[i+1]);
			//milad changes			
			for (i=0;i<MAX_NUM_CORES;i++)
				VddList[i]=vdd;
		}
	}
	for(i = 3; i < argc ; i++) {
		if((strcmp(argv[i], "-b") == 0) || (strcmp(argv[i], "--beta") == 0)){
			beta = (long double)atof(argv[i+1]);
		} else if ((strcmp(argv[i], "-i") == 0) || (strcmp(argv[i], "--iterations") == 0)) {
			iterations = atol(argv[i+1]);
		} else if ((strcmp(argv[i], "-f") == 0) || (strcmp(argv[i], "--failures") == 0)) {
			failuremodels = atoi(argv[i+1]);	
			// Sanity check
			if(failuremodels == 0) {
				printf("Error: At least one failure model needs to be considered.\n");
				usage(argc, argv);
				return 0;			
			}	
		} else if ((strcmp(argv[i], "-l") == 0) || (strcmp(argv[i], "--lifetime") == 0)) {
			MTTF = (long double)atof(argv[i+1]);
		} else if ((strcmp(argv[i], "-t") == 0) || (strcmp(argv[i], "--temperature") == 0)) {
			stdtemp = (long double)atof(argv[i+1]);
		} else if ((strcmp(argv[i], "-v") == 0) || (strcmp(argv[i], "--verbose") == 0)) {
			verbose = VERBOSE_ON;

			
		//milad changes
		} else if ((strcmp(argv[i], "-VL") == 0) || (strcmp(argv[i], "--VddList") == 0)) { 
			VddListString = argv[i+1];
			printf ("VddListString = %s\n",VddListString);
			VddListString = strtok(VddListString,",");
			while (VddListString != NULL)
			{
				VddListComponentCounter++;
				VddList[VddListComponentCounter] = atof(VddListString);
				VddListString = strtok (NULL, ",");
			}


		} else if ((strcmp(argv[i], "-freq") == 0) || (strcmp(argv[i], "--Frequency") == 0)) { 
			freqListString = argv[i+1];
			printf ("freqListString = %s\n",freqListString);
			freqListString = strtok(freqListString,",");
			while (freqListString != NULL)
			{
				freqListComponentCounter++;
				//strlen(freqListString)-=2;
				freqListString[strlen(freqListString)-2]=freqListString[strlen(freqListString)];
				freqList[freqListComponentCounter] = freqListString;
				printf("freqList[%d]=%s,len=%d\n",freqListComponentCounter,freqList[freqListComponentCounter],strlen(freqListString));
				freqListString = strtok (NULL, ",");
			}
			printf ("%d\n",freqListComponentCounter);
			for (i=0;i<=freqListComponentCounter;i++){
				if (strcmp(freqList[i],"FREQ_2GHz") == 0)
					VddList[i]=1.1;
				else if (strcmp(freqList[i],"FREQ_1900MHz") == 0)
					VddList[i]=1.03;
				else if (strcmp(freqList[i],"FREQ_1800MHz") == 0)
					VddList[i]=0.95;
				else if (strcmp(freqList[i],"FREQ_1700MHz") == 0)
					VddList[i]=0.9;
				else if (strcmp(freqList[i],"FREQ_1600MHz") == 0)
					VddList[i]=0.85;
				else if (strcmp(freqList[i],"FREQ_1500MHz") == 0)
					VddList[i]=0.82;
				else if (strcmp(freqList[i],"FREQ_1400MHz") == 0)
					VddList[i]=0.8;
				else if (strcmp(freqList[i],"FREQ_1300MHz") == 0)
					VddList[i]=0.75;
				else if (strcmp(freqList[i],"FREQ_1200MHz") == 0)
					VddList[i]=0.75;
				else if (strcmp(freqList[i],"FREQ_1100MHz") == 0)
					VddList[i]=0.75;
				else if (strcmp(freqList[i],"FREQ_1GHz") == 0)
					VddList[i]=0.75;
				else if (strcmp(freqList[i],"FREQ_800MHz") == 0)
					VddList[i]=0.75;
				else if (strcmp(freqList[i],"FREQ_500MHz") == 0)
					VddList[i]=0.75;


			}


		} else if (strcmp(argv[i], "-o") == 0) {

			if(i+1 >= argc) output = fopen(DEFAULT_OUTPUTFILE, "w");
			else if(argv[i+1][0] == '-') output = fopen(DEFAULT_OUTPUTFILE, "w");
			else output = fopen(argv[i+1], "w");

			if(output == NULL) printf("Could not access output file as write. Continuing anyway...\n");

		} else if (strcmp(argv[i], "-d") == 0) {

			if(i+1 >= argc) datfile = fopen(DEFAULT_DATFILE, "w");
			else if(argv[i+1][0] == '-') datfile = fopen(DEFAULT_DATFILE, "w");
			else datfile = fopen(argv[i+1], "w");

			if(datfile == NULL) printf("Could not access .dat file as write. Continuing anyway...\n");

		} else if (strcmp(argv[i], "-c") == 0) {

			configfile = fopen(argv[i+1], "r");
			if(configfile == NULL) printf("Could not access config file as read. Continuing anyway...\n");

		}
			
	}

	firstblock = (block *) malloc(sizeof(block));
	currentblock = firstblock;
	firstblock->nextblock = NULL;

	// Build "floorplan"
	if (verbose) printf("Reading area file\n");
	while(fscanf(inputarea, "%s", currentblock->name) != EOF) {
		if(currentblock->name[0] != '#') {
			fscanf(inputarea, "%Lf", &width);
			fscanf(inputarea, "%Lf", &height);
			currentblock->area = width*height;
			// Does the area make sense?
			if(currentblock->area <= 0) {
				printf("Error: Block areas need to be greater than zero\n");
				return SANITY_CHECK_ERROR; // Memory might not be freed. Take care here.
			}
			currentblock->failures = 0;
			currentblock->t = SANITY_CHECK_ERROR;
			currentblock->nextblock = (block *) malloc(sizeof(block));
			//milad changes 
			//here it just work for upto 100 cores
			currentblock->coreNumber=atoi(currentblock->name);
			currentblock->Vdd = VddList[currentblock->coreNumber];
			//printf ("%s with Vdd = %.2Lf\n",currentblock->name,currentblock->Vdd);			
					
			num_cores=currentblock->coreNumber;
			currentblock = currentblock->nextblock;
		}
		fscanf(inputarea, "%[^\n]", currentblock->name);
	}
	num_cores++;
	printf ("num_cores=%d\n",num_cores);
	for (i=0;i<num_cores;i++)
		printf ("VddList[%d] = %.2Lf\n",i,VddList[i]);
	printf ("Calibration Voltage = %.2Lf\n\n",vdd);
	endblock = currentblock;
	currentblock = firstblock;

	// Read temperatures
	if (verbose) printf("Reading temperture file\n");
	while(fscanf(inputtemp, "%s", blockname) != EOF) {

		// Does the temp make sense?
		fscanf(inputtemp, "%Lf", &temp);
		//if(temp <= 0) {
		//	printf("Error: Block tempertures need to be greater than zero\n");
		//	return SANITY_CHECK_ERROR; // Memory might not be freed. Take care here.
		//} //I removed this because I do another check and don't exit, just correct

		// Find block names that match
		while(currentblock != endblock) {
			if(strcmp(currentblock->name, blockname) == 0) currentblock->t = temp;
			currentblock = currentblock->nextblock;
		}
				
		currentblock = firstblock;
		fscanf(inputarea, "%[^\n]", currentblock->name);
	}

	/* Uncomment if you want to debug the linked list 

	currentblock = firstblock;
	while(currentblock != endblock) {
		printf("Block name: %s / Temperature: %Le / Area: %Le\n", currentblock->name, currentblock->t, currentblock->area);
		currentblock = currentblock->nextblock;
		getchar();
		// Windows: system("pause");
	} */

	currentblock = firstblock;
	while(currentblock != endblock) {
		if(currentblock->t <= 0) {
			currentblock->t = stdtemp;
			if(verbose) printf("WARNING: Tile %s not assigned a temperature, assuming %3.2LfK\n", currentblock->name, currentblock->t);
		}
		currentblock = currentblock->nextblock;
	}

	
	if (verbose) printf("Done!\n");
	// Start the random number generator (Seed it)
	Start_Seeder();
	if (verbose) printf("Seeding the random number generator...\n");

	// Informative echo
	printf("Calculating target SoC reliability with parameters\n");
	printf("Weibull Shape (Beta) = %.4Lf\n", beta);

	printf("With failure models:");
	if(failuremodels & NBTI) printf(" NBTI");
	if(failuremodels & TDDB) printf(" TDDB");
	printf("\n");

	printf("and using %ld iterations.\n\n", iterations);

	// Calibration sequence. This calibrates the MTTF as being
	// the default value for a standard 1mm x 1mm block at
	// the default temperature

	/* This is the part I am most concerned about. This assumes
	   the MTTF for both failure models will be the same for
	   Ceteris Paribus, which is most likely not true. The
	   argument that satisfies my concerns the most is that
	   we are always COMPARING MTTFs, not working with
	   abosolute values. */
	
	// NBTI
	if(failuremodels & NBTI) {
		NBTIcalibration = MTTF/Calculate_NBTI_MTTF(stdtemp);
		if(verbose) printf("NBTI cal. factor is: %Le\n", NBTIcalibration);
	}

	// TDDB
	if(failuremodels & TDDB) {
		TDDBcalibration = MTTF/Calculate_TDDB_MTTF(stdtemp, vdd);
		if(verbose) printf("TDDB cal. factor is: %Le\n", TDDBcalibration);
		
	}

	if(verbose) begin_time = clock(); // #TIMESTAMP

	//MTTF = Final_MTTF_Approach(firstblock, endblock);
	

	/* // This uses the theorical result to compare to the one obtained. This is
		// for verification purposes and see if the MC algorithm converges
	xprime = 0;
	currentblock = firstblock->nextblock;
	

	if(failuremodels & NBTI) {
			MTTF = NBTIcalibration*Calculate_NBTI_MTTF(firstblock->t)*(STANDARD_AREA/firstblock->area);
			alpha = 1/pow(Calculate_Alpha(MTTF, beta), beta);
			xprime = 1;
	}
	if(failuremodels & TDDB) {
			MTTF = TDDBcalibration*Calculate_TDDB_MTTF(firstblock->t, vdd)*(STANDARD_AREA/firstblock->area);
			if(xprime == 1) {
				alpha += 1/pow(Calculate_Alpha(MTTF, beta), beta);
			} else {
				alpha = 1/pow(Calculate_Alpha(MTTF, beta), beta);
				xprime = 1;
			}
				
		}
	
	while(currentblock != endblock) {
			
			//NBTI
			if(failuremodels & NBTI) {
				MTTF = NBTIcalibration*Calculate_NBTI_MTTF(currentblock->t)*(STANDARD_AREA/currentblock->area);
				alpha += 1/pow(Calculate_Alpha(MTTF, beta), beta);
			}
			//TDDB
			if(failuremodels & TDDB) {
				MTTF = TDDBcalibration*Calculate_TDDB_MTTF(currentblock->t, vdd)*(STANDARD_AREA/currentblock->area);
				alpha += 1/pow(Calculate_Alpha(MTTF, beta), beta);
			}
			currentblock = currentblock->nextblock;
	
	};
	
	alpha = 1/alpha;
	alpha = pow(alpha, 1/beta);
	MTTF = alpha*exp(lgammal(1+(1/beta)));
	printf("Estimated end alpha = %Le\n", alpha);
	printf("Estimated MTTF = %Le\n", MTTF);
	*/
	
	

	
	average = 0;
	for(i = 0; i < iterations; i++) {
		
		//Needs to run manually the first time because of x initial value
		aux = firstblock;
		currentblock = firstblock->nextblock;
		xprime = 0;
		
		//NBTI
		if(failuremodels & NBTI) {
			MTTF = Calculate_NBTI_MTTF(firstblock->t);
			alpha = Calculate_Alpha(MTTF, beta);
			x = NBTIcalibration*Gen_Weibull_Sample(alpha, beta)*(STANDARD_AREA/firstblock->area);
			xprime = 1;
		}
		//TDDB
		if(failuremodels & TDDB) {
			//milad changes
			MTTF = Calculate_TDDB_MTTF(firstblock->t, firstblock->Vdd);
			alpha = Calculate_Alpha(MTTF, beta);
			if(xprime == 1) {
				xprime = TDDBcalibration*Gen_Weibull_Sample(alpha, beta)*(STANDARD_AREA/firstblock->area);
				if(x > xprime) x = xprime;
			} else {
				x = TDDBcalibration*Gen_Weibull_Sample(alpha, beta)*(STANDARD_AREA/firstblock->area);
				xprime = 1;
			}
				
		}
		
		
		/* It is easy to expand and include other failure models in this program. One simply
		   has to calculate the MTTF using the known failure model formula,
		   and then derive the expression to generate random numbers. If the
		   generated number is less than the previous ones, keep it. Else, discard it */
		
		// End of first block. All the other blocks are contained in the loop
		
		while(currentblock != endblock) {
			
			//NBTI
			if(failuremodels & NBTI) {
				MTTF = Calculate_NBTI_MTTF(currentblock->t);
				alpha = Calculate_Alpha(MTTF, beta);
				xprime = NBTIcalibration*Gen_Weibull_Sample(alpha, beta)*(STANDARD_AREA/currentblock->area);
				if(x > xprime) {
					x = xprime;
					aux = currentblock;

				}
			}
			//TDDB
			if(failuremodels & TDDB) {
				//milad changes
				MTTF = Calculate_TDDB_MTTF(currentblock->t, currentblock->Vdd);
				alpha = Calculate_Alpha(MTTF, beta);
				xprime = TDDBcalibration*Gen_Weibull_Sample(alpha, beta)*(STANDARD_AREA/currentblock->area);
				if(x > xprime) {
					x = xprime;
					aux = currentblock;
				}
			}
			currentblock = currentblock->nextblock;
	
		};

		aux->failures += 1; // Increases the failures number of the block which failed

		// Prints the content to the CSV file

		// The MAX_COL parameter specifies how many columns the CSV file will have
		// for any program, such as MATLAB, this does not matter, but it might make
		// manual inspection more pleasing.
		if(datfile != NULL) {
			fprintf(datfile, "%Le, ", x);
			if(((i+1)%MAX_COL) == 0) fprintf(datfile, "\n");
		}
		
		average += x/(long double)iterations; // Average for mean time ( E[x] )

		// Lets the user know the progress. Useful for big iteration numbers or too many blocks 
		if(verbose) {
			if((i+1) == reference) {
				printf("Just passed iteration %ld\n", (i+1));
				reference *= REFERENCE_FREQUENCY; // Non-linear
				//reference += REFERENCE_FREQUENCY; //Linear
			}
		}

	} 

	if(verbose) {

		end_time = clock(); // #TIMESTAMP

		iterations = (long int)(end_time - begin_time); // #TIMESTAMP
		iterations = iterations/CLOCKS_PER_SEC;		// #TIMESTAMP
		printf("Total time elapsed: %02d days, %02d hours, %02d minutes and %02d seconds\n", (int)(iterations/SECONDS_PER_DAY), (int)(iterations/SECONDS_PER_HOUR)%24, (int)(iterations/SECONDS_PER_MINUTE)%60, (int)iterations%60);		// #TIMESTAMP
	}
	

	// Prints to output file if required
	// Output file is way more informative
	if(output != NULL) {
		fprintf(output, "Final statistics:\n");
		currentblock = firstblock;
		while(currentblock != endblock) {
			fprintf(output, "Block name: %s | Total failures: %ld | Failure percentage: %.4f\n", currentblock->name, currentblock->failures, 100*(float)((float)currentblock->failures/(float)iterations));
			currentblock = currentblock->nextblock;
		}
		fprintf(output, "SoC final MTTF: %Le\n", average);
	}
		

	printf("SoC final MTTF: %Le\n", average);

	// Let's not hog memory, shall we?
	currentblock = firstblock;
	while(currentblock != endblock) {
		aux = currentblock->nextblock;
		free(currentblock);
		currentblock = aux;
	}
	free(endblock);	

	fclose(inputarea);
	fclose(inputtemp);
	if(output != NULL) fclose(output);
	if(datfile != NULL) fclose(datfile);

	return 1;

}
