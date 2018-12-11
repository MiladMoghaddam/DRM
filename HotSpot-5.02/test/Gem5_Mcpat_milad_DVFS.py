#!/usr/bin/env python

print "\nNOC-based script for new GEM5 manipulated by Milad Ghorbani Moghaddam\n"
print "it should be called" 
print "	1 - without argument (default 'config.ini' or 'stats.txt')"
print "	2 - with argument first config_file second stats_file"

"""
SYNOPSIS
 
    m5-mcpat-parse.py [-h] [-v,--verbose] [--version] [--process_run_dirs_by_filter="[some characteristic sub string]"]
 
DESCRIPTION
 
    m5-mcpat-parse.py is a script for parsing M5 output and generating
    mcpat compatible xml. It is expected that you will want to modify
    this script to be compatible with your particular system. 
    
    Assumptions: 
    (1) Inside the run directories, the stats file is found in
        ./m5out/stats.txt
    (2) Inside the run directories, the config file is found in
        ./m5out/config.ini
    (3) The cache stats are assuming that you are using Jiayuan's
        directory cache coherence (You can easily change this)
    (4) You are willing to sit down for a 1/2 hour to change any differences
        your particular simulation model has. 
    
    Editing the code:
    
    Note that comments are present in the code to direct your attention. #TODO
    signifies that you should set the default value to match your systems parameters.
    If you have added this system parameter to the config.ini file, then you
    can put the related string filter in the m5_key field. #FIXME indicates
    a stat that I was not sure about and that you should check if you notice
    inconsistencies with expected behavior. 
    
    Likely, most of the changes you will add are in the functions addPower{Param|Stat}. 
    m5_key represents a unique string filter that identifies the stat in config.ini
    or stats output file. power_key is the corresponding McPat interface id that
    identifies the node in mcpat xml interface. By changing M5_keys, you can capture
    stats and params that you require. If you realize that you need to capture a stat 
    that is dependent on other stats, please look at the function generateCalcStats() 
    for an example of how to add calculated stats
 
EXAMPLES
 
    (1) To parse the current m5 run directory: $m50mcpat-parse.py
    (2) To parse all m5 run directories that begin with the prefix 'run:' with verbose output
     and meeting the assumptions above: $m5-mcpat-parse.py --process_run_dirs_by_filter="run:" -v
 
EXIT STATUS
 
    TODO: add exit code meanings
    (0) success with no errors
    (1) unable to find component
    (2) unable to handle multiple clock domains yet
    (3) cht does not have the key I generated for detailed cpu
    (4) child_id does not exist
    (5) child_id does not exist
    (6) parsed invalid stat
    (7) Identical component id occurs twice! Invalid Config
    (8) unable to perform conversion
 
AUTHOR
 
    Richard Strong <rstrong@cs.ucsd.edu>
 
LICENSE
 
    Copyright (c) [2009], Richard Strong <rstrong@cs.ucsd.edu>
 
    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.
 
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 
VERSION
 
    0.5 Alpha.
"""
 
import sys
import os
import traceback
import optparse
import time
import re
import math

READ_CONFIG='config.ini'
READ_STATS='stats.txt'
#print "It uses READ_CONFIG='config.ini' and READ_STATS='stats.txt'"
if len(sys.argv) ==3:
	READ_CONFIG=sys.argv[1]
	READ_STATS=sys.argv[2]


print "\nIt uses READ_CONFIG='%s' and READ_STATS='%s'\n" %(READ_CONFIG,READ_STATS)

def panic(msg, code):
    print "Error:%s" % (msg)
    os.sys.exit(code)

def warning(msg):
    global options
    if options.verbose:
        print "Warning:%s" %(msg)

def findBenchmarkTestSystem(benchmark):
    panic("Not used. I am wondering if I should set options.system_name")
    global options
    test_system=options.system_name
    
    if benchmark=="maerts" or benchmark=="stream":
        warning("chaging system name for stats of interest to 'client'")
        test_system="client"
    if benchmark=="webnew":
        warning("changing system name for stats of interest to 'server'")
        test_system="server"
    
    options.system_name=test_system
    return test_system

def sortComponentList(components):
    names=[]
    temp_hash={}
    for comp in components:
        names.append(comp.name)
        temp_hash[comp.name]=comp
#        print "temp_hash[%s]=%s"%(comp.name,temp_hash[comp.name])
#    print "names =%s" %names
    names.sort()
    ret=[]
    for comp_name in names:
        ret.append(temp_hash[comp_name])
    
    
    return ret
    
class Component:
    UNKNOWN=None
    CORE=1
    FILTER_TYPES = ["Tsunami"\
                   , "IsaFake"\
                   , "SimpleDisk"\
                   , "Terminal"\
                   , "Crossbar"\
                   , "IntrControl"\
                   , "IdeDisk"\
                   , "ExeTracer"\
                   , "AlphaInterrupts"\
                   , "Tracer"\
                   , "Bridge"\
                   #, "AtomicSimpleCPU"\
                   , "FUPool"\
                   , "BusConn"]

    def __init__(self, id, params, name=None):
        temp = id.split('.')
        if name==None:
            self.name = temp[len(temp)-1] #last field specifies what this component is
        else:
            self.name=name
        self.id = id
        self.params = params
        self.re_id=None
        self.re_name=None
        self.translated_params = {}
        self.translated_params_order = []
        self.children = []
        self.statistics = {}
        self.translated_statistics = {}
        self.calc_statistics = {}
        self.translator = Component.UNKNOWN
        self.power_xml_filter=False
        self.translated_statistics_order=[]

    '''
    generate new components to be writen to summary.xml
    '''
    def formXml(self, parent_node, doc):
        new_component = doc.createElement("component")
        parent_node.appendChild(new_component)
	main_self_id=self.id
#	x='none'	
#	if 'system.ruby.' in self.id: 
#		print 'system.ruby in self.id in formXml milad_debug'
#		new_self_id= self.id.split('.ruby')
#		self.id=new_self_id[0]+new_self_id[1]
#		x= new_self_id[0]+new_self_id[1]		
#		new_component.setAttribute("id",self.id )	
	#else:       
 	new_component.setAttribute("id", self.id)
        new_component.setAttribute("name", self.name)
        #print self.name
        #add params settings 
        for param_key in self.params:
            new_param = doc.createElement("param")
            new_param.setAttribute("name", param_key)
            new_param.setAttribute("value", self.params[param_key])
            new_component.appendChild(new_param)

        #add statistics
        for stat_key in self.statistics:
            new_stat = doc.createElement("stat")
            new_stat.setAttribute("name", stat_key)
            new_stat.setAttribute("value", self.statistics[stat_key])
            new_component.appendChild(new_stat)

        #add architectural stats for this level. 
#	if  x in self.id: 		       
#		for child in self.children:
#	            print 'yesssssssssssssssssss child= %s'
#		    child.formXml(parent_node, doc)
#		    print 'parent_node=%s' % parent_node
#	else:	
	for child in self.children:		
   	    child.formXml(new_component, doc)
    '''
    generate new components to be writen to power.xml
    '''
    def formXmlPower(self, parent_node, doc):
#milad: elminating some extra components  ( milad debug) (cpufreq for DVFS) (other for run)
        if 'cpu' in self.id:
#		print '9: formXml id: %s' % self.id
		if 'L1Dcache' in self.id or 'L1Icache' in self.id:
#			print '9: formXml id: %s' % self.id
			if 'L1IcacheMemory' not in self.id and 'L1DcacheMemory' not in self.id:
				return
		if 'isa' in self.id:			
#			print '9: formXml id: %s' % self.id
			return
	if 'cpu_clk_domain' in self.id or 'cpu_voltage_domain' in self.id or 'cpufreq' in self.id: #what is whown is the re_id which/ 
									   #is core_clk_domain and core_voltage_domain
		return
#.................................
        global options
        new_component = doc.createElement("component") # to be written in power.xml
        if self.power_xml_filter == True: # should not be written in power.xml
#		print '10: %s.power_xml_filter == True' % self.id           
		return
        parent_node.appendChild(new_component)
#	print '11 :%s.re_id = %s'% (self.id ,self.re_id)        
	if self.re_id == None:
            new_component.setAttribute("id", self.id)
        else:
            new_component.setAttribute("id", self.re_id)
        if self.re_name == None:    
            new_component.setAttribute("name", self.name)
        else:
            new_component.setAttribute("name", self.re_name)
#        print "re.id , rename = %s %s, %s %s" %(self.id,self.re_id,self.name,self.re_name)
        #add params settings 
        for param_key in self.translated_params_order:
#	    print '17: %s.translated_params_order=%s == %s:' % (self.id,self.translated_params_order,self.translated_params)
            new_param = doc.createElement("param")
            new_param.setAttribute("name", param_key)
            new_param.setAttribute("value", self.translated_params[param_key])
            new_component.appendChild(new_param)

        #add statistics
        for stat_key in self.translated_statistics_order:
#	    print '%s.translated_statistics_order=%s == %s' % (self.id,self.translated_statistics_order, self.translated_statistics)	
            new_stat = doc.createElement("stat")
            new_stat.setAttribute("name", stat_key)
            new_stat.setAttribute("value", self.translated_statistics[stat_key])
            new_component.appendChild(new_stat)

        # <component id="system" name="system">
        #     <param name="children" value="cpu0 cpu1 cpu2 cpu3 
        #     dir_cntrl0 dir_cntrl1 dir_cntrl2 dir_cntrl3  
        #     disk0 disk2 dma_cntrl0 dma_cntrl1 intrctrl 
        #     l1_cntrl0 l1_cntrl1 l1_cntrl2 l1_cntrl3 
        #     l2_cntrl0 l2_cntrl1 l2_cntrl2 l2_cntrl3 
        #     physmem piobus ruby simple_disk terminal tsunami"/>

        if self.name == options.system_name: # that is "system"
            new_children=[]
            # from among all children of this component keep those whose name (in that order): 
            # contains "filter", does not contain "unfilter", does not contain "unfilter2"
            filters   =[options.cpu_name,"L1Directory","L2cacheMemory","NoC","physmem","mc","niu","pcie","flashc"]
            unfilters =[None,            None,       None,           None, None,     None, None, None,  None]
            unfilters2=[None,            None,       None,           None, None,     None, None, None,  None]
  
            filter_pair=zip(filters, unfilters, unfilters2)
            for filter, unfilter, unfilter2 in filter_pair:
                temp_new=[]
                # system has children=cpu0 cpu1 cpu2 cpu3 dir_cntrl0 dir_cntrl1...
                for child in self.children: # cpu0 cpu1 cpu2 cpu3 l1_cntrl0 ... as system's children
                    # NOTE: filtering here is done based on the name and not re_name
                    # which might have been affected during the renaming routine!
                    child_name_to_use = child.name;
                    if (child.re_name != None): child_name_to_use = child.re_name
                    #print child_name_to_use
                    if filter in child.name: # "cpu" in cpu0,cpu1...; "l1_cntrl" in l1_cntrl
                        if (unfilter==None or unfilter not in child.name) \
                            and (unfilter2==None or unfilter2 not in child.name):
                            #print "filter:%s unfilter:%s unfilter2:%s child.name:%s"%(filter, unfilter, unfilter2, child.name)
                            temp_new.append(child)
#			    print ' 30 appent.child = id=%s, re_id=%s, name=%s, re_name=%s'% (child.id,child.re_id,child.name,child.re_name)
                new_children += sortComponentList(temp_new)
#		print '31 new_children= %s' %new_children
            self.children=new_children
        '''
        if self.params.has_key('type') and (self.params['type'] == "TimingSimpleCPU"):
            new_children=[]
            # this basically sorts children and prints them in this order in power.xml
            filters  =["PBT",options.itb_name, "icache", options.dtb_name, "dcache", "BTB"]
            unfilters=[None, None,             None,     None,             None,     None]
            filter_pair=zip(filters, unfilters)
            for filter, unfilter in filter_pair:
                temp_new=[]
                for child in self.children:
                    if filter in child.name:
                        temp_new.append(child)
                new_children += sortComponentList(temp_new)
            self.children=new_children
        '''
        for child in self.children:
            child.formXmlPower(new_component, doc) # recursive call?
        

    '''
    checkToFilter() is responsible for seeing the current component
    should be filtered from the power xml file. 
    '''
    def checkToFilter(self):
        global options
        ptype = self.params['type']
        for f in self.FILTER_TYPES:
            if ptype == f:
                self.power_xml_filter=True
            
        if "TimingSimpleCPU" in self.params['type'] and options.cpu_name not in self.name:
            self.power_xml_filter=True
        if "AtomicSimpleCPU" in self.params['type'] and options.cpu_name not in self.name:
            self.power_xml_filter=True
        
        if "iocache" in self.name:
            self.power_xml_filter=True
        
        if "server" in self.name:
            self.power_xml_filter=True
        
        if "client" in self.name:
            self.power_xml_filter=True
        
        if "etherdump" in self.name or "etherlink" in self.name:
            self.power_xml_filter=True
 
    def checkToRenameReid(self):
        global options
        ptype = self.params['type']
        if options.cpu_name in self.name:
            self.re_name=self.name.replace(options.cpu_name, "core")
            self.re_id=self.id.replace(options.cpu_name, "core")       
        if ("BTB" in self.id):
            self.re_id=self.id.replace(options.cpu_name, "core")
        
        # cris:
        # Q1: what happens with the sht[]'s if I make these changes?
        # Q2: children names stay the old l1_cntrl!
        if ("L1DcacheMemory" in self.id):
            self.re_id=self.id.replace(options.cpu_name, "core")
            self.re_id=self.re_id.replace("L1DcacheMemory", "dcache")
            self.re_name=self.name.replace("L1DcacheMemory", "dcache")
        if ("L1IcacheMemory" in self.id):
            self.re_id=self.id.replace(options.cpu_name, "core")
            self.re_id=self.re_id.replace("L1IcacheMemory", "icache")
            self.re_name=self.name.replace("L1IcacheMemory", "icache")
        if ("L2cacheMemory" in self.id):
            self.re_id=self.id.replace("L2cacheMemory", "L2")
            self.re_name=self.name.replace("L2cacheMemory", "L2") 
        ''' 
        if ("directory" in self.id):
            self.re_id=self.id.replace("directory", "L1Directory")
            self.re_name=self.name.replace("directory", "L1Directory")
        '''
	#milad debug re_id  
#	if ("L1Dcache" in self.id):
#		if 'cpu' in self.id:	    
#		     self.id=self.id.replace("L1Dcache", "dcache")
# 	             self.name=self.name.replace("L1Dcache", "dcache")	
#	if ("L1Icache" in self.id):
#		if 'cpu' in self.id:	    
#		     self.id=self.id.replace("L1Icache", "icache")
# 	             self.name=self.name.replace("L1Icache", "icache")	
#	if ("cpu" in self.id):
#	     self.re_id=self.id.replace(options.cpu_name, "core")
#            self.id=	self.id.replace(options.cpu_name, "core")
	if ('.ruby.L1Directory' in self.id):
	     self.re_id=self.id.replace('.ruby.', ".")		
        if ptype == 'AlphaTLB':
            # [system.cpu0.dtb]
            # type=AlphaTLB
            if self.name==options.itb_name:
                self.re_name=self.name.replace(options.itb_name,"itlb").replace(options.cpu_name, "core")
                self.re_id=self.id.replace(options.itb_name,"itlb").replace(options.cpu_name, "core")
            else:
                self.re_name=self.name.replace(options.dtb_name,"dtlb").replace(options.cpu_name, "core")
                self.re_id=self.id.replace(options.dtb_name,"dtlb").replace(options.cpu_name, "core")


'''
class Translator is used for finding and adding params and stats
to the xml. Define a translator for each unique component in your system
and make sure you add the assignment of the translator in setComponentTranslator
'''
class Translator:
    M5_PARAM=0
    CONVERSION=1
    DEFAULT_VALUE=2
    M5_STAT=3
    
    def __init__(self):
        self.power_params_order = []
        self.power_params = {}
        self.power_statistics = {}
        self.power_statistics_order = []
        None
    
    def addPowerParam(self, power_key, m5_key, default_value="NaV"):
        if not self.power_params.has_key(power_key):
            self.power_params_order.append(power_key)
        self.power_params[power_key] = {Translator.M5_PARAM: m5_key, Translator.DEFAULT_VALUE: default_value}
    
    def addPowerStat(self, power_key, m5_key, default_value="NaV"):
        if not self.power_statistics.has_key(power_key):
            self.power_statistics_order.append(power_key)
        self.power_statistics[power_key] = {Translator.M5_STAT: m5_key, Translator.DEFAULT_VALUE: default_value}
        
    '''
    translate_params(component) translates all params in component object
    from m5 parameters to the equivalent power model name
    '''
    def translate_params(self, component):
        for power_param_key in self.power_params_order:
            # example:
            # power_param_key = LSU_order
            # power_param = {0: 'unknown', 2: 'inorder'}
            power_param = self.power_params[power_param_key]
            #grab M5's version of the parameter needed and translate it to power file name
            self.translate_param(component, power_param, power_param_key)            
    '''
    translate_param(component, power_param) responsible for translating one M5 parameter
    to an m5 parameter and adding that parameter to the component translated_params variable
    '''
    def translate_param(self, component, power_param, key):
        #find the translated value if it exists
        component.translated_params_order.append(key)
        try:
            #print component.params[power_param[Translator.M5_PARAM]]
            component.translated_params[key] = component.params[power_param[Translator.M5_PARAM]]
        except:
            #if it doesn't exist, use a default value
            component.translated_params[key] = power_param[Translator.DEFAULT_VALUE]
    
    '''
    translate_statistics(component) translates all statistics in component object
    from m5 statistics to the equivalent power model statistics
    '''
    def translate_statistics(self, component):
        for power_stat_key in self.power_statistics_order:
            power_stat = self.power_statistics[power_stat_key]
            #grab M5's version of the statistic needed and translate it to power file stat
            self.translate_statistic(component, power_stat, power_stat_key)   
                         
    '''
    translate_statistc(component, power_param) responsible for translating one M5 statistic
    to a m5 statistic and adding that parameter to the component translated_statistics variable
    '''
    def translate_statistic(self, component, power_stat, key):
        #find the translated value if it exists
        component.translated_statistics_order.append(key)
        try:
            component.translated_statistics[key] = component.statistics[power_stat[Translator.M5_STAT]]
        except:
            #if it doesn't exist, use a default value
            component.translated_statistics[key] = power_stat[Translator.DEFAULT_VALUE]
                    
        
