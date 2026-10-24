"""
20171107:	This short script automatically creates the daily used folders and files, which we used to do manually everyday.
		As long as the file names and directories have not been modified, all one needs to change is the "Date".
20171211:	Add processing DDSpostcool.py in DDSFolder
20171218:	Transfer DropBox folder to PSUBox folder
20180730:	Add Phasescan.py in DDSFolder
20191119: 	Add CopyLog to copy the log from CameraFolder to PSUBoxFolder & rename existing log2.txt w/ timestamp
20191209:  Add DDSarb.py in DDSFolder
20260710:  Refactor DDS file copying into a loop over a filename list, skip
           (instead of crash on) files missing from the source folder, and
           add Coolscan.py to the copied files
20260713:  Auto-populate the new log.txt (date, MOT/OP/EO zeros lines carried
           forward from the most recent previous log, and the column header)
           instead of creating a blank file
20260714:  Carry forward freeform notes too: any lines typed between the EO
           zeros line and the header in the previous log are copied verbatim
           into the new log, grouped under the MOT/OP/EO zeros lines
20260714b: Date is now computed from the system clock instead of hardcoded,
           so the script always targets the day it's run on
20260714c: DirectoryCamera and DirectoryDDS are now derived from this file's
           own location instead of a hardcoded drive letter/username, since
           CameraControl and DDScontrol are always sibling folders. PSUBox
           lives in an unrelated Box Sync tree and stays a fixed path.
20260904:  The DDS GUI (DDScontrol/WeissDDS/Freq-Scan-GUI, replaces the
           Freqscan/Powerscan/... scripts) works in this same dated DDS
           folder: its pulse files and run files overwrite themselves there
           and its dds_log.txt records every compile / run / calibration
           change with the time. New step: snapshot the GUI's calibration
           state (f4new, trims, pi cals, panel defaults, session) into
           <DDS folder>/gui-state-at-start/ plus the GUI's git commit, once
           per day, so the day's changes can be read against its starting
           point. The GUI creates the dated folder itself when it starts
           before this script has run; the snapshot step still works then.
20261023:  DDS scripts are seeded per file: each one missing from today's DDS
           folder is copied from the most recent day folder that has it, also
           when today's folder already exists (the DDS GUI may have made it);
           files already there are never overwritten. Before, the search
           stopped at the first dated folder, so a GUI-made folder (GUI-only
           files) dropped all 15 scripts from every later day.
"""

import sys,math,csv,os,subprocess
import re       # for extracting the parenthesized field values from log lines
import shutil   # use for file copying
import datetime as dt # for manipulating timestamp


Date = dt.datetime.now().strftime("%Y%m%d")

# CameraControl (this script's own folder) and DDScontrol are always sibling
# folders on the lab PC, so derive both from this file's location instead of
# hardcoding the drive letter and username
ScriptDirectory  = os.path.dirname(os.path.abspath(__file__))
DirectoryCamera  = ScriptDirectory
DirectoryDDS      = os.path.join(os.path.dirname(ScriptDirectory),'DDScontrol')
#~ DirectoryDropBox = 'C:/Users/Yang/Dropbox/QC Lab - XLZ/'  # officially transferred to PSU Box on 20171218
DirectoryPSUBox  = 'C:/Users/Yang/Box Sync/b-weisslabs Shared/Quantum Computing/QC Lab - XLZ/'  # separate Box Sync tree, not derivable from this file's location
PathToSciTE       = 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Scintilla Text Editor\SciTE.lnk'
CreateCameraFolder = 		1
CreateDDSFolder = 		1
#~ CreateDropBoxFolder = 		1
CreatePSUBoxFolder = 		1

CopyLog                 =          0

CameraFolder =	os.path.join(DirectoryCamera,Date)
DDSFolder = 	os.path.join(DirectoryDDS,Date)
#~ DropBoxFolder =	os.path.join(DirectoryDropBox,Date)
PSUBoxFolder = 	os.path.join(DirectoryPSUBox,Date)

LogFile  = 		os.path.join(CameraFolder+"/log.txt")

# DDS scripts to seed each new day's folder with, copied from the most
# recent existing DDS folder. Add new filenames here as scripts are added.
DDSFileNames = [
	"Freqscan.py",
	"Freqscan2.py",
	"Freqscan-RF.py",
	"Cool_Cal.py",
	"Coolscan.py",
	"Rabi.py",
	"Rabi-RF.py",
	"DDScool.py",
	"DDSaddress.py",
	"DDSpostcool.py",
	"Phasescan.py",
	"Phasescan-RF.py",
	"DDSarb.py",
	"Powerscan.py",
	"Powerscan-RF.py",
]

# lines carried forward from the previous day's log, and the reusable header
LogCarryForwardLabels = ["MOT", "OP", "EO zeros"]
LogHeader = "#\tLV\t\tLH\t\tRV\t\tRH\t\tResult"

