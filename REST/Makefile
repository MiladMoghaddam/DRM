CC = g++

#CFLAGS = -Wall -pg -lm
CFLAGS = -O3 -lm

all: wipe obj_files REST

obj_files:	
	$(CC) $(CFLAGS) -c main.c 
	$(CC) $(CFLAGS) -c statistics.c

REST:
	$(CC) -o REST $(CFLAGS) main.o statistics.o

wipe: 
	rm -rf REST *.o *.so *.out

clean: 
	rm -rf .#* *~ REST *.o *.so ;