class InOrderCore(Translator):
    def __init__(self):
        Translator.__init__(self)
        #reverse translation from m5 params to power params
        #params 
        self.addPowerParam(power_key="clock_rate", m5_key="clockrate", default_value="NaV")
        self.addPowerParam(power_key="instruction_length", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="opcode_width", m5_key="unknown", default_value="7") #TODO: set your value
        self.addPowerParam(power_key="machine_type", m5_key="unknown", default_value="1") # 1 for inorder
        self.addPowerParam(power_key="number_hardware_threads", m5_key="numThreads", default_value="1") 
        self.addPowerParam(power_key="fetch_width", m5_key="unknown", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="number_instruction_fetch_ports", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="decode_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="issue_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="commit_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="fp_issue_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="prediction_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="pipelines_per_core", m5_key="unknown", default_value="1,1") #TODO: set your value
        self.addPowerParam(power_key="pipeline_depth", m5_key="unknown", default_value="7,10") #TODO: set your value
        self.addPowerParam(power_key="ALU_per_core", m5_key="unknown", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="MUL_per_core", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="FPU_per_core", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="instruction_buffer_size", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="decoded_stream_buffer_size", m5_key="unknown", default_value="16") #TODO: set your value
        self.addPowerParam(power_key="instruction_window_scheme", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="instruction_window_size", m5_key="unknown", default_value="16") 
        self.addPowerParam(power_key="fp_instruction_window_size", m5_key="unknown", default_value="16") 
        self.addPowerParam(power_key="ROB_size", m5_key="unknown", default_value="80")
        self.addPowerParam(power_key="archi_Regs_IRF_size", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="archi_Regs_FRF_size", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="phy_Regs_IRF_size", m5_key="unknown", default_value="32") 
        self.addPowerParam(power_key="phy_Regs_FRF_size", m5_key="unknown", default_value="32") 
        self.addPowerParam(power_key="rename_scheme", m5_key="unknown", default_value="0") 
        self.addPowerParam(power_key="register_windows_size", m5_key="unknown", default_value="0")
        self.addPowerParam(power_key="LSU_order", m5_key="unknown", default_value="inorder") #TODO: set your value
        self.addPowerParam(power_key="store_buffer_size", m5_key="unknown", default_value="64")
        self.addPowerParam(power_key="load_buffer_size", m5_key="unknown", default_value="0")
        self.addPowerParam(power_key="memory_ports", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="RAS_size", m5_key="unknown", default_value="32")
        #statistics
        self.addPowerStat(power_key="total_instructions", m5_key="committedInsts", default_value="0") 
        self.addPowerStat(power_key="int_instructions", m5_key="num_int_insts", default_value="0")
        self.addPowerStat(power_key="fp_instructions", m5_key="num_fp_insts", default_value="0") 
        self.addPowerStat(power_key="branch_instructions", m5_key="num_conditional_control_insts", default_value="0") # TODO: check this
        self.addPowerStat(power_key="branch_mispredictions", m5_key="unknown", default_value="0") # TODO: set your value
        self.addPowerStat(power_key="load_instructions", m5_key="num_load_insts", default_value="0")
        self.addPowerStat(power_key="store_instructions", m5_key="num_store_insts", default_value="0")
        self.addPowerStat(power_key="committed_instructions", m5_key="committedInsts", default_value="0")
        self.addPowerStat(power_key="committed_int_instructions", m5_key="num_int_insts", default_value="0") 
        self.addPowerStat(power_key="committed_fp_instructions", m5_key="num_fp_insts", default_value="0")
        self.addPowerStat(power_key="pipeline_duty_cycle", m5_key="unknown", default_value="0.5") #TODO: set your value
        self.addPowerStat(power_key="total_cycles", m5_key="numCycles", default_value="0") 
        self.addPowerStat(power_key="idle_cycles", m5_key="num_idle_cycles", default_value="0") #FIXME
        self.addPowerStat(power_key="busy_cycles", m5_key="num_busy_cycles", default_value="0") #FIXME
        self.addPowerStat(power_key="ROB_reads", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="ROB_writes", m5_key="unknown", default_value="0")
        self.addPowerStat(power_key="rename_accesses", m5_key="unknown", default_value="0")
        self.addPowerStat(power_key="fp_rename_accesses", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="inst_window_reads", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="inst_window_writes", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="inst_window_wakeup_access", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="fp_inst_window_reads", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="fp_inst_window_writes", m5_key="unknown", default_value="0") 
        self.addPowerStat(power_key="fp_inst_window_wakeup_access", m5_key="unknown", default_value="0")
        self.addPowerStat(power_key="int_regfile_reads", m5_key="num_int_register_reads", default_value="0")
        self.addPowerStat(power_key="float_regfile_reads", m5_key="num_fp_register_reads", default_value="0")
        self.addPowerStat(power_key="int_regfile_writes", m5_key="num_int_register_writes", default_value="0")
        self.addPowerStat(power_key="float_regfile_writes", m5_key="num_fp_register_writes", default_value="0")
        self.addPowerStat(power_key="function_calls", m5_key="num_func_calls", default_value="0")
        self.addPowerStat(power_key="context_switches", m5_key="kern.swap_context", default_value="0") 
        self.addPowerStat(power_key="ialu_accesses", m5_key="num_int_alu_accesses", default_value="0") 
        self.addPowerStat(power_key="fpu_accesses", m5_key="num_fp_alu_accesses", default_value="0")
        self.addPowerStat(power_key="mul_accesses", m5_key="unknown", default_value="0") #TODO: FIXME
        self.addPowerStat(power_key="cdb_alu_accesses", m5_key="num_int_alu_accesses", default_value="0") 
        self.addPowerStat(power_key="cdb_mul_accesses", m5_key="unknown", default_value="0") #TODO: FIXME
        self.addPowerStat(power_key="cdb_fpu_accesses", m5_key="num_fp_alu_accesses", default_value="0")
        #DO NOT CHANGE BELOW UNLESS YOU KNOW WHAT YOU ARE DOING
        self.addPowerStat(power_key="IFU_duty_cycle", m5_key="unknown", default_value="0.5")
        self.addPowerStat(power_key="LSU_duty_cycle", m5_key="unknown", default_value="0.25")
        self.addPowerStat(power_key="MemManU_I_duty_cycle", m5_key="unknown", default_value="0.5")
        self.addPowerStat(power_key="MemManU_D_duty_cycle", m5_key="unknown", default_value="0.25")
        self.addPowerStat(power_key="ALU_duty_cycle", m5_key="unknown", default_value="0.9")
        self.addPowerStat(power_key="MUL_duty_cycle", m5_key="unknown", default_value="0")
        self.addPowerStat(power_key="FPU_duty_cycle", m5_key="unknown", default_value="0.6")
        self.addPowerStat(power_key="ALU_cdb_duty_cycle", m5_key="unknown", default_value="0.9")
        self.addPowerStat(power_key="MUL_cdb_duty_cycle", m5_key="unknown", default_value="0")
        self.addPowerStat(power_key="FPU_cdb_duty_cycle", m5_key="unknown", default_value="0.6")
        

class OOOCore(Translator):
    def __init__(self):
        global options
        Translator.__init__(self)
        #reverse translation from m5 params to power params
        #params 
        self.addPowerParam(power_key="clock_rate", m5_key="clockrate")
        self.addPowerParam(power_key="opt_local", m5_key="unknown", default_value='1')
        self.addPowerParam(power_key="instruction_length", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="opcode_width", m5_key="unknown", default_value="7") #TODO: set your value
        self.addPowerParam(power_key="x86", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="micro_opcode_width", m5_key="unknown", default_value="8") #TODO: set your value
        self.addPowerParam(power_key="machine_type", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="number_hardware_threads", m5_key="numThreads", default_value="1") 
        self.addPowerParam(power_key="fetch_width", m5_key="fetchWidth", default_value="4") 
        self.addPowerParam(power_key="number_instruction_fetch_ports", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="decode_width", m5_key="decodeWidth", default_value="4")
        self.addPowerParam(power_key="issue_width", m5_key="issueWidth", default_value="4")
        self.addPowerParam(power_key="peak_issue_width", m5_key="issueWidth", default_value="6") #TODO: set your value
        self.addPowerParam(power_key="commit_width", m5_key="commitWidth", default_value="4")
        self.addPowerParam(power_key="fp_issue_width", m5_key="fp_issue_width", default_value="4") #TODO: set your value
        self.addPowerParam(power_key="prediction_width", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="pipelines_per_core", m5_key="unknown", default_value="1,1") #TODO: set your value
        self.addPowerParam(power_key="pipeline_depth", m5_key="unknown", default_value="7,7") #TODO: set your value
        if options.qualcomm:
            self.addPowerParam(power_key="ALU_per_core", m5_key="ALU_per_core", default_value="2") #TODO: set your value
        else:
            self.addPowerParam(power_key="ALU_per_core", m5_key="ALU_per_core", default_value="4") #TODO: set your value
        self.addPowerParam(power_key="MUL_per_core", m5_key="MUL_per_core", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="FPU_per_core", m5_key="FPU_per_core", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="instruction_buffer_size", m5_key="instruction_buffer_size", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="decoded_stream_buffer_size", m5_key="decoded_stream_buffer_size", default_value="16") #TODO: set your value
        self.addPowerParam(power_key="instruction_window_scheme", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="instruction_window_size", m5_key="numIQEntries", default_value="20") 
        self.addPowerParam(power_key="fp_instruction_window_size", m5_key="numIQEntries", default_value="15") 
        self.addPowerParam(power_key="ROB_size", m5_key="numROBEntries", default_value="80")
        self.addPowerParam(power_key="archi_Regs_IRF_size", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="archi_Regs_FRF_size", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="phy_Regs_IRF_size", m5_key="numPhysIntRegs", default_value="80") 
        self.addPowerParam(power_key="phy_Regs_FRF_size", m5_key="numPhysFloatRegs", default_value="72") 
        self.addPowerParam(power_key="rename_scheme", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="register_windows_size", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="LSU_order", m5_key="unknown", default_value="inorder") #TODO: set your value
        self.addPowerParam(power_key="store_buffer_size", m5_key="SQEntries", default_value="32")
        self.addPowerParam(power_key="load_buffer_size", m5_key="LQEntries", default_value="32")
        self.addPowerParam(power_key="memory_ports", m5_key="memory_ports", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="RAS_size", m5_key="RASSize", default_value="32")
        #statistics
        self.addPowerStat(power_key="total_instructions", m5_key="iq.iqInstsIssued", default_value="0") #m5_key="iq.iqInstsIssued"
        self.addPowerStat(power_key="int_instructions", m5_key="commit.int_insts", default_value="NaV")#m5_key="int_instructions"
        self.addPowerStat(power_key="fp_instructions", m5_key="commit.fp_insts", default_value="NaV")#m5_key="fp_instructions"
        self.addPowerStat(power_key="branch_instructions", m5_key="branchPred.condPredicted", default_value="NaV")#m5_key="BPredUnit.condPredicted"
        self.addPowerStat(power_key="branch_mispredictions", m5_key="branchPred.condIncorrect", default_value="NaV")#m5_key="BPredUnit.condIncorrect"
        self.addPowerStat(power_key="load_instructions", m5_key="commit.loads", default_value="NaV")#m5_key="load_instructions"
        self.addPowerStat(power_key="store_instructions", m5_key="iew.exec_stores", default_value="NaV")#m5_key="store_instructions"
        self.addPowerStat(power_key="committed_instructions", m5_key="commit.committedInsts", default_value="NaV") #m5_key="commit.count"
        self.addPowerStat(power_key="committed_int_instructions", m5_key="commit.int_insts", default_value="NaV")
        self.addPowerStat(power_key="committed_fp_instructions", m5_key="commit.fp_insts", default_value="NaV") 
        self.addPowerStat(power_key="pipeline_duty_cycle", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerStat(power_key="total_cycles", m5_key="numCycles", default_value="NaV")
        self.addPowerStat(power_key="idle_cycles", m5_key="idleCycles", default_value="NaV")
        self.addPowerStat(power_key="busy_cycles", m5_key="num_busy_cycles", default_value="NaV")
        self.addPowerStat(power_key="ROB_reads", m5_key="rob.rob_reads", default_value="34794891") #FIXME: rerun the experiments to include this statistic
        self.addPowerStat(power_key="ROB_writes", m5_key="rob.rob_writes", default_value="34794891") #FIXME: rerun the experiments to include this statistic
        self.addPowerStat(power_key="rename_reads", m5_key="rename.int_rename_lookups", default_value="0")
        self.addPowerStat(power_key="rename_writes", m5_key="unknown", default_value="0") #TODO: FIXME
        self.addPowerStat(power_key="fp_rename_reads", m5_key="rename.fp_rename_lookups", default_value="0") 
        self.addPowerStat(power_key="fp_rename_writes", m5_key="unknown", default_value="0") #TODO: FIXME
        self.addPowerStat(power_key="inst_window_reads", m5_key="iq.int_inst_queue_reads", default_value="NaV") 
        self.addPowerStat(power_key="inst_window_writes", m5_key="iq.int_inst_queue_writes", default_value="NaV") 
        self.addPowerStat(power_key="inst_window_wakeup_accesses", m5_key="iq.int_inst_queue_wakeup_accesses", default_value="NaV") 
        self.addPowerStat(power_key="fp_inst_window_reads", m5_key="iq.fp_inst_queue_reads", default_value="0") 
        self.addPowerStat(power_key="fp_inst_window_writes", m5_key="iq.fp_inst_queue_writes", default_value="NaV") 
        self.addPowerStat(power_key="fp_inst_window_wakeup_accesses", m5_key="iq.fp_inst_queue_wakeup_accesses", default_value="NaV")
        self.addPowerStat(power_key="int_regfile_reads", m5_key="int_regfile_reads", default_value="0")
        self.addPowerStat(power_key="float_regfile_reads", m5_key="fp_regfile_reads", default_value="0")
        self.addPowerStat(power_key="int_regfile_writes", m5_key="int_regfile_writes", default_value="0")
        self.addPowerStat(power_key="float_regfile_writes", m5_key="fp_regfile_writes", default_value="0")
        self.addPowerStat(power_key="function_calls", m5_key="commit.function_calls", default_value="NaV")
        self.addPowerStat(power_key="context_switches", m5_key="kern.swap_context", default_value="0")
        self.addPowerStat(power_key="ialu_accesses", m5_key="iq.int_alu_accesses", default_value="NaV") 
        self.addPowerStat(power_key="fpu_accesses", m5_key="iq.fp_alu_accesses", default_value="NaV")
        self.addPowerStat(power_key="mul_accesses", m5_key="iq.FU_type_0::IntMult", default_value="NaV")
        self.addPowerStat(power_key="cdb_alu_accesses", m5_key="iq.int_alu_accesses", default_value="NaV") 
        self.addPowerStat(power_key="cdb_mul_accesses", m5_key="iq.FU_type_0::IntMult", default_value="NaV")
        self.addPowerStat(power_key="cdb_fpu_accesses", m5_key="iq.fp_alu_accesses", default_value="NaV")
        #DO NOT CHANGE BELOW UNLESS YOU KNOW WHAT YOU ARE DOING
        self.addPowerStat(power_key="IFU_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="LSU_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="MemManU_I_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="MemManU_D_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="ALU_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="MUL_duty_cycle", m5_key="unknown", default_value="0.3")
        self.addPowerStat(power_key="FPU_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="ALU_cdb_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="MUL_cdb_duty_cycle", m5_key="unknown", default_value="0.3")
        self.addPowerStat(power_key="FPU_cdb_duty_cycle", m5_key="unknown", default_value="1")
        self.addPowerStat(power_key="number_of_BPT", m5_key="unknown", default_value="2")

class AlphaTLB(Translator): # Translation Lookaside Buffer
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="number_entries", m5_key="size")
        #statistics
        self.addPowerStat(power_key="fetch_accesses", m5_key="fetch_accesses", default_value="0")
        self.addPowerStat(power_key="fetch_misses", m5_key="fetch_misses", default_value="0")
        self.addPowerStat(power_key="data_accesses", m5_key="data_accesses", default_value="0")
        self.addPowerStat(power_key="data_misses", m5_key="data_misses", default_value="0")

class ITLB(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="number_entries", m5_key="size")
        #statistics
        self.addPowerStat(power_key="total_accesses", m5_key="total_accesses", default_value="0")
        self.addPowerStat(power_key="total_misses", m5_key="fetch_misses", default_value="0")
        self.addPowerStat(power_key="conflicts", m5_key="unknown", default_value="0") #FIXME: add this stat to M5. Sheng says it is the number of evictions. This is a question for the M5 community.
        
class DTLB(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="number_entries", m5_key="size")
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0")
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="0")        
        self.addPowerStat(power_key="read_misses", m5_key="read_misses", default_value="0")        
        self.addPowerStat(power_key="write_misses", m5_key="write_misses", default_value="0")
        self.addPowerStat(power_key="conflicts", m5_key="unknown", default_value="0") #FIXME: add this stat to M5. Sheng says it is the number of evictions. This is a question for the M5 community

class InstructionCache(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="icache_config", m5_key="is_icache")
        self.addPowerParam(power_key="buffer_sizes", m5_key="buffer_sizes")
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0") 
        self.addPowerStat(power_key="read_misses", m5_key="ReadReq_misses", default_value="0")
        self.addPowerStat(power_key="conflicts", m5_key="replacements", default_value="0")
        
class DataCache(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="dcache_config", m5_key="is_icache")
        self.addPowerParam(power_key="buffer_sizes", m5_key="buffer_sizes")
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0") 
        self.addPowerStat(power_key="read_misses", m5_key="read_misses", default_value="0")
        self.addPowerStat(power_key="conflicts", m5_key="replacements", default_value="0")
        
class SharedCacheL2(Translator):
    def __init__(self):
        global options
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="L2_config", m5_key="is_icache")
        self.addPowerParam(power_key="buffer_sizes", m5_key="buffer_sizes")
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="200")
        self.addPowerParam(power_key="ports", m5_key="unknown", default_value="1,1,1") #TODO: specify your value
        self.addPowerParam(power_key="device_type", m5_key="unknown", default_value=options.cache_device_type) #TODO: specify your value
        ##statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0") 
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="0") 
        self.addPowerStat(power_key="read_misses", m5_key="ReadReq_misses", default_value="0")
        self.addPowerStat(power_key="write_misses", m5_key="ReadExReq_misses", default_value="0") 
        self.addPowerStat(power_key="conflicts", m5_key="replacements", default_value="0") 
        self.addPowerStat(power_key="duty_cycle", m5_key="unknown", default_value="1.0")

