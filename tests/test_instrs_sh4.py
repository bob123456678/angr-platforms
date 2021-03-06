#!/usr/bin/python
import re
from angr_platforms.sh4 import *

"""
Test our lifter against objdump's disassembly
Input: a objdump -D text file
Author: bob123456678
Language: python 2.7

For each instruction, it prints:
-instruction bytes
-vex irsb
-our disassembly
-objdump's disassembly
"""

# Reads an objdump file, gets all instructions from non-system code segments
def readObjdump(fn):

    f = open(fn)

    relevantInstrs = {}
    relevantNames = set()

    skip = True

    for line in f:

        if re.search('^[0-9a-f]{8} <.+>:$', line):
            if "<." in line or "_GLOBAL" in line or "_DYNAMIC" in line:
                skip = True
                #print("SKIPPING " + line)
            else:
                skip = False
                #print("NOT SKIPPING " + line)
        elif not skip:

            m = re.search('^\s*([0-9a-f]{6}):\s+([0-9a-f]{2}) ([0-9a-f]{2})\s+([a-z/\.]+)\s+([^!]+).*$', line)
            if m:

                if ".word" not in line:
	
                    # If the disassembler gave us an operand address, extract it.
                    e = re.search('([0-9a-f]{6})', m.group(5))
					
                    if e:
                    	extractAddress = e.group(1)
                    else:
                    	extractAddress = ''
				
                    relevantInstrs[m.group(2)+m.group(3)] = {
                        'addr'  : m.group(1),
                        'byte0' : m.group(2),
                        'byte1' : m.group(3),
                        'name'  : m.group(4).strip(),
                        'desc'  : m.group(5).strip(),
						'xtrc'	: extractAddress
                    }
                    relevantNames.add(m.group(4).strip())
                
                    #print("%s : %s %s (%s %s)" % (m.group(1), m.group(2),m.group(3), m.group(4).strip(), m.group(5).strip()))

    print("Loaded %s unique instructions of %s types" % (len(relevantInstrs), len(relevantNames)))

    return relevantInstrs
	
"""
Lift an arbitrary instruction (up to 4 bytes if delayed branch)	
"""
def test_lift_one(instr):	

	l = helpers_sh4.LifterSH4(arch_sh4.ArchSH4(), 0, instr, revBytes=False, max_bytes=4)
	
	return l.irsb
	#.pp()
	
# run comparisongs
if __name__ == '__main__':

	# Instructions that we previously tested
	# skip = ['MOVLS','SETT','TST','JSR','MOVT','CMPPZ','XOR','MOVBL4','NEGC','MOVWL','MOVBL','AND','SHAR','STSFPUL','SUB','MOVLL','CMPHS','MOVW','JMP','NOP','MOVBS4','MOVBL0','MOVWS0','CMPHI','CMPEQ','SUBC','MOVBS','MOVBL0','LDSFPUL','MOVBS0','RTS','MOV','ADD','MOVLI','SHLL','MOVLS4','BF','BT','MOVLL4','EXTS','ADDI', 'CMPGT','MOVI','BRA','FLDS','LDSLPR','MOVLM','FSTS','MOVLP','STSLPR','MOVBSG']
	skip = []
	
	seen = set()
	step = True if raw_input("Step (y/n)?") == "y" else False

	for instruction in readObjdump('./test_programs/sh4/disasm.txt').values():

		try:
			instr = instruction['byte0'] + instruction['byte1']

			isDelayed = instruction['name'] in ('bra','rts','jmp','jsr')
			irsb = test_lift_one(instr.decode('hex'))
			cls = str(arch_sh4.ArchSH4.LAST_LIFTED_INSTR.__class__).split('_')[-1][:-2]

			if cls in skip:
				continue
				
			seen.add(cls)
			
			if isDelayed:
				# Add a nop after delayed branch, and get the new vex
				disasm = arch_sh4.ArchSH4.LAST_LIFTED_INSTR.disassemble()
				instr += "0900"
				irsb = test_lift_one(instr.decode('hex'))
				cls += ',' + str(arch_sh4.ArchSH4.LAST_LIFTED_INSTR.__class__).split('_')[-1][:-2]

			print("Instruction of class %s with bytes %s" % (cls, instr))

			irsb.pp()
			
			# Otherwise the regs will get fetched again and printed erroneously in the vex
			if not isDelayed:
				disasm = arch_sh4.ArchSH4.LAST_LIFTED_INSTR.disassemble()

			print(disasm)
			
			# Calculate offset, to make verification easier
			if instruction['xtrc']:
				diff = int(instruction['xtrc'],16) - int(instruction['addr'],16)
				diff = ' (offset=' + str(diff) + ')'
			else:
				diff = ''
				
			print(instruction['name'] + ' ' + instruction['desc'] + ' @ ' + instruction['addr'] + diff)
			print("=" * 50)
			
			if step:
				c = raw_input("Press enter to continue to next...")
				if c == "c":
					step = False
					
		except Exception as e:
		
			print(e)
			print("ERROR decoding instruction at %s!" % instruction['addr'])
			break

	print("Lifted the following %s instruction classes: " % len(seen))
	print(sorted(seen))
	
# This is how you would manually test one instruction
#test_lift_one("\x11\x2f").pp()
#test_lift_one("\x08\x2f").pp()