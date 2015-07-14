'''
ramdisk.py:
A tool for creating and mounting temporary filesystems on Linux.
Can use tmpfs or ramfs, and checks for compatibility before setting up any filesystems.
'''
import sys, os, subprocess
# Create a flags class to store variables in.
class Flags:
	supports_ramfs = False
	supports_tmpfs = False
	is_root = False
	mem_free = 0
	hr_mem_free = "0MB"

# Create a class that contains all the ANSI colour codes we need.
class ANSI:
	reset = '\033[0m'
	yelw = '\033[93m'
	green = '\033[92m'
	red = '\033[91m'

# Function to extract free memory in kB from /proc/meminfo and return it.
def get_free_memory():
	meminfo = open("/proc/meminfo").read()
	memfree = 0
	memfree_detected = False
	for line in meminfo.split():
		if memfree_detected:
			memfree = int(line)
			break
		if 'MemFree' in line:
			memfree_detected = True
	return memfree

# Function to reset the ANSI colours upon exit.
def exit():
	print(ANSI.reset, end="")
	sys.exit(0)

# Function to initialise all the values in the Flags class.
# Checks system compatibility and permissions before starting.
def initialise():
	try:
		# Make everything yellow!
		print(ANSI.yelw)
		# Check if the host is running Linux - this utility is written against it
		print("Initialising ramdisk tool.\n\nChecking the host system is linux... ", end="")
		if not sys.platform == "linux":
			# if not, tell the user and exit.
			print("\n" + ANSI.red + "This operating system is not supported. Sorry!")
			exit()
		# Check for root access.
		print("\nChecking if this script is running as root... ", end="")
		# If UID=0 for the current user (as it should be if you're root):
		if os.geteuid() == 0:
			print("it is.")
			# Remember we're root for the rest of the session.
			Flags.is_root = True
		# If not:
		else:
			print(ANSI.red + "it isn't.\n" + ANSI.yelw)
			# Ask the user if they want to continue as a non-root user.
			tmp = input("Running as a non-root user may result in permission errors.\nContinue?(Y/n): ")
			if tmp.lower() != "y":
				print(ANSI.red + "Okay, quitting. Try running with sudo.")
				exit()
			else:
				print("Okay, suit yourself.")
				Flags.is_root = False
		# Check /proc/filesystems and see if it contains "tmpfs".
		# If it does, we can reasonably assume the system supports tmpfs.
		# Sets flags accordingly.
		print("Checking if this system supports tmpfs... ", end="")
		try:
			if "tmpfs" in open("/proc/filesystems").read():
				print("it does.")
				Flags.supports_tmpfs = True
			else:
				print(ANSI.red + "it doesn't." + ANSI.yelw)
				Flags.supports_tmpfs = False
		# If an error occurs trying to read /proc/filesystems, tell the user what happened and exit.
		except IOError as ioe:
			if ioe[0] == errno.EPERM:
				print(ANSI.red + "\nYou don't have permission to read /proc/filesystems. Exiting.")
				exit()
			else:
				print(ANSI.red + "\nA general exception occurred while reading /proc/filesystems. Exiting.")
				exit()
		# Check /proc/filesystems and see if it contains "ramfs".
		# If it does, we can reasonably assume the system supports ramfs.
		# Sets flags accordingly.
		print("Checking if this system supports ramfs... ", end="")
		try:
			if "ramfs" in open("/proc/filesystems").read():
				print("it does.\n")
				Flags.supports_ramfs = True
			else:
				print(ANSI.red + "it doesn't.\n" + ANSI.yelw)
				Flags.supports_ramfs = False
		# If an error occurs trying to read /proc/filesystems, tell the user what happened and exit.
		except IOError as ioe:
			if ioe[0] == errno.EPERM:
				print(ANSI.red + "\nYou don't have permission to read /proc/filesystems. Exiting.")
				exit()
			else:
				print(ANSI.red + "\nA general exception occurred while reading /proc/filesystems. Exiting.")
				exit()
		# If neither ramfs or tmpfs is supported, tell the user and exit.
		if not Flags.supports_ramfs and not Flags.supports_tmpfs:
			print(ANSI.red + "Your system supports neither ramfs nor tmpfs.\nPlease rectify this before using this script.")
			exit()
		# Detect the amount of free memory left on the system.
		print("Detecting free memory...")
		# Create an integer containing the free memory, and generate a human-readable string for use throughout the interface.
		Flags.mem_free = get_free_memory()
		Flags.hr_mem_free = str(round(Flags.mem_free / 1000)) + "MB"
		print("You have " + Flags.hr_mem_free + " free memory.\n")
		user_interface()
	except KeyboardInterrupt:
		exit()