class SharedCacheL3(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="L3_config", m5_key="is_icache")
        self.addPowerParam(power_key="buffer_sizes", m5_key="buffer_sizes")
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="100")
        self.addPowerParam(power_key="ports", m5_key="unknown", default_value="1,1,1") #TODO: specify your value
        self.addPowerParam(power_key="device_type", m5_key="unknown", default_value=options.cache_device_type) #TODO: specify your value
        ##statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0") 
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="0") 
        self.addPowerStat(power_key="read_misses", m5_key="ReadReq_misses", default_value="0")
        self.addPowerStat(power_key="write_misses", m5_key="ReadExReq_misses", default_value="0") 
        self.addPowerStat(power_key="conflicts", m5_key="replacements", default_value="0")

class Mesh(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params        
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="1400")
        self.addPowerParam(power_key="horizontal_nodes", m5_key="horizontal_nodes", default_value="2")
        self.addPowerParam(power_key="vertical_nodes", m5_key="vertical_nodes", default_value="2")
        self.addPowerParam(power_key="has_global_link", m5_key="has_global_link", default_value="0")
        self.addPowerParam(power_key="link_throughput", m5_key="link_throughput", default_value="1")
        self.addPowerParam(power_key="link_latency", m5_key="link_latency", default_value="1")
        self.addPowerParam(power_key="input_ports", m5_key="input_ports", default_value="4")
        self.addPowerParam(power_key="output_ports", m5_key="output_ports", default_value="4")
        self.addPowerParam(power_key="virtual_channel_per_port", m5_key="vcs_per_vnet", default_value="4") #FIXME: what is this?
        self.addPowerParam(power_key="flit_bits", m5_key="ni_flit_size", default_value="16") #FIXME: what is this?
        self.addPowerParam(power_key="input_buffer_entries_per_vc", m5_key="buffers_per_data_vc", default_value="4")#FIXME
        self.addPowerParam(power_key="chip_coverage", m5_key="unknown", default_value="1")

        #statistics
        self.addPowerStat(power_key="total_accesses", m5_key="total_flits_injected", default_value="0")
        self.addPowerStat(power_key="duty_cycle", m5_key="unknown", default_value="0.1")
        

class BusConn(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="1400")
        self.addPowerParam(power_key="type", m5_key="unknown", default_value="0")
        self.addPowerParam(power_key="vertical_nodes", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="has_global_link", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="link_throughput", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="link_latency", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="input_ports", m5_key="input_ports", default_value="9")
        self.addPowerParam(power_key="output_ports", m5_key="output_ports", default_value="8")
        self.addPowerParam(power_key="virtual_channel_per_port", m5_key="unknown", default_value="2") #FIXME: what is this?
        self.addPowerParam(power_key="flit_bits", m5_key="unknown", default_value="40") #FIXME: what is this?
        self.addPowerParam(power_key="input_buffer_entries_per_vc", m5_key="unknown", default_value="128")#FIXME
        self.addPowerParam(power_key="chip_coverage", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="link_routing_over_percentage", m5_key="unknown", default_value="1.0")

        #statistics
        self.addPowerStat(power_key="total_accesses", m5_key="total_packets_received", default_value="0")
        self.addPowerStat(power_key="duty_cycle", m5_key="unknown", default_value="1")

class Bus(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="1400")
        self.addPowerParam(power_key="type", m5_key="unknown", default_value="0") # 0 for BUS
        self.addPowerParam(power_key="horizontal_nodes", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="vertical_nodes", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="has_global_link", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="link_throughput", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="link_latency", m5_key="unknown", default_value="1")
        self.addPowerParam(power_key="input_ports", m5_key="input_ports", default_value="0")
        self.addPowerParam(power_key="output_ports", m5_key="output_ports", default_value="0")
        self.addPowerParam(power_key="virtual_channel_per_port", m5_key="unknown", default_value="2") #FIXME: what is this?
        self.addPowerParam(power_key="input_buffer_entries_per_vc", m5_key="unknown", default_value="128")#FIXME
        self.addPowerParam(power_key="flit_bits", m5_key="unknown", default_value="40") #FIXME: what is this?
        self.addPowerParam(power_key="chip_coverage", m5_key="unknown", default_value="1") #really should be a function of the number of nocs
        self.addPowerParam(power_key="link_routing_over_percentage", m5_key="unknown", default_value="0.5")
        #statistics
        self.addPowerStat(power_key="total_accesses", m5_key="total_packets_received", default_value="0")
        self.addPowerStat(power_key="duty_cycle", m5_key="unknown", default_value="1")

class Crossbar(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="clock", m5_key="clock")
        self.addPowerParam(power_key="port", m5_key="port")
        self.addPowerParam(power_key="type", m5_key="type")
        self.addPowerParam(power_key="bandwidth", m5_key="bandwidth_Mbps")
        #statistics
        self.addPowerStat(power_key="accesses", m5_key="accesses")

class Predictor(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="local_predictor_size", m5_key="unknown", default_value="10,3")
        self.addPowerParam(power_key="local_predictor_entries", m5_key="unkown", default_value="1024")
        self.addPowerParam(power_key="global_predictor_entries", m5_key="unknown", default_value="4096")
        self.addPowerParam(power_key="global_predictor_bits", m5_key="unknown", default_value="2")
        self.addPowerParam(power_key="chooser_predictor_entries", m5_key="unknown", default_value="4096")
        self.addPowerParam(power_key="chooser_predictor_bits", m5_key="unknown", default_value="2")        
        #self.addPowerParam(power_key="prediction_width", m5_key="unknown", default_value="2")    
        #statistics

class System(Translator):
    def __init__(self):
        Translator.__init__(self)
        global options
        #params
        self.addPowerParam(power_key="number_of_cores", m5_key="number_of_cores", default_value="NaV")
        self.addPowerParam(power_key="number_of_L1Directories", m5_key="number_of_L1Directories", default_value="NaV")
        self.addPowerParam(power_key="number_of_L2Directories", m5_key="number_of_L2Directories", default_value="NaV") #Shadow L4 with 0 latency back memory is our L2 directory
        self.addPowerParam(power_key="number_of_L2s", m5_key="number_of_L2s", default_value="NaV")
        self.addPowerParam(power_key="number_of_L3s", m5_key="number_of_L3s", default_value="NaV")
        self.addPowerParam(power_key="number_of_NoCs", m5_key="number_of_nocs", default_value="NaV")
        self.addPowerParam(power_key="homogeneous_cores", m5_key="homogeneous_cores", default_value="0")
        self.addPowerParam(power_key="homogeneous_L2s", m5_key="homogeneous_L2s", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="homogeneous_L1Directories", m5_key="homogeneous_L1Directories", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="homogeneous_L2Directories", m5_key="homogeneous_L2Directories", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="homogeneous_L3s", m5_key="homogeneous_L3s", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="homogeneous_ccs", m5_key="unknown", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="homogeneous_NoCs", m5_key="homogeneous_nocs", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="core_tech_node", m5_key="unknown", default_value=options.core_tech_node) #TODO: set your value
        if options.sys_vdd_scale != None:
            self.addPowerParam(power_key="sys_vdd_scale", m5_key="unknown", default_value=options.sys_vdd_scale) #TODO: set your value
        if options.tech_node=="32":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000') #2GHz; TODO: set your value
        elif options.tech_node=="22":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000')
        elif options.tech_node=="16":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000')
        elif options.tech_node=="45":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000')
        elif options.tech_node=="65":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000')
        elif options.tech_node=="90":
            self.addPowerParam(power_key="target_core_clockrate", m5_key="unknown", default_value='2000')
        self.addPowerParam(power_key="temperature", m5_key="unknown", default_value="350") #TODO: set your value
        self.addPowerParam(power_key="number_cache_levels", m5_key="number_cache_levels", default_value="NaV")
        self.addPowerParam(power_key="interconnect_projection_type", m5_key="unknown", default_value=options.interconnect_projection_type) #TODO: set your value
        self.addPowerParam(power_key="device_type", m5_key="unknown", default_value=options.core_device_type) #TODO: set your value
        self.addPowerParam(power_key="longer_channel_device", m5_key="unknown", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="machine_bits", m5_key="unknown", default_value="64") #TODO: set your value
        self.addPowerParam(power_key="virtual_address_width", m5_key="unknown", default_value="64") #TODO: set your value
        self.addPowerParam(power_key="physical_address_width", m5_key="unknown", default_value="52") #TODO: set your value
        self.addPowerParam(power_key="virtual_memory_page_size", m5_key="unknown", default_value="4096") #TODO: set your value
        self.addPowerParam(power_key="number_of_dir_levels", m5_key="number_of_dir_levels", default_value="0") #TODO: set your value
        #self.addPowerParam(power_key="first_level_dir", m5_key="first_level_dir", default_value="NaV") #REMOVED: ask Sheng what this stat is all about
        #self.addPowerParam(power_key="domain_size", m5_key="unknown", default_value="NaV") #REMOVED: ask Sheng about domain size
        self.addPowerStat(power_key="total_cycles", m5_key="total_cycles", default_value="0") #FIXME: ask Sheng about domain size
        self.addPowerStat(power_key="idle_cycles", m5_key="unknown", default_value="0") #FIXME: ask Sheng about domain size
        self.addPowerStat(power_key="busy_cycles", m5_key="total_cycles", default_value="0") #FIXME: ask Sheng about domain size

# cris: I made read_accesses and write_accesses as statistics; they were params       
class BTB(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="BTB_config", m5_key="BTB_config", default_value="6144,4,2,1,1,3")
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="0")
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="0")