def CarryForwardLine(line):
	"""Rewrite a "label (old values) --> (final values)" log line so that the
	final values (the last parenthesized group) become both value groups for
	the new day. Label formatting, arrow style, and any text after the last
	parenthesis are preserved."""
	line = line.rstrip("\n")
	groups = re.findall(r"\([^)]*\)", line)
	if not groups:
		return line
	final = groups[-1]
	prefix = line[:line.index("(")]
	suffix = line[line.rindex(")")+1:]
	arrow = " ---> " if "--->" in line else " --> "
	return prefix + final + arrow + final + suffix

def PopulateLogFile(logFile):
	"""Write the beginning of a new day's log: the date, the MOT/OP/EO zeros
	lines initialized from the previous day's final values, and the header."""
	# find the most recent previous log.txt, searching back day by day
	NumberOfDate = 90
	Base = dt.datetime.strptime(Date,"%Y%m%d")
	prevLogFile = None
	for counter in range(1,NumberOfDate):
		OlderDate = (Base - dt.timedelta(days=counter)).strftime("%Y%m%d")
		candidate = os.path.join(DirectoryCamera,OlderDate,"log.txt")
		if os.path.isfile(candidate):
			prevLogFile = candidate
			print ("	log.txt initialized from "+OlderDate+" log")
			break

	lines = [Date]
	if prevLogFile is not None:
		with open(prevLogFile) as f:
			prevLines = f.readlines()

		# carry forward the MOT/OP/EO zeros lines, tracking the last one found
		# so we know where the freeform notes below them start
		lastFieldIndex = 0
		for label in LogCarryForwardLabels:
			matchIndex = next((i for i,l in enumerate(prevLines) if l.strip().startswith(label) and "(" in l), None)
			if matchIndex is not None:
				lines.append(CarryForwardLine(prevLines[matchIndex]))
				lastFieldIndex = max(lastFieldIndex,matchIndex+1)
			else:
				print ("	"+label+" line not found in previous log, skipped")

		# carry forward any freeform notes between the last field line and the
		# header, so running notes persist day to day until removed
		headerIndex = next((i for i,l in enumerate(prevLines) if l.rstrip("\n") == LogHeader), None)
		if headerIndex is not None:
			notes = [l.rstrip("\n") for l in prevLines[lastFieldIndex:headerIndex] if l.strip() != ""]
			lines.extend(notes)
		else:
			print ("	Header line not found in previous log, no notes carried forward")
	else:
		print ("	No recent log.txt found within "+str(NumberOfDate)+" days, only date and header written")
	lines.append(LogHeader)
	with open(logFile,'w') as f:
		f.write("\n".join(lines)+"\n\n")

# create an empty folder for Camera program data
if (CreateCameraFolder == 1 and not os.path.isdir(CameraFolder)):
	os.makedirs(CameraFolder)		
	print (Date+" Camera Folder created")
	PopulateLogFile(LogFile)		# create log.txt pre-filled with the date, carried-forward field lines, and header
	os.startfile(CameraFolder)		# open the Camera folder to drag log.txt to here
elif (CreateCameraFolder == 0):
	print ("CreateCameraFolder = 0")
else:
	print (Date+" Camera Folder already exists")


# create the folder for DDS files, and seed it with the DDS scripts
if (CreateDDSFolder ==1):
	if not os.path.isdir(DDSFolder):
		os.makedirs(DDSFolder)
		print (Date+" DDS Folder created")
	else:
		print (Date+" DDS Folder already exists")	# e.g. the DDS GUI made it first; still seed it below

	# each script missing from today's folder is copied from the most recent
	# day folder that has that script, searching back up to NumberOfDate days.
	# Per file, not per folder: since 2026-09-04 the DDS GUI makes day folders
	# with only its own files, and a folder-level search stopped at those.
	# A script already in today's folder is never overwritten.
	NumberOfDate = 90
	Base = dt.datetime.strptime(Date,"%Y%m%d")
	NumberSeeded = 0
	for fileName in DDSFileNames:
		dstFile = os.path.join(DDSFolder,fileName)
		if os.path.isfile(dstFile):
			continue
		srcFile = None
		for counter in range(1,NumberOfDate):
			OlderDate = (Base - dt.timedelta(days=counter)).strftime("%Y%m%d")
			candidate = os.path.join(DirectoryDDS,OlderDate,fileName)
			if os.path.isfile(candidate):
				srcFile = candidate
				break
		if srcFile is not None:
			shutil.copyfile(srcFile,dstFile)
			NumberSeeded += 1
			print ("	"+fileName+" copied from "+OlderDate+" DDS Folder")
		else:
			print ("	"+fileName+" not found in any DDS Folder of the last "+str(NumberOfDate)+" days, skipped")
	if (NumberSeeded > 0):
		os.startfile(DDSFolder)		# open the DDS folder to drag DDS files to here