# Updates the integer and human-readable mem-free values.
def update_free_memory():
	Flags.mem_free = get_free_memory()
	Flags.hr_mem_free = str(round(Flags.mem_free / 1000)) + "MB"

# Actually runs the shell commands.
def create_ramdisk(fs_type, fs_mountpoint, fs_size):
	print("*** Creating ramdisk ***")
	# First, update the free memory values to ensure they are up-to-date.
	update_free_memory()
	# Convert fs_size to an integer if need be.
	if fs_size is not int:
		try:
			fs_size = int(fs_size)
		except TypeError:
			print(ANSI.red + "You must enter an integer as the size." + ANSI.green)
			return
	# Check that the user isn't trying to create a ramdisk larger than they have free RAM:
	if fs_size * 1000 > Flags.mem_free:
		print(ANSI.red + "Creating this ramdisk would use up more system memory than you have free.")
		print("Your free memory: " + Flags.hr_mem_free)
		print("Size of the ramdisk: " + str(fs_size) + "M" + ANSI.green)
		return
	# Check that the user isn't trying to select a filesystem that is not supported by their system.
	if (fs_type == "tmpfs" and not Flags.supports_tmpfs) or (fs_type == "ramfs" and not Flags.supports_ramfs):
		print(ANSI.red + "You specified " + fs_type + ", which your system does not support. Stopping." + ANSI.green)
		return
	# Check that the mountpoint exists, and if not, create it.
	if not os.path.exists(fs_mountpoint):
		print("Your mountpoint " + fs_mountpoint + " does not exist. Creating.")
		try:
			os.makedirs(fs_mountpoint)
		except OSError as ose:
			if ose.errno == errno.EACCES:
				print(ANSI.red + "Access denied: " + fs_mountpoint + "\nCheck permissions or run as root and retry." + ANSI.green)
			else:
				print(ANSI.red + "A general exception occurred while creating the mountpoint:\n" + fs_mountpoint + ANSI.green)
			return
	# If the user selecs ramfs, warn them about ramfs' dynamic allocation nature.
	if fs_type == "ramfs":
		print(ANSI.red + "NOTE: ramfs will dynamically allocate more memory to itself if you fill it.\nThis can cause your system to hang if it eventually runs out of memory.\n" + ANSI.green)
	# Generate the command.
	cmd = "mount -t " + fs_type + " -o size=" + str(fs_size) + "M " + fs_type + " " + fs_mountpoint
	print(ANSI.yelw + "Executing command:\n" + cmd + ANSI.green)
	tmp = None
	# Execute the command.
	try:
		tmp = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError:
		print(ANSI.red + "An error occurred while creating the ramdisk.\nHere is the output of the mount command:\n" + str(tmp) + ANSI.green)
		return
	print(ANSI.green + "The ramdisk was created successfully and is mounted at this path:\n" + fs_mountpoint + "\nYou can unmount it by running this command:\nsudo umount -f " + fs_mountpoint)
# Function to unmount a ramdisk
'''
Requirements:
	Lists currently mounted ramdisks, their mount points, their size and their type.
	Allows the user to unmount a ramdisk, with error checking.
'''

# User interface function.
def user_interface():
	print(ANSI.green)
	while True:
		print("ramdisk.py by tobycode.")
		print("1) create a ramdisk")
		print("\nx) exit")
		tmp = input(">>>")
		if tmp.lower() == "1":
			create_ramdisk(input("tmpfs or ramfs?\n>>>"), input("Where should the ramdisk be mounted?\n>>>"), input("How large should the ramdisk be (in MB)?\n>>>"))
		else:
			exit()

initialise()