class L1Directory(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="Directory_type", m5_key="unknown", default_value="1") #TODO: specify your value
        self.addPowerParam(power_key="Dir_config", m5_key="Dir_config", default_value="65536,2,0,1,3,3, 8") 
        self.addPowerParam(power_key="buffer_sizes", m5_key="buffer_sizes", default_value="8,8,8,8") #TODO: specify your value
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="1400") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerParam(power_key="ports", m5_key="unknown", default_value="1,1,1") #TODO: specify your value
        self.addPowerParam(power_key="device_type", m5_key="unknown", default_value=options.cache_device_type) #TODO: specify your value
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="1024") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="1024") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerStat(power_key="read_misses", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache
        self.addPowerStat(power_key="write_misses", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache
        self.addPowerStat(power_key="conflicts", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache

class L2Directory(Translator):
    def __init__(self):
        Translator.__init__(self)
        #params
        self.addPowerParam(power_key="Directory_type", m5_key="unknown", default_value="1") #TODO: specify your value
        self.addPowerParam(power_key="Dir_config", m5_key="Dir_config", default_value="65536,2,0,1,3,3, 8") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerParam(power_key="buffer_sizes", m5_key="unknown", default_value="8,8,8,8") #TODO: specify your value
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="1400") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerParam(power_key="ports", m5_key="unknown", default_value="1,1,1") #TODO: specify your value
        self.addPowerParam(power_key="device_type", m5_key="unknown", default_value=options.cache_device_type) #TODO: specify your value
        #statistics
        self.addPowerStat(power_key="read_accesses", m5_key="read_accesses", default_value="1024") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerStat(power_key="write_accesses", m5_key="write_accesses", default_value="1024") #FIXME: make sure it gets the right value from ruby.stats
        self.addPowerStat(power_key="read_misses", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache
        self.addPowerStat(power_key="write_misses", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache
        self.addPowerStat(power_key="conflicts", m5_key="unknown", default_value="0") #FIXME: Add this stat to M5. My model does not treat directory as a cache

class PhysicalMemory(Translator):
    def __init__(self):
        Translator.__init__(self)
        global options
        #params        
        self.addPowerParam(power_key="mem_tech_node", m5_key="unknown", default_value=options.mem_tech_node) #TODO: Set your value
        self.addPowerParam(power_key="device_clock", m5_key="unknown", default_value="200") #TODO: Set your value
        self.addPowerParam(power_key="peak_transfer_rate", m5_key="unknown", default_value="6400") #TODO: set your value
        self.addPowerParam(power_key="internal_prefetch_of_DRAM_chip", m5_key="unknown", default_value="4") #FIXME: add this param to M5
        self.addPowerParam(power_key="capacity_per_channel", m5_key="unknown", default_value="4096") #TODO: set your value
        self.addPowerParam(power_key="number_ranks", m5_key="unknown", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="num_banks_of_DRAM_chip", m5_key="unknown", default_value="8") #TODO: set your value
        self.addPowerParam(power_key="Block_width_of_DRAM_chip", m5_key="unknown", default_value="64") #TODO: set your value
        self.addPowerParam(power_key="output_width_of_DRAM_chip", m5_key="unknown", default_value="8") #TODO: set your value
        self.addPowerParam(power_key="page_size_of_DRAM_chip", m5_key="unknown", default_value="8") #TODO: set your value
        self.addPowerParam(power_key="burstlength_of_DRAM_chip", m5_key="unknown", default_value="8") #TODO: set your value
        #statistcs
        self.addPowerStat(power_key="memory_accesses", m5_key="num_phys_mem_accesses", default_value="0")
        self.addPowerStat(power_key="memory_reads", m5_key="num_phys_mem_reads", default_value="0")
        self.addPowerStat(power_key="memory_writes", m5_key="num_phys_mem_writes", default_value="0")

#Memory Controller
class MC(Translator):
    def __init__(self):
        Translator.__init__(self)
        self.addPowerParam(power_key="mc_clock", m5_key="mc_clock", default_value="800") #TODO: set your value
        self.addPowerParam(power_key="peak_transfer_rate", m5_key="1600", default_value="1600") #TODO: set your value
        self.addPowerParam(power_key="llc_line_length", m5_key="unknown", default_value="16") #TODO: set your value
        self.addPowerParam(power_key="number_mcs", m5_key="unknown", default_value="1") #TODO: set this value
        self.addPowerParam(power_key="memory_channels_per_mc", m5_key="unknown", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="number_ranks", m5_key="unknown", default_value="2") #TODO: set your value
        self.addPowerParam(power_key="req_window_size_per_channel", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="IO_buffer_size_per_channel", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="databus_width", m5_key="unknown", default_value="32") #TODO: set your value
        self.addPowerParam(power_key="addressbus_width", m5_key="unknown", default_value="32") #TODO: set your value
        #statistcs
        self.addPowerStat(power_key="memory_accesses", m5_key="num_phys_mem_accesses", default_value="0")
        self.addPowerStat(power_key="memory_reads", m5_key="num_phys_mem_reads", default_value="0")
        self.addPowerStat(power_key="memory_writes", m5_key="num_phys_mem_writes", default_value="0")

# cris: I added these three as they seem to be required by McPAT
class NIU(Translator):
    def __init__(self):
        Translator.__init__(self)
        self.addPowerParam(power_key="type", m5_key="type", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="350") #TODO: set your value
        self.addPowerParam(power_key="number_units", m5_key="number_units", default_value="2") #TODO: set your value
        #statistcs
        self.addPowerStat(power_key="duty_cycle", m5_key="duty_cycle", default_value="1.0")
        self.addPowerStat(power_key="total_load_perc", m5_key="total_load_perc", default_value="0.7")

class PCIE(Translator):
    def __init__(self):
        Translator.__init__(self)
        self.addPowerParam(power_key="type", m5_key="type", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="withPHY", m5_key="withPHY", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="clockrate", m5_key="clockrate", default_value="350") #TODO: set your value
        self.addPowerParam(power_key="number_units", m5_key="number_units", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="number_channels", m5_key="number_channels", default_value="8") #TODO: set your value
        #statistcs
        self.addPowerStat(power_key="duty_cycle", m5_key="duty_cycle", default_value="1.0")
        self.addPowerStat(power_key="total_load_perc", m5_key="total_load_perc", default_value="0.7")

class FLASHC(Translator):
    def __init__(self):
        Translator.__init__(self)
        self.addPowerParam(power_key="number_flashcs", m5_key="number_flashcs", default_value="0") #TODO: set your value
        self.addPowerParam(power_key="type", m5_key="type", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="withPHY", m5_key="withPHY", default_value="1") #TODO: set your value
        self.addPowerParam(power_key="peak_transfer_rate", m5_key="peak_transfer_rate", default_value="200") #TODO: set your value
        #statistcs
        self.addPowerStat(power_key="duty_cycle", m5_key="duty_cycle", default_value="1.0")
        self.addPowerStat(power_key="total_load_perc", m5_key="total_load_perc", default_value="0.7")


'''
setComponentTranslator takes as input a component object, and assigns
the translator field to the right type of Translator object. Translator
objects are responsible for grabbing the right stats and naming them
correctly
'''
def setComponentTranslator(component):
    global options
    if 'core' in component.id:
	print '28: %s' % component.id 
    for pair in options.interconn_names.split('#'):
        name, util = pair.split(',')
        if name in component.name:
            if component.params['type'] == "Bus":
                component.translator = Bus()
            elif component.params['type'] == "BusConn":
                component.translator = BusConn()
            elif component.params['type'] == "GarnetNetwork_d":
                component.translator = Mesh()
            elif component.params['type'] == "Crossbar":
                component.translator = Crossbar()
            return
    if options.cpu_name in component.name:
        if component.params['type'] == "TimingSimpleCPU":
            component.translator = InOrderCore()
        if component.params['type'] == "AtomicSimpleCPU":
            component.translator = InOrderCore()
        if component.params['type'] == "DerivO3CPU":
            component.translator = OOOCore()
    elif options.itb_name in component.name:
        component.translator = ITLB()
    elif options.dtb_name in component.name:
        component.translator = DTLB()
    # NOTE: I must use L1IcacheMemory and not icache because
    # icache is actually the re_name and not the name...
    elif "L1IcacheMemory" in component.name:
        if component.params['type'] == "RubyCache":
#	    print '27: building InstructionCache() '	    
            component.translator = InstructionCache()
    elif "L1DcacheMemory" in component.name:
        if component.params['type'] == "RubyCache":
#	    print '28: building DataCache() '
            component.translator = DataCache()
    elif "L2cacheMemory" in component.name:
        if component.params['type'] == "RubyCache":
            component.translator = SharedCacheL2()
    elif "L1Directory" in component.name:
        component.translator = L1Directory()
    elif "PBT" in component.name:
        component.translator = Predictor()
    elif "BTB" in component.name:
        component.translator = BTB()
    elif "physmem" in component.name:
        component.translator = PhysicalMemory()
    elif "mc" in component.name:
        component.translator = MC()
    elif "niu" in component.name:
        component.translator = NIU()
    elif "pcie" in component.name:
        component.translator = PCIE()
    elif "flashc" in component.name:
        component.translator = FLASHC()
    elif options.system_name == component.name:
        component.translator = System()
    else:
        return


'''
find the voltage scaling for a frequency scaling for data:
from Gaurav Dhiman's Hotpower paper
DFS             FREQ    VOLT    PERC_VOLT
1               2600    1.25    1
0.730769231     1900    1.15    0.92
0.538461538     1400    1.05    0.84
0.307692308     800     0.9     0.72
dvs = 0.4032*dfs + 0.6102
'''
def dfsToDvs(dfs):
    dvs = 0.4032*dfs + 0.6102
    return dvs
    

'''
run() is repsonsible for going through all the directories
that have results, creating paths to all important files,
and calling parseSystemConfig that handles the power.xml 
creation.
'''        
def run():
    global options
    filter = ""
    if options.process_run_dirs_by_filter != None:
        dirs = os.listdir('.')       
#milad_guide
#Return a list containing the names of the entries in the directory 					      #given by path. The list is in arbitrary order. It does not include 					      #the special entries '.' and '..' even if they are present in the 					#directory.
        filter = options.process_run_dirs_by_filter
    else:
        dirs = '.'
        
    for dir in dirs:
        if filter not in dir:
            continue
            
        # TODO: cris, here more work is needed to set things up
        # so that dvs/dfs is done on a per core basis when we work with CMP; 
        if options.do_vdd_scaling and "1core:dfs" in dir:
  #          match = re.match("run.*:1core:dfs([0-9]+)",dir)
  #          assert(match)
  #          dfs = int(match.group(1))/100.0
  #          dvs = dfsToDvs(dfs)
  #          options.sys_vdd_scale = str(dvs)
             print "If"
#        else:
  #          options.sys_vdd_scale = None
#             print "Else"
        component_hash = {}
        stats_hash = {}
        if options.verbose:
            print "processing:%s" %(dir)
        output_dir=options.output_dir # default is "m5out"
        if not os.path.exists(os.path.join(dir,output_dir)):
          output_dir=""
        
        config_file_path = os.path.join(dir, output_dir,options.config_fn)
        stat_file_path = os.path.join(dir, output_dir, options.stats_fn)
        # ruby.stats file grabbed here
        ruby_file_path = os.path.join(dir, output_dir, options.ruby_fn) 
        out_file_path = os.path.join(dir, output_dir, options.summary_fn)
        out_file_path_2 = os.path.join(dir, output_dir, options.power_fn)
        if not os.path.exists(config_file_path):
            warning("config file does not exist:%s" % (config_file_path))
        if not os.path.exists(stat_file_path):
            warning("stat path does not exist:%s" % (stat_file_path))
        if not os.path.exists(ruby_file_path):
            warning("Ruby stats file does not exist: %s! This is OK if you are not using Ruby" % (ruby_file_path))
        parseSystemConfig(ruby_file_path, config_file_path, stat_file_path, out_file_path, out_file_path_2, component_hash, stats_hash)

'''
genId will take a list of system components and concat 
them to make a specific component of stat identifier.
'''
def genId(id_list):
    res=''
    for id in id_list:
        res += '%s.' %(id)
    
    res = res.rstrip('.')
    return res

def tryGrabComponentStat(component, stat, conversion="int"):
    try:
        value=str(component.statistics[stat])
    except:
        value="0"
    
    if conversion=="int":
        value=int(value)
    else:
        panic("unable to perform conversion", 8)
    return value
        
'''
generateCalcStats is a function used to: 
(1) add statistics that are composed from several other statistics and params that
can be seen by the translator objects in the next phase. 
(2) rename newly generated components to meet the McPat specifications
(3) move children components to a new parent component to meet the right xml form
This code is the least generic and will likely needed to be changed by new users. 
If there is a bug, it probably is in this function ... X_X
'''
def generateCalcStats(cht, sht):
    global options
    num_cores=0
    num_l1s=0
    num_l2s=0
    num_l3s=0
    num_nocs=0
    clock_rate=1400
    o3_cpu_exists=False
    timing_cpu_exists=False
    homogeneous_cores="0"
    homogeneous_L2s="0"
    homogeneous_L3s="0"
    homogeneous_L1s="0"
    homogeneous_L2Directories="0"
    homogeneous_L1Directories="0"
    homogeneous_nocs="0"
    num_cache_levels=0
    new_components_to_add=[]
    components_to_remove=[]
    fastest_clock=1000000000000

   #milad debug, defining num_l1directories variable
    num_l1directories=0 
   #milad_debug calculating total_num_cores
    total_num_cores=0
    for c_key in cht:
	component = cht[c_key]
	params = component.params
        ptype = params['type']
        component_name = component.name
	if (options.cpu_name in component_name) and \
            (ptype == "TimingSimpleCPU" or ptype == "AtomicSimpleCPU"):
		total_num_cores += 1
#    print '52 = total_num_cores = %s' % total_num_cores
   # part (1): everything but the network(s);
   
    for c_key in cht:
        # grab generic component info
        component = cht[c_key]
        if not component.params.has_key('type'):
            continue # skip components witout a type;
        params = component.params
        ptype = params['type']
        component_name = component.name

        
        if ("server" in c_key and options.system_name != "server") or \
            ("client" in c_key and options.system_name != "client"):
            component.power_xml_filter=True
 
        # add subcomponents to different major components. 
        if ptype == 'AlphaTLB':
            # example:
            # [system.cpu1.dtb]
            # type=AlphaTLB
            # size=48
            data_hits = tryGrabComponentStat(component, "data_hits", conversion="int") 
            data_misses= tryGrabComponentStat(component, "data_misses", conversion="int") 
            fetch_hits= tryGrabComponentStat(component, "fetch_hits", conversion="int") 
            fetch_misses=tryGrabComponentStat(component, "fetch_misses", conversion="int") 
            write_hits=tryGrabComponentStat(component, "write_hits", conversion="int") 
            write_misses=tryGrabComponentStat(component, "write_misses", conversion="int") 
            read_hits=tryGrabComponentStat(component, "read_hits", conversion="int")
            read_misses=tryGrabComponentStat(component, "read_misses", conversion="int")  
            component.statistics["total_accesses"] = str(data_hits+ data_misses + fetch_hits + fetch_misses)
            component.statistics["write_accesses"] = str(write_hits+write_misses)
            component.statistics["read_accesses"] = str(read_hits+read_misses)
                
        if ptype == 'Bus' or ptype == "BusConn":
            # example:
            #[system.piobus]
            #type=Bus
            #port=system.physmem.port[0] system.tsunami.cchip.pio system.tsunami.pchip.pio 
            #     system.tsunami.fake_sm_chip.pio system.tsunami.fake_uart1.pio 
            #     system.tsunami.fake_uart2.pio system.tsunami.fake_uart3.pio 
            #     system.tsunami.fake_uart4.pio system.tsunami.fake_ppc.pio 
            #     system.tsunami.fake_OROM.pio system.tsunami.fake_pnp_addr.pio 
            #     system.tsunami.fake_pnp_write.pio system.tsunami.fake_pnp_read0.pio 
            #     system.tsunami.fake_pnp_read1.pio system.tsunami.fake_pnp_read2.pio system.tsunami.fake_pnp_read3.pio 
            #     system.tsunami.fake_pnp_read4.pio system.tsunami.fake_pnp_read5.pio system.tsunami.fake_pnp_read6.pio 
            #     system.tsunami.fake_pnp_read7.pio system.tsunami.fake_ata0.pio system.tsunami.fake_ata1.pio 
            #     system.tsunami.fb.pio system.tsunami.io.pio system.tsunami.uart.pio system.tsunami.backdoor.pio 
            #     system.tsunami.ide.pio system.tsunami.ethernet.pio system.l1_cntrl0.sequencer.pio_port 
            #     system.l1_cntrl1.sequencer.pio_port system.l1_cntrl2.sequencer.pio_port system.l1_cntrl3.sequencer.pio_port
            #     system.tsunami.ethernet.config system.tsunami.ide.config
            num_ports=len(component.params['port'].split())
            for pair in options.interconn_names.split('#'):
                name, util = pair.split(',')
                if name in component.name:
                    component.re_name = component.name.replace(name, "noc%s"%num_nocs)
                    component.re_id = component.id.replace(name, "NoC%s"%num_nocs)
                    num_nocs = str(int(num_nocs)+1)
                    break
            # calculate clock frequency (why do they call it rate?) under the
            # assumption that the clock period "clock" is given in picoseconds
            # in the output files from gem5; 
            # so, f=[1/T]*10^6 in MHz if T is given in picoseconds;
            # example clock = 500 ps => clockrate = 2000MHz = 2GHz
            cpu_clock_rate = int(1/(float(params['clock'])*1e-2)) #f=1/T
            component.params["clockrate"] = str(cpu_clock_rate)
            component.params["input_ports"] = str(num_ports)
            component.params["output_ports"] = str(num_ports)
            bus_name = component_name
            ports = params['port'].split()
            for port in ports:
                #remove port name to find component this bus is attached to
                temp = port.split('.')
                comp_id = genId(temp[0:len(temp)-1])
                if not cht.has_key(comp_id):
                    panic("unable to find component: %s" % (comp_id), 1)
                # add the bus width to the component to make 
                # it easier for the power model
                cht[comp_id].params[bus_name + ".width"] = params['width']

   	
        # how many cores are there
        if (options.cpu_name in component_name) and \
            (ptype == "TimingSimpleCPU" or ptype == "AtomicSimpleCPU"):
            # example:
            # [system.cpu0] <--- component name is "cpu0" here
            # type=TimingSimpleCPU
            # children=dtb interrupts itb tracer
            # checker=Null
            # clock=500
            # cpu_id=0
            # ...
                        
            print_debug_message("Component Name: " + component.name
                                + "\ncht key: " + c_key)
            
            #clock=int(component.params['clock'])
            
            if("clock" in component.params.keys()):
                clock=int(component.params['clock'])
            else:
                clock=int(cht[component.params['clk_domain']].params['clock'])
            
            if fastest_clock == None or fastest_clock > clock:
                fastest_clock=clock
            num_cores += 1
            if num_cores > 1:
                homogeneous_cores="0"
                #if("clock" in component.params.keys()):
                #    cpu_clock_rate=int(1/(float(component.params['clock'])*1e-6)) #f=1/T
                #else:
                #    cpu_clock_rate=int(1/(float(cht[cht[c_key].params['clk_domain']].params['clock'] )*1e-6)) #f=1/T

            #cpu_clock_rate=int(1/(float(component.params['clock'])*1e-6)) #f=1/T
            cpu_clock_rate=calculateComponentClockRate(cht,c_key)
            
            if ptype == "TimingSimpleCPU":
                timing_cpu_exists=True
            component.params["clockrate"] = str(cpu_clock_rate)
#milad : add component for detailed cpu
        if (options.cpu_name in component_name) and (ptype == "DerivO3CPU"):
            # example:
            # [system.cpu0] <--- component name is "cpu0" here
            # type=TimingSimpleCPU
            # children=dtb interrupts itb tracer
            # checker=Null
            # clock=500
            # cpu_id=0
            # ...
                        
            print_debug_message("Component Name: " + component.name
                                + "\ncht key: " + c_key)
            
            #clock=int(component.params['clock'])
            
            if("clock" in component.params.keys()):
                clock=int(component.params['clock'])
            else:
                clock=int(cht[component.params['clk_domain']].params['clock'])
            
            if fastest_clock == None or fastest_clock > clock:
                fastest_clock=clock
            num_cores += 1
            if num_cores > 1:
                homogeneous_cores="0"
                #if("clock" in component.params.keys()):
                #    cpu_clock_rate=int(1/(float(component.params['clock'])*1e-6)) #f=1/T
                #else:
                #    cpu_clock_rate=int(1/(float(cht[cht[c_key].params['clk_domain']].params['clock'] )*1e-6)) #f=1/T

            #cpu_clock_rate=int(1/(float(component.params['clock'])*1e-6)) #f=1/T
            cpu_clock_rate=calculateComponentClockRate(cht,c_key)
            
#            if ptype == "TimingSimpleCPU":
#                timing_cpu_exists=True
            component.params["clockrate"] = str(cpu_clock_rate)
               
        if ptype == "RubyCache":
            # example from config.ini:
            # [system.l1_cntrl0.L1DcacheMemory]
            # type=RubyCache
            # assoc=2
            # is_icache=false
            # latency=3
            # replacement_policy=PSEUDO_LRU
            # size=65536
            # start_index_bit=6
            try:
                banked = component.params["banked"]
                num_banks = component.params["numBanks"]
            except:
                banked = "false"
                num_banks=1
            size = component.params["size"]
            # block_size is used as line size inside McPAT?
	    #milad debug , adding block size from config.ini
            block_size = cht['system.ruby'].params['block_size_bytes'] #milad debug       64 #FIXME component.params["block_size"] 
#           #milad debug defining cache_block_size variable
#	    cache_block_size=component.params["block_size"]
            assoc = component.params["assoc"]
            # Miss Status/Information Holding Register count:
            num_mshrs=64 # int(float(size)/float(block_size)) FIXME
            component.params["buffer_sizes"]= "%d,%d,%d,%d" %(num_mshrs,num_mshrs,num_mshrs,num_mshrs)
            if banked == "false":
                banked="0"
                num_banks="1"
            else:
                banked="1"
            
            if "Icache" in component_name or "Dcache" in component_name:
		#milad debug 		
#		print"Icash or Dcache are in component_name= %s"%component.id                
		temp = component.id.split('.')
                core_component = temp[0]+'.'+temp[1]
                latency_wrt_core = int(component.params["latency"]) #FIXME str(int(math.ceil(float(component.params["latency"])/float(cht[core_component].params["clock"]))))
                component.params["is_icache"] = \
                    "%s,%s,%s,%s,%s,%s" %(size,block_size,assoc,num_banks,"1",latency_wrt_core) #TODO: set throughput w.r.t core clock

            if "Icache" in component_name:
                try: # for now: include all statistics from "ruby.stats" file:
                    component.statistics["read_accesses"] = \
                        str(int(component.statistics["Ifetch"]))
                except:
                    component.statistics["read_accesses"] = "0"

            if "Dcache" in component_name:
				Own_GETX = tryGrabComponentStat(component, "Own_GETX", conversion="int") 
				Fwd_GETX = tryGrabComponentStat(component, "Fwd_GETX", conversion="int") 
				Fwd_GETS = tryGrabComponentStat(component, "Fwd_GETS", conversion="int") 
				Fwd_DMA = tryGrabComponentStat(component, "Fwd_DMA", conversion="int") 
				Ack = tryGrabComponentStat(component, "Ack", conversion="int") 
				Data = tryGrabComponentStat(component, "Data", conversion="int") 
				Exclusive_Data = tryGrabComponentStat(component, "Exclusive_Data", conversion="int") 
				All_acks = tryGrabComponentStat(component, "All_acks", conversion="int") 
				Use_Timeout = tryGrabComponentStat(component, "Use_Timeout", conversion="int") 
				write_accesses = tryGrabComponentStat(component, "write_accesses", conversion="int") 
				Load = tryGrabComponentStat(component, "Load", conversion="int") 
				Store = tryGrabComponentStat(component, "Store", conversion="int") 
				Inv = tryGrabComponentStat(component, "Inv", conversion="int") 
				Writeback_Ack = tryGrabComponentStat(component, "Writeback_Ack", conversion="int") 
				Writeback_Ack_Data = tryGrabComponentStat(component, "Writeback_Ack_Data", conversion="int") 
				Writeback_Nack = tryGrabComponentStat(component, "Writeback_Nack", conversion="int") 
				L1_Replacement = tryGrabComponentStat(component, "L1_Replacement", conversion="int") 

				component.statistics["read_accesses"]=str(Own_GETX+Fwd_GETX+Fwd_GETS+Fwd_DMA+Ack+Data+Exclusive_Data+All_acks+Use_Timeout)
				component.statistics["write_accesses"]=str(Load+Store+Inv+Writeback_Ack+Writeback_Ack_Data+Writeback_Nack)
				component.statistics["replacements"]=str(L1_Replacement)

				#print "\n\n\n 1:%s   2:%s   3:%s   \n\n"%(component.statistics["read_accesses"],component.statistics["write_accesses"],component.statistics["replacements"])

				
#milad debug change the name from "ruby.L2cache" to "L2CacheMemroy" 
            if ("ruby.L2cache" in component_name):
#	    if ("L2cacheMemory" in component_name):
#		print "18: milad debug YES L2 in component name"
#		print 'comp= %s' % component_name
#                component.name = component.name.replace('ruby.L2cache', "L2cache")
 #               component.id = component.id.replace('ruby.L2cache', "L2.cache")
		
		
                # example from config.ini:
                # [system.l2_cntrl0.L2cacheMemory]
                # type=RubyCache
                # assoc=8
                # is_icache=false
                # latency=15
                # replacement_policy=PSEUDO_LRU
                # size=2097152
                # start_index_bit=8

		#milad debug , defining l2_size variable
		#milad_debug new dir_block_size calculation
                #dir_block_size="16"  #FIXME block_size of 64 causes problems for L1Directory so I hardcoded 16 
		l2_size = component.params["size"]
		dir_block_size=total_num_cores + 3 # 3 bit as dirty and states and num_cores bit to locate
		if (dir_block_size%8) != 0 :
			dir_block_size=(dir_block_size/8 + 1)*8					
#		print '50: dir_block_size=%s    total_num_cores= %s' %(dir_block_size,total_num_cores)
                dir_size = str(int(float(l2_size)/float(block_size)))
                latency_wrt_core = int(component.params["latency"]) #FIXME str(int(math.ceil(float(component.params["latency"])/float(cht[core_component].params["clock"]))))

                dir_number_banks="1" #bank_size not equal to 1 causes problems for the L1DIrectory. 
                component.params["Dir_config"] = "%s,%s,%s,%s,%s,%s" %(dir_size,dir_block_size,assoc,dir_number_banks,"1",latency_wrt_core)#TODO: set throughput w.r.t core clock,		
		#milad debug, defining l1_dir_config variable
		l1_dir_config={}
		l1_dir_config =  "%s,%s,%s,%s,%s,%s" %(dir_size,dir_block_size,assoc,dir_number_banks,"1",latency_wrt_core)
                # I assume that the clock frequency L2 cache is being run at
                # is the same as of the associated/corresponding core itself;
                # NOTE: that at this stage cores are id'ed in the "cht" array by
                # their initial ids as found in gem5 files; so, below I must
                # use options.cpu_name and not "core"
                # NOTE: I also assume that by this time the cores have been processed and
                # so their clock values have been retrieved;
                core_id = component.id
                print_debug_message("Replaceing L2 Cache in core_id: " + core_id)
                
                #substituteSystemCPU(core
                if 'l2cacheMemory' in component.id:
			print '.............................................fsfsfsdf..........................'
                if("ruby" in component.id) or ("L2cacheMemory" in component.id):
#		    print "19: milad debug YES ruby + L2 in component name = %s" % component.id
                    core_id = core_id.replace("ruby.L2cache",options.cpu_name) # system.cpu0
                    #cpu_clock_rate=int(1/(float( cht[cht[core_id].params['clk_domain']].params['clock'] )*1e-6)) #f=1/T
                else:
                    core_id = core_id.replace("L2cacheMemory",options.cpu_name) # system.cpu0
                    #cpu_clock_rate=int(1/(float( cht[core_id].params['clock'] )*1e-6)) #f=1/T
                
                cpu_clock_rate=calculateComponentClockRate(cht,core_id)
                                    
                print_debug_message("Replaced L2 Cache in core_id, new id: " + core_id)
                
                print_debug_message("L2 in component name: " + component_name
                                    + "\n\nCPU NAME: " + options.cpu_name
                                    + "\nCOMPONENT ID: " + str(component.id)
                                    + "\nSYSTEM NAME: " + options.system_name)

                component.params["clockrate"] = str(cpu_clock_rate)
                component.params["is_icache"] = "%s,%s,%s,%s,%s,%s" \
                    %(size,block_size,assoc,num_banks,"1",latency_wrt_core) #TODO: set throughput w.r.t core clock


                L1_GETS = tryGrabComponentStat(component, "L1_GETS", conversion="int")
                L1_GETX = tryGrabComponentStat(component, "L1_GETX", conversion="int") 
                Fwd_GETX = tryGrabComponentStat(component, "Fwd_GETX", conversion="int") 
                Fwd_GETS = tryGrabComponentStat(component, "Fwd_GETS", conversion="int") 
                Fwd_DMA = tryGrabComponentStat(component, "Fwd_DMA", conversion="int") 
                Own_GETX = tryGrabComponentStat(component, "Own_GETX", conversion="int") 
                Inv = tryGrabComponentStat(component, "Inv", conversion="int") 
                IntAck = tryGrabComponentStat(component, "IntAck", conversion="int") 
                ExtAck = tryGrabComponentStat(component, "ExtAck", conversion="int") 
                All_Acks = tryGrabComponentStat(component, "All_Acks", conversion="int") 
                Data = tryGrabComponentStat(component, "Data", conversion="int") 
                Data_Exclusive = tryGrabComponentStat(component, "Data_Exclusive", conversion="int") 
                L1_WBCLEANDATA = tryGrabComponentStat(component, "L1_WBCLEANDATA", conversion="int") 
                L1_WBDIRTYDATA = tryGrabComponentStat(component, "L1_WBDIRTYDATA", conversion="int") 
                Unblock = tryGrabComponentStat(component, "Unblock", conversion="int") 
                Exclusive_Unblock = tryGrabComponentStat(component, "Exclusive_Unblock", conversion="int") 
                DmaAck = tryGrabComponentStat(component, "DmaAck", conversion="int") 
                L1_PUTO = tryGrabComponentStat(component, "L1_PUTO", conversion="int") 
                L1_PUTX = tryGrabComponentStat(component, "L1_PUTX", conversion="int") 
                L1_PUTS_only = tryGrabComponentStat(component, "L1_PUTS_only", conversion="int") 
                L1_PUTS = tryGrabComponentStat(component, "L1_PUTS", conversion="int") 
                Writeback_Ack = tryGrabComponentStat(component, "Writeback_Ack", conversion="int") 
                Writeback_Nack = tryGrabComponentStat(component, "Writeback_Nack", conversion="int") 
                L2_Replacement = tryGrabComponentStat(component, "L2_Replacement", conversion="int") 
                component.statistics["read_accesses"]=str(L1_GETS+L1_GETX+Fwd_GETX+Fwd_GETS+Fwd_DMA+Own_GETX+Inv+IntAck+ExtAck+All_Acks+Data+Data_Exclusive+L1_WBCLEANDATA+L1_WBDIRTYDATA+Unblock+Exclusive_Unblock+DmaAck)
                component.statistics["write_accesses"]=str(L1_PUTO+L1_PUTX+L1_PUTS_only+L1_PUTS+Writeback_Ack+Writeback_Nack)
                component.statistics["replacements"]=str(L2_Replacement)
                #print "\n 1:%s   2:%s   3:%s "%(component.statistics["read_accesses"],component.statistics["write_accesses"],component.statistics["replacements"])



  
                '''try: # for now: include all statistics from "ruby.stats" file:
#		    print'compute read_accesses....................................'
                    component.statistics["read_accesses"] = \
                        str(int(component.statistics["L1_GETS"]) + \
                            int(component.statistics["L1_GETX"]) + \
                 #in4c   #    int(component.statistics["Fwd_GETX"]) + \     # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["Fwd_GETS"]) + \     # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["Fwd_DMA"]) + \     # milad debug not available/
									 # in 16c blackscholes
                 #in4c   #    int(component.statistics["Own_GETX"]) + \    # milad debug not available/
									 # in 16c blackscholes
                 #in4c  #    int(component.statistics["Inv"]) + \    # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["IntAck"]) + \     # milad debug not available/
									 # in 16c blackscholes
                 #in4c  #    int(component.statistics["ExtAck"]) + \    # milad debug not available/
									 # in 16c blackscholes
                            int(component.statistics["All_Acks"]) + \
                            int(component.statistics["Data"]) + \
                            int(component.statistics["Data_Exclusive"]) + \
                            int(component.statistics["L1_WBCLEANDATA"]) + \
                            int(component.statistics["L1_WBDIRTYDATA"]) + \
                            int(component.statistics["Unblock"]) + \
                            int(component.statistics["Exclusive_Unblock"])  ) #+ \
                  #in4c  #    int(component.statistics["DmaAck"]))      # milad debug not available/
									 # in 16c blackscholes
                    component.statistics["write_accesses"] = \
                        str(int(component.statistics["L1_PUTO"]) + \
                            int(component.statistics["L1_PUTX"]) + \
                            int(component.statistics["L1_PUTS_only"]) + \
                            int(component.statistics["L1_PUTS"]) + \
                            int(component.statistics["Writeback_Ack"]) ) #+ \
                        #    int(component.statistics["Writeback_Nack"]))  # milad debug not available/
									 # in 16c blackscholes
                    component.statistics["replacements"] = \
                        str(int(component.statistics["L2_Replacement"]))
                except:
                    component.statistics["read_accesses"] = "0"
                    component.statistics["write_accesses"] = "0"
                    component.statistics["replacements"] = "0"

#		print'compute read_accesses....................%s'%component.statistics["read_accesses"]'''




#milad debug read_access

            if 'L2cacheMemory' in component.id:

                L1_GETS = tryGrabComponentStat(component, "L1_GETS", conversion="int")
                L1_GETX = tryGrabComponentStat(component, "L1_GETX", conversion="int") 
                Fwd_GETX = tryGrabComponentStat(component, "Fwd_GETX", conversion="int") 
                Fwd_GETS = tryGrabComponentStat(component, "Fwd_GETS", conversion="int") 
                Fwd_DMA = tryGrabComponentStat(component, "Fwd_DMA", conversion="int") 
                Own_GETX = tryGrabComponentStat(component, "Own_GETX", conversion="int") 
                Inv = tryGrabComponentStat(component, "Inv", conversion="int") 
                IntAck = tryGrabComponentStat(component, "IntAck", conversion="int") 
                ExtAck = tryGrabComponentStat(component, "ExtAck", conversion="int") 
                All_Acks = tryGrabComponentStat(component, "All_Acks", conversion="int") 
                Data = tryGrabComponentStat(component, "Data", conversion="int") 
                Data_Exclusive = tryGrabComponentStat(component, "Data_Exclusive", conversion="int") 
                L1_WBCLEANDATA = tryGrabComponentStat(component, "L1_WBCLEANDATA", conversion="int") 
                L1_WBDIRTYDATA = tryGrabComponentStat(component, "L1_WBDIRTYDATA", conversion="int") 
                Unblock = tryGrabComponentStat(component, "Unblock", conversion="int") 
                Exclusive_Unblock = tryGrabComponentStat(component, "Exclusive_Unblock", conversion="int") 
                DmaAck = tryGrabComponentStat(component, "DmaAck", conversion="int") 
                L1_PUTO = tryGrabComponentStat(component, "L1_PUTO", conversion="int") 
                L1_PUTX = tryGrabComponentStat(component, "L1_PUTX", conversion="int") 
                L1_PUTS_only = tryGrabComponentStat(component, "L1_PUTS_only", conversion="int") 
                L1_PUTS = tryGrabComponentStat(component, "L1_PUTS", conversion="int") 
                Writeback_Ack = tryGrabComponentStat(component, "Writeback_Ack", conversion="int") 
                Writeback_Nack = tryGrabComponentStat(component, "Writeback_Nack", conversion="int") 
                L2_Replacement = tryGrabComponentStat(component, "L2_Replacement", conversion="int") 

                component.statistics["read_accesses"]=str(L1_GETS+L1_GETX+Fwd_GETX+Fwd_GETS+Fwd_DMA+Own_GETX+Inv+IntAck+ExtAck+All_Acks+Data+Data_Exclusive+L1_WBCLEANDATA+L1_WBDIRTYDATA+Unblock+Exclusive_Unblock+DmaAck)
                component.statistics["write_accesses"]=str(L1_PUTO+L1_PUTX+L1_PUTS_only+L1_PUTS+Writeback_Ack+Writeback_Nack)
                component.statistics["replacements"]=str(L2_Replacement)
                #print "\n 1:%s   2:%s   3:%s "%(component.statistics["read_accesses"],component.statistics["write_accesses"],component.statistics["replacements"])


                '''try: # for now: include all statistics from "ruby.stats" file:
#		    print'compute read_accesses....................................'
                    component.statistics["read_accesses"] = \
                        str(int(component.statistics["L1_GETS"]) + \
                            int(component.statistics["L1_GETX"]) + \
                 #in4c   #    int(component.statistics["Fwd_GETX"]) + \     # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["Fwd_GETS"]) + \     # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["Fwd_DMA"]) + \     # milad debug not available/
									 # in 16c blackscholes
                 #in4c   #    int(component.statistics["Own_GETX"]) + \    # milad debug not available/
									 # in 16c blackscholes
                 #in4c  #    int(component.statistics["Inv"]) + \    # milad debug not available/
									 # in 16c blackscholes
                        #    int(component.statistics["IntAck"]) + \     # milad debug not available/
									 # in 16c blackscholes
                 #in4c  #    int(component.statistics["ExtAck"]) + \    # milad debug not available/
									 # in 16c blackscholes
                            int(component.statistics["All_Acks"]) + \
                            int(component.statistics["Data"]) + \
                            int(component.statistics["Data_Exclusive"]) + \
                            int(component.statistics["L1_WBCLEANDATA"]) + \
                            int(component.statistics["L1_WBDIRTYDATA"]) + \
                            int(component.statistics["Unblock"]) + \
                            int(component.statistics["Exclusive_Unblock"])  ) #+ \
                  #in4c  #    int(component.statistics["DmaAck"]))      # milad debug not available/
									 # in 16c blackscholes
                    component.statistics["write_accesses"] = \
                        str(int(component.statistics["L1_PUTO"]) + \
                            int(component.statistics["L1_PUTX"]) + \
                            int(component.statistics["L1_PUTS_only"]) + \
                            int(component.statistics["L1_PUTS"]) + \
                            int(component.statistics["Writeback_Ack"]) ) #+ \
                        #    int(component.statistics["Writeback_Nack"]))  # milad debug not available/
									 # in 16c blackscholes
                    component.statistics["replacements"] = \
                        str(int(component.statistics["L2_Replacement"]))
                except:
                    component.statistics["read_accesses"] = "0"
                    component.statistics["write_accesses"] = "0"
                    component.statistics["replacements"] = "0"'''
#		print'compute read_accesses....................%s'%component.statistics["read_accesses"]

        # add l1 directories
        # this is the case of components that I moved around to create the
        # L1 directories; basically the child "directory" of for example
        # [system.dir_cntrl3.directory] (as it comes from config.ini) was
        # moved inside the array cht to become system.L1Directory3;
        if ("L1Directory" in component_name):
            # note that its type is RubyDirectoryMemory; see config.ini file
            # [system.dir_cntrl0.directory]
            # type=RubyDirectoryMemory
            # map_levels=4
            # numa_high_bit=7
            # size=33554432
            # use_map=false
            # version=0
#            size = component.params["size"]
#            block_size = 64 #FIXME
#            assoc = 2 #FIXME
            # Miss Status/Information Holding Register count:
            num_mshrs=64; # int(float(size)/float(block_size))
            component.params["buffer_sizes"]= "%d,%d,%d,%d" \
                %(num_mshrs,num_mshrs,num_mshrs,num_mshrs)
            # to find latency, I need to look in for example in system.dir_cntrl0.memBuffer
            temp_id = component.id

            temp_id = temp_id.replace("L1Directory","dir_cntrl")#dir_cntrl
            temp_id = temp_id+".memBuffer"
            latency = int(cht[temp_id].params["mem_ctl_latency"])
            num_banks = int(cht[temp_id].params["banks_per_rank"])
            # based on what's inside the mcpat code, the following form the 
            # contents of Dir_config[i], when i=
            # 0 capacity=size; 1 blockW=block_size; 2 assoc=assoc;
            # 3 nbanks=num_banks; 4 throughput=1; 5 latency=latency;
            # 6 ?=8 a default value that seems not to be used inside mcpat;
	    #milad debug, correcting dir config
            component.params["Dir_config"] = "%s,%s,%s,%s,%s,%s, %s" \
                %(size,block_size,assoc,num_banks,"1",latency, 8) #TODO: set throughput w.r.t core clock
	    component.params["Dir_config"]=l1_dir_config  #calculated in l2 cache
            # get also the clock frequency as the one of the core
            core_id = component.id
            
            if("ruby" in component.id):
                core_id = core_id.replace("ruby.L1Directory",options.cpu_name) # system.cpu0
                #cpu_clock_rate=int(1/(float( cht[cht[core_id].params['clk_domain']].params['clock'] )*1e-6)) #f=1/T
            else:
                core_id = core_id.replace("L1Directory",options.cpu_name) # system.cpu0
                #cpu_clock_rate=int(1/(float( cht[core_id].params['clock'] )*1e-6)) #f=1/T
            
            cpu_clock_rate=calculateComponentClockRate(cht,core_id)
                             
            print_debug_message("L1Directory in component: " + component_name + " -- " + " CPU NAME: " + options.cpu_name)

            component.params["clockrate"] = str(cpu_clock_rate)
#	    print '24: L1Directory read_access'

            GETX = tryGrabComponentStat(component, "GETX", conversion="int") 
            GETS = tryGrabComponentStat(component, "GETS", conversion="int") 
            Unblock = tryGrabComponentStat(component, "Unblock", conversion="int") 
            Last_Unblock = tryGrabComponentStat(component, "Last_Unblock", conversion="int") 
            Exclusive_Unblock = tryGrabComponentStat(component, "Exclusive_Unblock", conversion="int") 
            Memory_Data = tryGrabComponentStat(component, "Memory_Data", conversion="int") 
            Memory_Ack = tryGrabComponentStat(component, "Memory_Ack", conversion="int") 
            DMA_READ = tryGrabComponentStat(component, "DMA_READ", conversion="int") 
            DMA_ACK = tryGrabComponentStat(component, "DMA_ACK", conversion="int") 
            Data = tryGrabComponentStat(component, "Data", conversion="int") 
            PUTX = tryGrabComponentStat(component, "PUTX", conversion="int") 
            PUTO = tryGrabComponentStat(component, "PUTO", conversion="int") 
            PUTO_SHARERS = tryGrabComponentStat(component, "PUTO_SHARERS", conversion="int") 
            Clean_Writeback = tryGrabComponentStat(component, "Clean_Writeback", conversion="int") 
            Dirty_Writeback = tryGrabComponentStat(component, "Dirty_Writeback", conversion="int") 
            DMA_WRITE = tryGrabComponentStat(component, "DMA_WRITE", conversion="int") 

            component.statistics["read_accesses"]=str(GETX+GETS+Unblock+Last_Unblock+Exclusive_Unblock+Memory_Data+Memory_Ack+DMA_READ+DMA_ACK+Data)
            component.statistics["write_accesses"]=str(PUTX+PUTO+PUTO_SHARERS+Clean_Writeback+Dirty_Writeback+DMA_WRITE)
             #component.statistics["replacements"]=str(L2_Replacement)



            '''try: # for now: include all statistics from "ruby.stats" file:
                component.statistics["read_accesses"] = \
                    str(int(component.statistics["GETX"]) + \
                        int(component.statistics["GETS"]) + \
                        #int(component.statistics["Unblock"]) + \
                        #int(component.statistics["Last_Unblock"]) + \
                        int(component.statistics["Exclusive_Unblock"]) + \
                        int(component.statistics["Memory_Data"]) + \
                        int(component.statistics["Memory_Ack"]) ) # + \
                    #    int(component.statistics["DMA_READ"]) + \  milad debug:in blackscholes 16c
                    #    int(component.statistics["DMA_ACK"]) + \  milad debug:in blackscholes 16c
                    #    int(component.statistics["Data"]))
                component.statistics["write_accesses"] = \
                    str(int(component.statistics["PUTX"]) + \
                        #int(component.statistics["PUTO"]) + \
                        int(component.statistics["PUTO_SHARERS"]) + \
                        int(component.statistics["Clean_Writeback"]) + \
                        int(component.statistics["Dirty_Writeback"]) )# + \
                   #     int(component.statistics["DMA_WRITE"]))  milad debug:in clackscholes 16c
            except:
                component.statistics["read_accesses"] = "0"
                component.statistics["write_accesses"] = "0"'''

          
        # create MC component and add in the tree as child of system
        # cris: I am not sure if I should stick to just one MC that
        # I create here once via the existence of physmem; OR, I should
        # create for example in the case of 2x2 four MC's via the
        # existence of 
        # [system.dma_cntrl0] type=DMA_Controller ...
        # inside config.ini; I saw some papers advocating a num of MC's
        # equal to sqrt(N), N=num of cores;
        # NOTE: current version is from original script...
        if "physmem" in component.id and options.system_name in component.id:
            # example:
            # [system.physmem]
            # type=PhysicalMemory
            # file=
            # latency=30000
            # latency_var=0
            # null=false
            # range=0:134217727
            # zero=false
            # port=system.piobus.port[0] system.l1_cntrl0.sequencer.physMemPort system.l1_cntrl1.sequencer.physMemPort system.l1_cntrl2.sequencer.physMemPort system.l1_cntrl3.sequencer.physMemPort system.dma_cntrl0.dma_sequencer.physMemPort system.dma_cntrl1.dma_sequencer.physMemPort
#	    print '25: physmem read_access comp_name:%s comp_id=%s' %(component_name , component.id)
            # (a) define this as a "mem" component 
            component.re_name=component.name.replace("physmem", "mem")
            component.re_id=component.id.replace("physmem", "mem")
            try:
                component.statistics["num_phys_mem_accesses"] = \
                    str(int(component.statistics["num_phys_mem_reads"]) + \
                        int(component.statistics["num_phys_mem_writes"]))
            except:
                component.statistics["num_phys_mem_accesses"] = "0"

            # (b) create a "mc" memory controller component;
            child_id="%s.mc" %(options.system_name)
            new_params={}
            # NOTE: there is something fishy here: latency=30000 for example
            # in config.ini compared to latency=3 for example for system.l1_cntrl1.L1DcacheMemory
            # so, I do not think it's correct to compute mc_clock like in the
            # original script mc_clock=1/latency*1e-6;
            # instead, I'll just use "boot_cpu_frequency" of "system"
            # from config.ini
            new_params["mc_clock"] = str( cht[options.system_name].params['boot_cpu_frequency'])
            new_comp=Component(child_id, new_params)
            try:
                new_comp.statistics["num_phys_mem_accesses"] = component.statistics["num_phys_mem_accesses"]
                new_comp.statistics["num_phys_mem_reads"] = component.statistics["num_phys_mem_reads"]
                new_comp.statistics["num_phys_mem_writes"] = component.statistics["num_phys_mem_writes"]
            except:
                new_comp.statistics["num_phys_mem_accesses"] = "0"
                new_comp.statistics["num_phys_mem_reads"] = "0"
                new_comp.statistics["num_phys_mem_writes"] = "0"
            new_components_to_add.append((child_id,new_comp))
            cht[options.system_name].children.append(new_comp)

	#milad debug counting l1directory
	if ptype=='RubyDirectoryMemory':
		num_l1directories+=1
#		print '53: num_l1direcories =%s' %num_l1directories
        # count cache levels        
        if ptype == "RubyCache" and ("L1DcacheMemory" in component_name or "L1IcacheMemory" in component_name):
#	    print '32: count + id:%s name:%s' % (component.id,component_name)
            if num_cache_levels < 1:
                num_cache_levels = 1
            num_l1s +=1 
            if num_l1s ==1:
                homogeneous_L1s="1"
            elif num_l1s > 1:
                homogeneous_L1s="0"   
        if ptype == "RubyCache" and "L2cacheMemory" in component_name:
#	    print '32: count + id:%s name:%s' % (component.id,component_name)	    	
            if num_cache_levels < 2:
                num_cache_levels = 2
            num_l2s +=1
            if num_l2s ==1:
                homogeneous_L1Directories="1"
                homogeneous_L2s="1"
            elif num_l2s > 1:
                homogeneous_L1Directories="0"
                homogeneous_L2s="0"	 
        if ptype == "RubyCache" and "L3" in component_name:
            if num_cache_levels < 3:
                num_cache_levels = 3
            num_l3s +=1
            if num_l3s ==1:
                homogeneous_L2Directories="1"
                homogeneous_L3s="1"
            elif num_l3s > 1:
                homogeneous_L2Directories="0"
                homogeneous_L3s="0"
    '''
    print num_cache_levels
    print num_l1s
    print homogeneous_L1s
    print num_l2s
    print homogeneous_L2s
    print num_l3s
    print homogeneous_L3s
    '''

    # part (2): only network(s);

    for c_key in cht:
        component = cht[c_key]
        if not component.params.has_key('type'):
            continue # skip components witout a type;
        params = component.params
        ptype = params['type']
        component_id = component.id
        if ptype == 'GarnetNetwork_d': # original script had Mesh2D
            print 'garnet'
            # example:
            # [system.ruby.network]
            # type=GarnetNetwork_d
            # children=topology
            # buffers_per_ctrl_vc=1
            # buffers_per_data_vc=4
            # control_msg_size=8
            # ...

            # I take it out as McPAT deals with crossbar NoC; if
            # I record inside power.xml that num_noc!=0, McPAT will
            # want to read one...
            #num_nocs = num_nocs +1
            component.params["topology"] = "Mesh"
            # get the clock info from the parent of network; that is
            # from system.ruby as it appears in config.ini:
            # [system.ruby]
            # type=RubySystem
            # clock=500
            # NOTE: this is ok for now, but if I'll have DVFS or VFI then
            # parts of the network may be clocked at different clock freqs;
            temp = component_id.split('.')
            #cpu_clock_rate=int(1/(float( cht[temp[0]+"."+temp[1]].params['clock'] )*1e-6)) #f=1/T
            cpu_clock_rate=calculateComponentClockRate(cht,temp[0]+"."+temp[1])
            component.params["clockrate"] = str(cpu_clock_rate)
            num_ports=num_cores # must be already computed in part (1) above
            component.params["horizontal_nodes"] = str(int(math.sqrt(num_ports))) #Makes assumption about the topology being near square like
            component.params["vertical_nodes"] = str(int(math.ceil(num_ports/float(component.params["horizontal_nodes"])))) #square like topology examinations
            component.params["has_global_link"] = "0" #FIXME: what is this?
            component.params["link_throughput"] = "1"
            component.params["link_latency"] = "1"
            component.params["input_ports"] = str(num_ports)
            component.params["output_ports"] = str(num_ports)
            component.statistics["total_routing_counts"] = 0

    
    for key_id, new_comp in new_components_to_add:
        cht[key_id]=new_comp


    # add calculated statistics
    cht[options.system_name].statistics["total_cycles"] = \
        str(int(sht["%s."%(options.system_name)+"sim_ticks"])/int(fastest_clock))
    cht[options.system_name].params["number_of_cores"] = str(num_cores)
    cht[options.system_name].params["number_of_L1Directories"] = str(num_l1directories) #milad debug instead of num_l2s
    cht[options.system_name].params["number_of_L2s"] = str(num_l2s)
    cht[options.system_name].params["number_of_L2Directories"] = str(num_l3s)
    cht[options.system_name].params["number_of_L3s"] = str(num_l3s)
    cht[options.system_name].params["number_of_nocs"] = str(num_nocs)
    cht[options.system_name].params["homogeneous_cores"] = homogeneous_cores
    cht[options.system_name].params["number_cache_levels"] = str(num_cache_levels)
    cht[options.system_name].params["homogeneous_L2s"] = homogeneous_L2s
    cht[options.system_name].params["homogeneous_L3s"] = homogeneous_L3s
    cht[options.system_name].params["homogeneous_L1Directories"] = homogeneous_L1Directories
    cht[options.system_name].params["homogeneous_L2Directories"] = homogeneous_L2Directories
    cht[options.system_name].params["number_of_dir_levels"] = str(num_cache_levels-1)
    cht[options.system_name].params["homogeneous_nocs"] = homogeneous_nocs
    
'''
moveAroundSomeComponents() does the following component movements;
because this is how McPAT expects/likes it;
(1) moves L1DcacheMemory,L1IcacheMemory from l1_cntrl0 to cpu0
(2) moves L2cacheMemory from l2_cntrl0 to cpu0
(3) moves directory from dir_cntrl0 to cpu0

*child refers to children field of component in .ini
'''
def moveAroundSomeComponents(cht):
    
#    print_debug_message("cht: "
#                            + "\ncht length: " + str(len(cht.keys()))

#                            + "\ncht keys: \n\n" + str(cht.keys())
#                            + "\ncht values: \n\n" + str(cht.values()))
        
    
    for c_key in cht: #system.l1_cntrl0
        component = cht[c_key]
        
        
 #       print_debug_message("c_key: " + c_key)
        
        if component.params.has_key('children'):
            for child in component.params['children'].split():
                if c_key == "root":
                    child_id = child
                else:
                    child_id = "%s.%s" %(component.id, child) #system.l1_cntrl0.L1DcacheMemory
                
                print_debug_message("child_id: " + child_id)
                
                if (child == "L1DcacheMemory") or (child == "L1IcacheMemory"):
                    # remove it from system.l1_cntrl0
                    component.children.remove( cht[child_id] )
                    new_c_key = c_key
                    new_c_key = new_c_key.replace("l1_cntrl",options.cpu_name)
                    
                    print_debug_message("new_c_key: " + new_c_key)
                    
                    # add it to system.cpu0
                    cht[new_c_key].children.append( cht[child_id] )
                    new_child_id = child_id
                    new_child_id = new_child_id.replace("l1_cntrl",options.cpu_name)
                    # update its id as a cht[] component itself to reflect its new owner;
                    cht[child_id].id = new_child_id
                
                if (child == "L2cacheMemory") :
                    # remove it from system.l2_cntrl0
                    component.children.remove( cht[child_id] )
                    # add it to system
                    cht[options.system_name].children.append( cht[child_id] )
                    new_child_id = component.id #system.l2_cntrl0
                    new_child_id = new_child_id.replace("l2_cntrl","L2cacheMemory")
                    new_child_name = new_child_id
                    new_child_name = new_child_name.replace(options.system_name+".","")
                    # update its id as a cht[] component itself to reflect its new owner;
                    cht[child_id].name = new_child_name
                    cht[child_id].id = new_child_id
                # ------------------------------------------------------------------------
                # Ruby specific cache controller that replaced the system controller
                if ((child == "L1Dcache") or (child == "L1Icache")) and ("ruby" in c_key):
                    print_debug_message("Replacing ruby L1 cache controller, identified by key - " + c_key)
                    
                    # remove it from system.l1_cntrl0
                    component.children.remove( cht[child_id] )
                    new_c_key = c_key
                    new_c_key = new_c_key.replace("ruby.l1_cntrl",options.cpu_name)
                    
                    print_debug_message("new_c_key: " + new_c_key)
                    
                    # add it to system.cpu0
                    print_debug_message(new_c_key + " children: " + str(cht[new_c_key].children))

                    cht[new_c_key].children.append( cht[child_id] )
                    
                    print_debug_message(new_c_key + " new children: " + str(cht[new_c_key].children))
                    
                    new_child_id = child_id
                    new_child_id = new_child_id.replace("ruby.l1_cntrl",options.cpu_name)
                    
                    # update its id as a cht[] component itself to reflect its new owner;
                    print_debug_message(child_id + " id: " + cht[child_id].id)

                    cht[child_id].id = new_child_id
                    
                    print_debug_message(child_id + " new id: " + cht[child_id].id)
                
                if ((child == "L2cache")) and ("ruby" in c_key):
                    print_debug_message("Replacing ruby L2 cache controller...")
                    
                    # remove it from system.l2_cntrl0
                    component.children.remove( cht[child_id] )
                    # add it to system
                    cht[options.system_name].children.append( cht[child_id] )
                    new_child_id = component.id #system.l2_cntrl0
                    new_child_id = new_child_id.replace("l2_cntrl","L2cache")
                    new_child_name = new_child_id
                    new_child_name = new_child_name.replace(options.system_name+".","")
                    # update its id as a cht[] component itself to reflect its new owner;
                    cht[child_id].name = new_child_name
                    cht[child_id].id = new_child_id
                    
                # ------------------------------------------------------------------------
                
                if (child == "directory"):
                    
                    print_debug_message("Removing " + child_id + " from " + component.id + " and adding to system...")
                    
                    # remove it from system.dir_cntrl0's children {directory, memBuffer}
                    component.children.remove( cht[child_id] )
                    # add it to system
                    cht[options.system_name].children.append( cht[child_id] )
                    new_child_id = component.id #system.dir_cntrl0
                    
                    print_debug_message("Replacing dir_cntrl in " + new_child_id + "...")
                    
                    new_child_id = new_child_id.replace("dir_cntrl","L1Directory") #system.L1Directory0
                    new_child_name = new_child_id #system.L1Directory0
                    
                    print_debug_message("options var: \n\n" + str(options))
                                        
                    print_debug_message("Replacing system info in " + new_child_name + "...")
                    
                    #new_child_name = new_child_name.replace(options.system_name+".","") #L1Directory0
                    
                    search_for_this = re.search("L1Directory", new_child_name)
                    new_child_name = new_child_name[:0] + new_child_name[search_for_this.start():]
                    
                    # update its id as a cht[] component itself to reflect its new owner;
                    cht[child_id].name = new_child_name #L1Directory0
                    cht[child_id].id = new_child_id #system.L1Directory0
                
                    print_debug_message("New Child Name " + new_child_name + "...")
                    print_debug_message("New Child ID " + new_child_id + "...")


'''
createComponentTree() does the following:
(1) creates a tree of components by looking at the config.ini 
parameter children for each component. 
(2) stats are added to each component as appropriate.
(3) missing stats are generated.
(4) component translator is set
(5) the translator grabs all relevant stats and params for
the component and renames from M5 names to McPat names
'''
def createComponentTree(cht, sht):

    # (1) create a component tree by looking at the "children" parameter
    # milad debug component cht			
    for comp1 in cht:	
	if 'ruby.' in cht[comp1].name: 
		comp_name_split= cht[comp1].name.split('.')  
		cht[comp1].name=comp_name_split[1]
		comp_id_split= cht[comp1].id.split('.')   
		comp_id_new = comp_id_split[0]		
		for i in range(2 , len(comp_id_split)):
		     comp_id_new=comp_id_new+'.'+comp_id_split[i]  
		print 'comp_id_new ======%s' %comp_id_new
		print "components: %s comp_name_split= %s" % (comp1,comp_name_split)
		print 'id: %s -- name: %s -- translated_params= %s -- translated_params_order= %s -- children= %s -- calc_statistics= %s ---------' % ( cht[comp1].id , cht[comp1].name , cht[comp1].translated_params , cht[comp1].translated_params_order , cht[comp1].children , cht[comp1].calc_statistics   )
    
    Component ( 'system.l2_cache1' , 'params')
    
    for c_key in cht:
      component = cht[c_key]
      if component.params.has_key('children'):
            for child in component.params['children'].split():
#		print "has_children: child [%s] = %s"%(component.name,child)                
		if c_key == "root":
#                   print '1'
		    child_id = child
                else:
#		    print '2'
                    child_id = "%s.%s" %(component.id, child)
#		    print 'child_id=%s' %child_id
#		else: 
#	    	    print '3'
#		    cmpSplit=component.id.split('system.')
#	            print 'cmpSplit=%s' %cmpSplit 
#          	    child_id= 'system.ruby.%s.%s' %(cmpSplit[1],child)
							                
		if not cht.has_key(child_id):		            
		    # this child of this component must exist already as
                    # a component itself created during the run of parseSystemConfig;
                    panic("3:child_id %s does not exist." %(child_id),5)
                component.children.append(cht[child_id])
                
    # (2) add all statistics to right component
    for stat_key in sht:
        #find the longest prefix that matches a component id
        stat = sht[stat_key]
        # example of "stat_key":
        # system.l1_cntrl2.L1IcacheMemory.Ifetch
        # system.l2_cntrl1.L1_GETS
        # system.l1_cntrl0.L1DcacheMemory.Writeback_Ack_Data
        temp = stat_key.split('.')
        num_fields = len(temp)
        prefix_id = None
 #       print 'num_fields: ........................................................ :%s'%num_fields
	for x in xrange(num_fields, 0, -1):
	    
            prefix_id = genId(temp[0:x])
            #if 'dir_cntrl' in stat_key: print prefix_id
            if cht.has_key(prefix_id):
                break # found a component whose id is part of this "stat" id;
        
        # examples of "prefix_id" at this moment: 
        # system.l1_cntrl3.L1DcacheMemory
        # system.l2_cntrl3
        # system.l1_cntrl2.L1IcacheMemory
        # add the statistic to the right component
        stat_id = genId(temp[x:num_fields])
        # examples of "stat_id":
        # Ifetch
        # Exclusive_Unblock
        if len(stat_id) < 1:
            panic("error: parsed invalid stat.",6)
        
        # for all those stats that don't have a component, add it to root component
        if not cht.has_key(prefix_id):
            prefix_id="root"
            stat_id = genId(temp)
              
    
        component = cht[prefix_id]
        # example:
        # system.l1_cntrl3.L1DcacheMemory {statistics} [ Writeback_Ack_Data ] = 12345
        component.statistics[stat_id] = stat
        #print stat_id
    # (3) 

    moveAroundSomeComponents(cht)
#    #milad debug 6 print component+params+statistics after movearoundsomecomponents
    for debug_id in cht:
	if '.L1Dcache' in cht[debug_id].name:	
	    print '6: config.ini---- components: name= %s id= %s --- params= %s --- statistics= %s' %(cht[debug_id].name,cht[debug_id].id , cht[debug_id].params , cht[debug_id].statistics)

    # cris: this a first phase (mechanism) to filter out
    # unwanted components; also, here we rename some, which affects
    # actually the second mechanisms for filtering out components,
    # mechanisms which is in "formXmlPower(self, parent_node, doc)"
    # function; so be aware of this; if you rename here, then second 
    # mechanim must work with the right pairs...
    # (4) filter out unwanted component info in power.xml        
    for key in cht:
        cur_component=cht[key]
        
        print_debug_message("key: " + key
                            + "\ncur_component keys: \n\n" + str(cur_component.params.keys())
                            + "\ncur_component values: \n\n" + str(cur_component.params.values()))
        cur_component.checkToFilter()
        cur_component.checkToRenameReid()
#milad debug after rename 
    for id in cht:
	if 'core' in cht[id].id:
   	     print '12: %s            before    gencalcstats'%cht[id].id

    # cris: I should move this before the next for loop with the renaming stuff?
    # because a lot of things inside this generateCalcStats are done
    # based on the original naming l1_cntrl, l2_cntrl, dir_cntrl,
    # L1DcacheMemory, etc. as they appear in config.ini generated by gem5;
    # (5) generate calculated statistics
    generateCalcStats(cht, sht)

    # (6) set component translators
    for id in cht:        
#	print "28: %s" %id
        component = cht[id]
        setComponentTranslator(component)		
        if (component.translator != Component.UNKNOWN):
            component.translator.translate_params(component)
            component.translator.translate_statistics(component)
#milad debug 7 print component+params+statistics in movearoundsomecomponents
#    for debug_id in cht:
#	if '.L1Dcache' in cht[debug_id].name:	
#	    print '7: config.ini---- components: name= %s id= %s --- params= %s --- statistics= %s' %(cht[debug_id].name,cht[debug_id].id , cht[debug_id].params , cht[debug_id].statistics)

    #milad debug component
'''    for comp1 in cht:	
	if 'ruby.' in cht[comp1].name: 
		comp_name_split= cht[comp1].name.split('.')  
		cht[comp1].name=comp_name_split[1]
		comp_id_split= cht[comp1].id.split('.')   
		comp_id_new = comp_id_split[0]		
		for i in range(2 , len(comp_id_split)):
		     comp_id_new=comp_id_new+'.'+comp_id_split[i]  
		print 'comp_id_new ======%s' %comp_id_new
		print "components: %s comp_name_split= %s" % (comp1,comp_name_split)
		print 'id: %s -- name: %s -- translated_params= %s -- translated_params_order= %s -- children= %s -- calc_statistics= %s ---------' % ( cht[comp1].id , cht[comp1].name , cht[comp1].translated_params , cht[comp1].translated_params_order , cht[comp1].children , cht[comp1].calc_statistics   )
		print '-- params --: %s' %cht[comp1].params
		print '-- stats --:----------------------------- %s' %cht[comp1].statistics
'''
'''

self.id = id
        self.params = params
        self.re_id=None
        self.re_name=None
        self.translated_params = {}
        self.translated_params_order = []
        self.children = []
        self.statistics = {}
        self.translated_statistics = {}
        self.calc_statistics = {}
        self.translator = Component.UNKNOWN
        self.power_xml_filter=False
        self.translated_statistics_order=[]
'''
'''
genComponentXml is responsible for generating summary.xml,
the intermediate form for power.xml
'''                
def genComponentXml(root_component, out_path):
    import xml.dom.minidom
    global options
    doc = xml.dom.minidom.Document()
        
    root_component.formXml(doc ,doc)
    if options.verbose:
        print "writing:%s" %(out_path)
    f = open(out_path, 'w')
    f.write(doc.toprettyxml())
    f.close()

'''
genPowerXml is responsible for generating power.xml,
the interface for McPat
''' 
def genPowerXml(root_component, out_path):
    import xml.dom.minidom
    global options
    doc = xml.dom.minidom.Document()

    root_component.formXmlPower(doc ,doc)
    if options.verbose:
        print "writing:%s" %(out_path)
    f = open(out_path, 'w')
    f.write(doc.toprettyxml())
    f.close()

'''
# a subtle dirty thing: config.ini counts cores as 01,02,03,...
# while controllers are counted as 1,2,3,... so, I need to take care of 
# "0" if index less than 10...
'''                
def clean_up_key(key):
    res = key
    # these replacement are based on how config.ini looks now;
    # this may need to be updated;
    if ("cpu00" in res): res=res.replace("cpu00","cpu0")
    if ("cpu01" in res): res=res.replace("cpu01","cpu1")
    if ("cpu02" in res): res=res.replace("cpu02","cpu2")
    if ("cpu03" in res): res=res.replace("cpu03","cpu3")
    if ("cpu04" in res): res=res.replace("cpu04","cpu4")
    if ("cpu05" in res): res=res.replace("cpu05","cpu5")
    if ("cpu06" in res): res=res.replace("cpu06","cpu6")
    if ("cpu07" in res): res=res.replace("cpu07","cpu7")
    if ("cpu08" in res): res=res.replace("cpu08","cpu8")
    if ("cpu09" in res): res=res.replace("cpu09","cpu9")

    if ("links00" in res): res=res.replace("links00","links0")
    if ("links01" in res): res=res.replace("links01","links1")
    if ("links02" in res): res=res.replace("links02","links2")
    if ("links03" in res): res=res.replace("links03","links3")
    if ("links04" in res): res=res.replace("links04","links4")
    if ("links05" in res): res=res.replace("links05","links5")
    if ("links06" in res): res=res.replace("links06","links6")
    if ("links07" in res): res=res.replace("links07","links7")
    if ("links08" in res): res=res.replace("links08","links8")
    if ("links09" in res): res=res.replace("links09","links9")

    if ("routers00" in res): res=res.replace("routers00","routers0")
    if ("routers01" in res): res=res.replace("routers01","routers1")
    if ("routers02" in res): res=res.replace("routers02","routers2")
    if ("routers03" in res): res=res.replace("routers03","routers3")
    if ("routers04" in res): res=res.replace("routers04","routers4")
    if ("routers05" in res): res=res.replace("routers05","routers5")
    if ("routers06" in res): res=res.replace("routers06","routers6")
    if ("routers07" in res): res=res.replace("routers07","routers7")
    if ("routers08" in res): res=res.replace("routers08","routers8")
    if ("routers09" in res): res=res.replace("routers09","routers9")

    return res

'''
parseSystemConfig is repsonsible for creating a component dictionary, a statisitic dictionary, and
then using this two structures to build a an internal tree of component objects that contain
fields with their parameters and statistics. 
@config_file_path string to the config.ini file
@stats_file_path string to the stat file path
@out_file_path path to put the summary.xml file that is the intermediate of the power.xml file
@out_file_path_2 path to put the power.xml file
@cht dictionary that contains all component keys and their associated objects.
@sht dictionary that contains all stat keys and their associated stat objects. 
'''                
def parseSystemConfig(ruby_file_path, config_file_path, stats_file_path, out_file_path, out_file_path_2, cht, sht):

    # (1) parsing from file "m5out/config.ini" 
    # (components and their params)
    #milad debug counting number_of_cpus because its needed in defining dir_size
    global total_cpu_num
    total_cpu_num=0
    with open(config_file_path) as openfileobject:
       for line in openfileobject:
       	    if 'cpu' in line:
		total_cpu_num=total_cpu_num+1
#    print '51:  total_cpu_num=%s' %total_cpu_num
    	
    # parse the configuration
    f = open(config_file_path, 'r')
    id = None # the id of current system component
    params = {} # params set for the current config
    
    # add all the components to the dictionary;
    # including for cache and directory controller;
    for line in f:
        # NOTE: necsessary evil: clean up all lines such that
        # they are all consistent in terms of counting stuff;
        line = clean_up_key(line) # "0i" --> "i"

        #look for a new param id
        #example lines:
        #[system.l1_cntrl3]
        #type=L1Cache_Controller
        #children=L1DcacheMemory L1IcacheMemory sequencer
        #L1DcacheMemory=system.l1_cntrl3.L1DcacheMemory
        #L1IcacheMemory=system.l1_cntrl3.L1IcacheMemory
        #buffer_size=0
        #cntrl_id=3
        #...
        #[system.l1_cntrl3.L1DcacheMemory]
        #[system.l1_cntrl3.L1IcacheMemory]
        #[system.l1_cntrl3.sequencer]
        #[system.l2_cntrl3]
        #[system.l2_cntrl3.L2cacheMemory]
        #[system.dir_cntrl3]
        #[system.dir_cntrl3.directory]
        #[system.dir_cntrl3.memBuffer] 
        if '[' in line and ']' in line and '=' not in line:
            id = line.rstrip().rstrip(']').lstrip('[')
            if cht.has_key(id):
                if options.verbose:
                    print "Identical ID match: %s. It happens for NoC links." %(id)
                    #panic("Identical component id occurs twice! Invalid Config",7)
                
        #find params for id 
        # examples:
        # params[ type ] = L1Cache_Controller
        # params[ children ] = L1DcacheMemory L1IcacheMemory sequencer
        elif id: 
            temp = line.split('=')
            #assume that a newline or line without an = is the beginning of the next component
            if len(temp) == 0 or len(temp) == 1:	    	
		           	
		cht[id]=Component(id, params)
		params = {}
#		print 'id=%s' %id                 

#	        if 'system.ruby.' in id:
#			idSplit=id.split('.ruby.')	
#			id=idSplit[0]+'.'+idSplit[1]
#			cht[id]=Component(id, params)
		id=None
            #grab the param
            else:
                if len(temp) != 2:
                    warning("A param with more than one '=' occurred: %s. parts=%d" %(line, len(temp)))
                params[temp[0]]=temp[1].rstrip()
        #milad debug 1 component read config.ini
#        for debug_id in cht:
#	    if 'L1Dcache' in cht[debug_id].id:	
		#print 'component_new= %s' % component_new
#		params={}
#		cht[component_new]=Component(component_new,params)
#		cht[component_new].params=cht[cht[debug_id].id].params
#		cht['system.l2_cntrl'+str(i-1)] = cht['system.ruby.l2_cntrl'+str(i-1)]				



    # (2) parsing from file "m5out/stats.txt"

    # add all the statistics to the dictionary
    g = open(stats_file_path, 'r')
    for line in g:
        line = clean_up_key(line) # "0i" --> "i"
        # example:
        # system.cpu2.dtb.data_accesses 14724983
        #       group(1)                group(2)
        match = re.match("(%s[\.0-9a-zA-z_:]*)\s+([\w\.]+)\s+"%(options.system_name), line)
        if match:
            sht[match.group(1)] = match.group(2)
            continue
            
        match = re.match(r"(global[\.0-9a-zA-z_:]*)\s+([\w\.]+)\s+", line)
        if  match:
            sht[match.group(1)] = match.group(2)
            continue
        
        match = re.match(r"([\.0-9a-zA-z_:]*)\s+([\w\.]+)\s+", line)
        if  match:
            sht["%s."%(options.system_name)+match.group(1)] = match.group(2)
            continue

	match = re.match(r"([\.0-9a-zA-z_:]*)\s+([\w\.]+)\s+", line)
        if  match:
            sht["%s."%(options.system_name)+match.group(1)+match.group(2)] = match.group(3)
            continue

    #milad debug 3 read ruby.stats
    h = open(stats_file_path, 'r')

    #milad debug	
    build_component_flag_l1directory=0
    build_component_flag_l1directory_append_sys_child=0
    build_component_flag_l1_cntrl_Icache=0
    build_component_flag_l1_cntrl_Icache_append_sys_child=0
    build_component_flag_l1_cntrl_Dcache=0
    build_component_flag_l1_cntrl_Dcache_append_sys_child=0
    build_component_flag_l2_cntrl=0
    build_component_flag_l2_cntrl_append_sys_child=0
#milad debug read ruby from stats
    for line in h:
        line = clean_up_key(line) # "0i" --> "i"
#        if len(temp) == 0 or len(temp) == 1:
 #               id = None

        if 'Directory_Controller' in line: # this is the case of id = system.l1_cntrl 		
		id = "L1Directory"		
		if 'total'  not in line:		
		    element = line.split()
		    elementSplit = element[0].split('.')	
		    for k in range (0 , len (elementSplit)):
			if elementSplit[k]=='Directory_Controller' :
			     addString = elementSplit[k+1]
			     for j in range ((k+2) , len(elementSplit) ):
				addString=addString+'.'+elementSplit[j]
		    temp = line.split('|')	
		    for i in range(1,len(temp)):						
			      tempData= temp[i].split()			
		              sht['system.ruby.dir_cntrl'+str(i-1)+'.directory.'+addString] = tempData[0]

        if 'L2Cache_Controller' in line: # this is the case of id = system.l1_cntrl 		
		id = "L2cacheMemory"		
		if 'total'  not in line:		
		    element = line.split()
		    elementSplit = element[0].split('.')	
		    for k in range (0 , len (elementSplit)):
			if elementSplit[k]=='L2Cache_Controller' :
			     addString = elementSplit[k+1]
			     for j in range ((k+2) , len(elementSplit) ):
				addString=addString+'.'+elementSplit[j]
		    temp = line.split('|')	
		    if build_component_flag_l2_cntrl==0:		    
			for i in range(1,len(temp)):
			      component_new=options.system_name+"."+id+str(i-1)
			      params={}
			      cht[component_new]=Component(component_new,params)
			      cht[component_new].params=cht['system.ruby.l2_cntrl'+str(i-1)+'.L2cache'].params
#			      cht['system.l2_cntrl'+str(i-1)] = cht['system.ruby.l2_cntrl'+str(i-1)]				
		        build_component_flag_l2_cntrl=1 #lock Do not build l2_cntrl again			    
		    for i in range(1,len(temp)):						
			      tempData= temp[i].split()			
		              sht[options.system_name+"."+id+str(i-1)+'.'+addString] = tempData[0]
		    if build_component_flag_l2_cntrl_append_sys_child==0:		    
			for i in range(1,len(temp)):
			      cht[options.system_name].children.append(cht[options.system_name+"."+id+str(i-1)]) 
			           
		        build_component_flag_l2_cntrl_append_sys_child=1 #lock Do not append l2_cntrl again				
# Milad debug
# L1Cache in stats.txt
	if 'L1Cache_Controller' in line:
		if 'total'  not in line:
			if 'Ifetch' in line:
				id='L1IcacheMemory'
				element = line.split()
		 		elementSplit = element[0].split('.')	
		                for k in range (0 , len (elementSplit)):
					if elementSplit[k]=='L1Cache_Controller' :
			     			addString = elementSplit[k+1]
			     			for j in range ((k+2) , len(elementSplit) ):
							addString=addString+'.'+elementSplit[j]
				temp = line.split('|')
      		                if build_component_flag_l1_cntrl_Icache==0:
					for i in range(1,len(temp)):
			      			#component_new=options.system_name+"."+id+str(i-1)
						component_new='system.cpu'+str(i-1)+'.'+id
			      			params={}
						params ['type']="RubyCache"
			      			cht[component_new]=Component(component_new,params)
			      			cht[component_new].params=cht['system.ruby.l1_cntrl'+str(i-1)+'.L1Icache'].params
#						print '0000 id= %s    name= %s' % (cht[component_new].id , cht[component_new].name) 
	  			        build_component_flag_l1_cntrl_Icache=1 #lock Do not build l2_cntrl 
		    		for i in range(1,len(temp)):						
					      tempData= temp[i].split()			
				              sht['system.cpu'+str(i-1)+'.'+id+'.'+addString] = tempData[0]
					      sht['system.ruby.l1_cntrl'+str(i-1)+'.L1Icache.'+addString] = tempData[0] #NEW
				if build_component_flag_l1_cntrl_Icache_append_sys_child==0:		    
					for i in range(1,len(temp)):
			    			cht['system.cpu'+str(i-1)].children.append(cht['system.cpu'+str(i-1)+'.'+id]) 
			           
		  		        build_component_flag_l1_cntrl_Icache_append_sys_child=1 #lock Do not append l2_cntrl 				
			
			else:
				id='L1DcacheMemory'
				element = line.split()
		 		elementSplit = element[0].split('.')	
		                for k in range (0 , len (elementSplit)):
					if elementSplit[k]=='L1Cache_Controller' :
			     			addString = elementSplit[k+1]
			     			for j in range ((k+2) , len(elementSplit) ):
							addString=addString+'.'+elementSplit[j]
				temp = line.split('|')
      		                if build_component_flag_l1_cntrl_Dcache==0:
					for i in range(1,len(temp)):
			      			component_new='system.cpu'+str(i-1)+'.'+id
			      			params={}
						params ['type']="RubyCache"
			      			cht[component_new]=Component(component_new,params)
			      			cht[component_new].params=cht['system.ruby.l1_cntrl'+str(i-1)+'.L1Dcache'].params
	  			        build_component_flag_l1_cntrl_Dcache=1 #lock Do not build l2_cntrl 
		    		for i in range(1,len(temp)):						
					      tempData= temp[i].split()			
				              sht['system.cpu'+str(i-1)+'.'+id+'.'+addString] = tempData[0]
				if build_component_flag_l1_cntrl_Dcache_append_sys_child==0:		    
					for i in range(1,len(temp)):
			    			cht['system.cpu'+str(i-1)].children.append(cht['system.cpu'+str(i-1)+'.'+id]) 
			           
		  		        build_component_flag_l1_cntrl_Dcache_append_sys_child=1 #lock Do not append l2_cntrl    
 
#    l1_cntrl0_id=options.system_name+"L2_cntrltest"
#    params = {}
#    params["type"]="1"
#    cht[l1_cntrl0_id]=Component(l1_cntrl0_id, params)
#    sht[l1_cntrl0_id]=sht
#    sht[l1_cntrl0_id+".total_load_perc"]="0.7"

#    print 'milad debug end of manipulated code'

    #    print_debug_message("Parsing ruby.stats line:\n\n" + line)

    # (4) add some "default"/standard components that seem to be 
    # required by McPAT; I use default values as I do not see them reported
    # in config.ini, stats.txt, or ruby.stats;
    # (a) create "dummy" components: system.niu, system.pcie, and system.flashc
    # these are wanted by the McPAT tool, which errors out if these components
    # are not included at the end of power.xml; I could just change the code 
    # of McPAT to fix that but I prefer this workaround;
    # notice that these three components are created automatically if you used
    # the other method of generating the power.xml, that is the Perl script
    # m5-mcpat.pl + mcpat-template.xml
    mem_id = options.system_name+".physmem"
    params = {}
    params["type"]='0'
    params["mem_tech_node"]="9999"
    params["device_clock"]="9999"
    params["peak_transfer_rate"]="9999"
    params["internal_prefetch_of_DRAM_chip"]="9999"
    params["capacity_per_channel"]="9999"
    params["number_ranks"]="9999"
    params["num_banks_of_DRAM_chip"]="9999"
    params["Block_width_of_DRAM_chip"]="9999"
    params["output_width_of_DRAM_chip"]="9999"
    params["page_size_of_DRAM_chip"]="9999"
    params["burstlength_of_DRAM_chip"]="9999"
    cht[mem_id]=Component(mem_id, params)
    sht[mem_id+".memory_accesses"]="9999"
    sht[mem_id+".memory_reads"]="9999"
    sht[mem_id+".memory_writes"]="9999"
    cht[options.system_name].children.append(cht[mem_id])

    dummy1_id = options.system_name+".niu"
    params = {}
    params["type"]="0"
    params["clockrate"]="350"
    params["number_units"]="2"
    cht[dummy1_id]=Component(dummy1_id, params)
    sht[dummy1_id+".duty_cycle"]="1.0"
    sht[dummy1_id+".total_load_perc"]="0.7"
    
    dummy2_id = options.system_name+".pcie"
    params = {}
    params["type"]="0"
    params["withPHY"]="1"
    params["clockrate"]="350"
    params["number_units"]="1"
    params["number_channels"]="8"
    cht[dummy2_id]=Component(dummy2_id, params)
    sht[dummy2_id+".duty_cycle"]="1.0"
    sht[dummy2_id+".total_load_perc"]="0.7"

    # system flash controller; do I really need this?
    dummy3_id = options.system_name+".flashc"
    params = {}
    params["number_flashcs"]="0"
    params["type"]="1"
    params["withPHY"]="1"
    params["peak_transfer_rate"]="200"
    cht[dummy3_id]=Component(dummy3_id, params)
    sht[dummy3_id+".duty_cycle"]="1.0"
    sht[dummy3_id+".total_load_perc"]="0.7"
		
    # also, add these components to the children of 
    # options.system_name (that is "system"); this should really
    # be part of step 5, but put here to have it all in one place;
    cht[options.system_name].children.append(cht[dummy1_id])
    cht[options.system_name].children.append(cht[dummy2_id])
    cht[options.system_name].children.append(cht[dummy3_id])
    

    # (b) here, I add even more dummy components, which again seem to be 
    # required by McPAT; these are BTB (branch target buffer) components
    # for each of the cores; they are inserted with default values
    # as shown in the Translator BTB;
    new_components_to_add=[]
    for id in cht:
        component = cht[id]
        if options.cpu_name in component.name: # this is a core
            # create its BTB component
            dummy_id = component.id+".BTB"
            new_params = {}
            # next BTB_config is declared with default values;
            # meanings in the BTB_config: {size, line, assoc, banks, v1, v2}
            # where the last two will be used inside McPAT to calculate:
            # throughput=v1/clockRate, latency=v2/clockRate;
            new_params["BTB_config"]="6144,4,2,1,1,3" # default values; FIX THIS
            sht[dummy_id+".read_accesses"]="0" # FIX THIS
            sht[dummy_id+".write_accesses"]="0" # FIX THIS
            new_comp=Component(dummy_id, params)
            new_components_to_add.append((dummy_id,new_comp))
            # append it to children of this core
            cht[component.id].children.append(new_comp)
    # after going thru all add the new components to cht
    for key_id, new_comp in new_components_to_add:
        cht[key_id]=new_comp
    #milad debug 4 components + params
#    for debug_id in cht:
#	if 'ruby.L2' in cht[debug_id].name:	
#	    print 'config.ini---- components: name= %s id= %s --- params= %s ---statistics= %s' %(cht[debug_id].name,cht[debug_id].id , cht[debug_id].params , cht[debug_id].statistics)
    # (5) put all the components into a tree
    createComponentTree(cht, sht)

#    #milad debug 8 print component+params+statistics 
#    for debug_id in cht:
#	if '.L1Dcache' in cht[debug_id].name:	
#	    print '8: config.ini---- components: name= %s id= %s --- params= %s --- statistics= %s' %(cht[debug_id].name,cht[debug_id].id , cht[debug_id].params , cht[debug_id].statistics)

  
    # (6) generate the intermediate xml summary.xml
    genComponentXml(cht['root'], out_file_path)
    # (7) generate the McPat power.xml
    genPowerXml(cht['root'], out_file_path_2)

def findComponentClock(cht, component_key):
    
    try:
        print_debug_message("Component Key: " + component_key)
        component_clock=cht[component_key].params['clock']
    
    except KeyError as e:
        print_debug_message("Component Key: " + component_key)
        print_debug_message("\n\nMissing 'clock' param, trying clock_domain...")
        component_clock=cht[cht[component_key].params['clk_domain']].params['clock']

    return component_clock

def calculateComponentClockRate(cht, component_key):
    clock_rate=int(1/(float( findComponentClock(cht,component_key) )*1e-6)) #f=1/T
    return clock_rate

def substituteSystemCPU(component, cpu):
    return re.sub(r'\..*', cpu, component, flags=re.IGNORECASE)



#Milad: sort XMLfile given to mcpat (mcpat supposes that its input is inorder) 
def sortXML():
        WRITE_FILE = open("./power_65nm_sorted.xml", 'w')
########### start ##############
        READ_FILE = open("./power_65nm.xml", 'r')
        write = 1
        for line in READ_FILE:
                if  (('"system.core0"' in line)):           
                         write = 0
                if write==1:                 
                        WRITE_FILE.write(line) 
########### core ##############
        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (0,10):
                    if  (('"system.core%s"'%core_number in line)):           
                         write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line) and ("</component>" in prev_line):
                        write = 0
                prev_line=line

        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (10,100):
                    if  (('"system.core%s"'%core_number in line)):
                                write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line) and ("</component>" in prev_line):
                        write = 0
                prev_line=line
########### L1Directory ##############
        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (0,10):
                    if  (('"system.L1Directory%s"'%core_number in line)):
                                write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line

        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (10,100):
                    if  (('"system.L1Directory%s"'%core_number in line)):
                                write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line
########### L2 ##############
        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (0,10):
                    if  (('"system.L2%s"'%core_number in line)):
                                write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line

        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        prev_line=""
        for line in READ_FILE:
                for core_number in range (10,100):
                    if  (('"system.L2%s"'%core_number in line)):
                                write = 1
                if write==1:                 
                        WRITE_FILE.write(line) 
                if ("</component>" in line):
                        write = 0
                prev_line=line
########### rest ##############
        READ_FILE = open("./power_65nm.xml", 'r')
        write = 0
        for line in READ_FILE:
                if  (('"system.mem"' in line)):
                        write = 1
                if write==1:                 
                        WRITE_FILE.write(line)  


############################################




    
def main ():
    global options, args
 
    # TODO: Do something more interesting here...
    if options.verbose:
        print 'm5-mcpat-parse.py'
        print '...'

    if options.tech_node=="90":
        tech_node="90"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%(tech_node)
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "90 nm Core Technology Node"
    elif options.tech_node=="65":
        tech_node="65"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%(tech_node)
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "65 nm Core Technology Node"
        
    elif options.tech_node=="45":
        tech_node="45"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%(tech_node)
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
       # options.do_vdd_scaling = True #Scale voltage for 45 nm
       # options.sys_vdd_scale = "0.90" #-10% Scale
       # I believe voltage scaling is done inside of McPAT
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "45 nm Core Technology Node"
        
    elif options.tech_node=="32":
        tech_node="32"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%(tech_node)
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
      #  options.do_vdd_scaling = True #Scale voltage for 32 nm
      #  options.sys_vdd_scale = "0.8325" #-7.5% Scale
      #  I Believe voltage scaling is done inside of McPAT
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "32 nm Core Technology Node"

    elif options.tech_node=="22":
        tech_node="22"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%("32")
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
      #  options.do_vdd_scaling = True #Scale voltage for 22 nm
      #  options.sys_vdd_scale = "0.791" #-5% Scale
      #  I believe voltage scaling is done inside of McPAT
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "22 nm Core Technology Node"
    
    elif options.tech_node=="16":
        tech_node="16"
        options.old_m5_stats = True
        options.cpu_name = "cpu"
        options.stats_fn = READ_STATS #"stats.txt"
        options.config_fn = READ_CONFIG #"config.ini"
        options.mem_tech_node = "%s"%("32")
        options.core_tech_node = "%s"%(tech_node)
        options.core_device_type = "0" #HIGH PERFORMANCE
        options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
        options.interconnect_projection_type = "0"
    #    options.do_vdd_scaling = True #Scale voltage for 16 nm
    #    options.sys_vdd_scale = "0.771" #-2.5% Scale
        options.summary_fn="summary_%snm.xml"%(tech_node)
        options.power_fn="power_%snm.xml"%(tech_node)
        print "16 nm Core Technology Node"
  # McPAT only downscales to 16 nm
  #  elif options.tech_node=="8":
  #      tech_node="8"
  #      options.old_m5_stats = True
  #      options.cpu_name = "cpu"
  #      options.stats_fn = "stats.txt"
  #      options.config_fn = "config.ini"
  #      options.mem_tech_node = "%s"%("32")
  #      options.core_tech_node = "%s"%(tech_node)
  #      options.core_device_type = "0" #HIGH PERFORMANCE
  #      options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
  #      options.interconnect_projection_type = "0"
  #      options.do_vdd_scaling = True #Scale voltage for 8 nm
  #      options.sys_vdd_scale = "0.760" #-1.5% Scale
  #      options.summary_fn="summary_%snm.xml"%(tech_node)
  #      options.power_fn="power_%snm.xml"%(tech_node)
  #      print "8 nm Core Technology Node"
        
  #  elif options.tech_node=="5":
  #      tech_node="16"
  #      options.old_m5_stats = True
  #      options.cpu_name = "cpu"
  #      options.stats_fn = "stats.txt"
  #      options.config_fn = "config.ini"
  #      options.mem_tech_node = "%s"%("32")
  #      options.core_tech_node = "%s"%(tech_node)
  #      options.core_device_type = "0" #HIGH PERFORMANCE
  #      options.cache_device_type = "0" #HIGH PERFORMANCE DEVICE TYPE
  #      options.interconnect_projection_type = "0"
  #      options.do_vdd_scaling = True #Scale voltage for 5 nm
  #      options.sys_vdd_scale = "0.752" #-1% Scale
  #      options.summary_fn="summary_%snm.xml"%(tech_node)
  #      options.power_fn="power_%snm.xml"%(tech_node)
  #      print "5 nm Core Technology Node"
    
    else:
        print "Invalid Technology Node Size"
        print "Please Choose One of the Following:"
        print "65, 45, 32, 22, or 16"
        os._exit(1)
    run()
    #added by Milad
    sortXML()


# Prints a debug message if debug is enabled

import inspect

print_debug=0

def print_debug_message(debug_message):

	"Print debug message if debug enabled"

	if (print_debug):

		print ("\n*************************\nLINE " + str(inspect.currentframe().f_back.f_lineno) + " : " + debug_message

				+ "\n*************************\n")

    
 
if __name__ == '__main__':
    try:
        start_time = time.time()
        parser = optparse.OptionParser(
                formatter=optparse.TitledHelpFormatter(),
                usage=globals()['__doc__'],
                version='TODO')
        parser.add_option ('-v', '--verbose', action='store_true',
                default=False, help='verbose output')
        parser.add_option ('-f', '--process_run_dirs_by_filter', action='store',
                default=None, help="process a series of run directories by some specificed filter string")
        parser.add_option('--old_m5_stats', action="store_true", default=False, help='processing old m5 stats')
        parser.add_option('-a', '--asisa', action='store_true', default=False, help='process asisa power')
        parser.add_option('--tech_node', action='store',default="65", help='Size of technology node')
        parser.add_option('--asisa65', action='store_true', default=False, help='process asisa power 65')
        parser.add_option('--asisa45', action='store_true', default=False, help='process asisa power 45')
        parser.add_option('--asisa32', action='store_true', default=False, help='process asisa power 32')
        parser.add_option('--asisa22', action='store_true', default=False, help='process asisa power 22')
        parser.add_option('-q', '--qualcomm', action='store_true', default=False, help='process asisa power')
        parser.add_option('-e', '--idlestudy', action='store_true', default=False, help='process idlestudy power assuming LOP circuits')
        parser.add_option('--idlestudy22_LOP', action='store_true', default=False, help='process idlestudy power assuming LOP circuits 22nm')
        parser.add_option('--idlestudy32_LOP', action='store_true', default=False, help='process idlestudy power assuming LOP circuits 32nm')
        parser.add_option('--idlestudy22_HP', action='store_true', default=False, help='process idlestudy power assuming LOP circuits 22nm')
        parser.add_option('--idlestudy32_HP', action='store_true', default=False, help='process idlestudy power assuming LOP circuits 32nm')
        parser.add_option('--idlestudy2', action='store_true', default=False, help='process idlestudy power assuming HP circuits')
        # Alex: cpu_name changed here to work with "cpu" that is 
        # used inside GEM5's output files;
        parser.add_option('-c', '--cpu_name', action='store', type='string', default="cpu", help="the string used cpu comparisons") 
        parser.add_option('-s', '--stats_fn', action='store', type='string', default='stats.txt', help="the name of the stats file to use")
        parser.add_option('-C', '--config_fn', action='store', type='string', default='config.ini', help="the name of the config file to use")
        # cris: ruby stats file name; I should use these
        # file names to run mutiple benchmarks in parallel;
        parser.add_option('-r', '--ruby_fn', action='store', type='string', default='ruby.stats', help="the name of the Ruby stats file to use.") 
        parser.add_option('-F', '--output_dir', action='store', type='string', default='m5out', help="name of Folder with gem5 output files: stats, config, ruby.")
        parser.add_option('-y', '--summary_fn', action='store', type='string', default='summary_gem5.xml', help="the name of the summary output file name")
        parser.add_option('-p', '--power_fn', action='store', type='string', default='power_gem5.xml', help="the name of the summary output file name")
        parser.add_option('-S', '--system_name', action='store', type='string', default='system', help="the name the system we are consider for stats")
        parser.add_option('-l', '--l1_cache_cpu_name', action='store', type='string', default='cpu', help="the name of the cpu to which the l1 dcache and icache were first attached")
        parser.add_option('-i', '--itb_name', action='store', type='string', default='itb', help="The name associated with M5's itb")
        parser.add_option('-d', '--dtb_name', action='store', type='string', default='dtb', help="The name associated with M5's dtb")
        parser.add_option('-I', '--interconn_names', action='store', type='string', default='tol2bus,0.5', help="The name of the interconnects to consider")
        parser.add_option('-m', '--mem_tech_node', action='store', type='string', default='32', help="The technology node of the memory")
        parser.add_option('-t', '--core_tech_node', action='store', type='string', default='32', help="The technology node of the core")
        parser.add_option('-D', '--core_device_type', action='store', type='string', default='0', help="The core device type: 0=High Performance,1=Low Standby Power,2=Low Operating Power")
        parser.add_option('-E', '--cache_device_type', action='store', type='string', default='0', help="The cache device type: 0=High Performance,1=Low Standby Power,2=Low Operating Power")
        parser.add_option('-P', '--interconnect_projection_type', action='store', type='string', default='0', help="The cache device type: 0=High Performance,1=Low Standby Power,2=Low Operating Power")
        parser.add_option('--sys_vdd_scale', action='store', type='string', default=None, help="The amount to scale vdd by in the system.")
    #    parser.add_option('--frequency', action='store', type='string', default='2000', help="Frequency of the core")
        parser.add_option('--do_vdd_scaling', action='store_true', default=False, help="The amount to scale vdd by in the system.")
       # parser.add_options('-N', '--num_cores', action='store', type='int', default=1, help="The number of cores that must be processed.")
        (options, args) = parser.parse_args()
        if options.verbose: print time.asctime()
        exit_code = main()
        if exit_code is None:
            exit_code = 0
        if options.verbose: print time.asctime()
        if options.verbose: print 'TOTAL TIME IN MINUTES:',
        if options.verbose: print (time.time() - start_time) / 60.0
        sys.exit(exit_code)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        raise e
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        os._exit(1)

########################################################