elif (CreateDDSFolder == 0):
	print ("CreateDDSFolder = 0")


# snapshot the DDS GUI's calibration state into the day's DDS folder (once
# per day; the GUI itself logs the day's changes to <DDS folder>\dds_log.txt)
GUIDirectory = os.path.join(DirectoryDDS,'WeissDDS','Freq-Scan-GUI')
GUIStateFiles = [
	"f4new.npy",            # the measured carrier
	"freq_offset.npy",      # per-transition frequency trims
	"transition_cal.json",  # pi powers/lengths per pulse type
	"panel_config.ini",     # panel defaults
	"session_state.json",   # sequences in the editor + library
	"type_memory.json",     # per-type length/power/HSR memory
]
SnapshotGUIState = 	1

def GUIVersion(gitDirectory):
	"""The GUI's git commit (short hash + branch), read from .git without
	needing git on the PATH; '' when it cannot be read."""
	try:
		with open(os.path.join(gitDirectory,"HEAD")) as f:
			head = f.read().strip()
		if head.startswith("ref: "):
			ref = head[5:]
			refFile = os.path.join(gitDirectory,*ref.split("/"))
			if os.path.isfile(refFile):
				with open(refFile) as f:
					return f.read().strip()[:7]+" ("+ref.split("/")[-1]+")"
			packed = os.path.join(gitDirectory,"packed-refs")
			if os.path.isfile(packed):
				with open(packed) as f:
					for line in f:
						parts = line.split()
						if len(parts) == 2 and parts[1] == ref:
							return parts[0][:7]+" ("+ref.split("/")[-1]+")"
			return ""
		return head[:7]
	except (IOError,OSError):
		return ""

if (SnapshotGUIState == 1 and os.path.isdir(GUIDirectory) and os.path.isdir(DDSFolder)):
	StateFolder = os.path.join(DDSFolder,"gui-state-at-start")
	if not os.path.isdir(StateFolder):
		os.makedirs(StateFolder)
		for fileName in GUIStateFiles:
			srcFile = os.path.join(GUIDirectory,"variables",fileName)
			if os.path.isfile(srcFile):
				shutil.copyfile(srcFile,os.path.join(StateFolder,fileName))
			else:
				print ("	"+fileName+" not present in the GUI's variables folder, skipped")
		with open(os.path.join(StateFolder,"gui-version.txt"),"w") as f:
			f.write("Freq-Scan-GUI "+(GUIVersion(os.path.join(GUIDirectory,".git")) or "(version unknown)")+"\n")
			f.write("state copied "+dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
		print (Date+" GUI calibration state snapshotted to gui-state-at-start")
	else:
		print (Date+" GUI state snapshot already exists")
elif (SnapshotGUIState == 0):
	print ("SnapshotGUIState = 0")
elif not os.path.isdir(GUIDirectory):
	print ("DDS GUI not found at "+GUIDirectory+", no state snapshot")


#~ # create an empty folder on DropBox
#~ if (CreateDropBoxFolder == 1 and not os.path.isdir(DropBoxFolder)):
	#~ os.makedirs(DropBoxFolder)		
	#~ print (Date+" DropBox Folder created")
	#~ os.startfile(DropBoxFolder)		# open the DropBox folder but no need
#~ elif (CreateDropBoxFolder == 0):
	#~ print ("CreateDropBoxFolder = 0")
#~ else:
	#~ print (Date+" DropBox Folder already exists")
	
# create an empty folder on PSUBox 
if (CreatePSUBoxFolder == 1 and not os.path.isdir(PSUBoxFolder)):
	os.makedirs(PSUBoxFolder)		
	print (Date+" PSUBox Folder created")
	os.startfile(PSUBoxFolder)		# open the PSUBox folder but no need
elif (CreatePSUBoxFolder == 0):
	print ("CreatePSUBoxFolder = 0")
else:
	print (Date+" PSUBox Folder already exists")	
	
	
# copy the log file from CameraFolder to PSUBoxFolder
if (CopyLog == 1):
	timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
	scr_file = os.path.join(CameraFolder+"/log.txt")
	dst_file = os.path.join(PSUBoxFolder+"/log2.txt")
	if os.path.isfile(dst_file):
		dst_backup_file = os.path.join(PSUBoxFolder+"/log2_"+timestamp+".txt")
		os.rename(dst_file,dst_backup_file)
	shutil.copyfile(scr_file,dst_file)
	print (Date+" log file copied to PSUBoxFolder")


#~ os.startfile(DropBoxFolder)
#~ os.startfile(PSUBoxFolder)
#~ os.startfile(DDSFolder)
#~ os.startfile(CameraFolder)

# TODO: Life will be easier if the files can be automatically opened in SciTE instead of being manually dragged to here
#~ subprocess.call([PathToSciTE, LogFile,], shell=True)

