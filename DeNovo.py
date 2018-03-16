#!/usr/bin/python3

import os , re , time , datetime , random , requests , urllib.request , bs4 , math , Bio.PDB , numpy
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pyrosetta import *
from pyrosetta.toolbox import *
init()
#--------------------------------------------------------------------------------------------------------------------------------------
#Functions
def SASA(pose):
	''' Calculates the different layers (Surface, Boundery, Core) of a structure according its SASA (solvent-accessible surface area) '''
	''' Returns three lists Surface amino acids = [0] , Boundery amino acids = [1] , Core amino acids = [2] '''
	#Temporary generate a .pdb file of the pose to isolate the layers since it is not yet possible to do that using a Rosetta pose, this temporary .pdb file will be deleted after the layers are found
	pose.dump_pdb('ToDesign.pdb')
	#Standard script to setup biopython's DSSP to calculate SASA using Wilke constants
	parser = Bio.PDB.PDBParser()
	structure = parser.get_structure('X' , 'ToDesign.pdb')
	model = structure[0]
	dssp = Bio.PDB.DSSP(model , 'ToDesign.pdb' , acc_array = 'Wilke')
	#Loop to get SASA for each amino acid
	lis = list()
	count = 0
	for x in dssp:
		if x[1]=='A' : sasa=129*(x[3])
		elif x[1]=='V' : sasa=174*(x[3])
		elif x[1]=='I' : sasa=197*(x[3])
		elif x[1]=='L' : sasa=201*(x[3])
		elif x[1]=='M' : sasa=224*(x[3])
		elif x[1]=='P' : sasa=159*(x[3])
		elif x[1]=='Y' : sasa=263*(x[3])
		elif x[1]=='F' : sasa=240*(x[3])
		elif x[1]=='W' : sasa=285*(x[3])
		elif x[1]=='R' : sasa=274*(x[3])
		elif x[1]=='C' : sasa=167*(x[3])
		elif x[1]=='N' : sasa=195*(x[3])
		elif x[1]=='Q' : sasa=225*(x[3])
		elif x[1]=='E' : sasa=223*(x[3])
		elif x[1]=='G' : sasa=104*(x[3])
		elif x[1]=='H' : sasa=224*(x[3])
		elif x[1]=='K' : sasa=236*(x[3])
		elif x[1]=='S' : sasa=155*(x[3])
		elif x[1]=='T' : sasa=172*(x[3])
		elif x[1]=='D' : sasa=193*(x[3])
		lis.append((x[2] , sasa))
	#Label each amino acid depending on its SASA position according to the parameters highlighted in the paper by (Koga et.al., 2012 - PMID: 23135467). The parameters are as follows:
	#Surface:	Helix or Sheet: SASA => 60		Loop: SASA => 40
	#Boundry:	Helix or Sheet: 15 < SASA < 60		Loop: 25 < SASA < 40
	#Core:		Helix or Sheet: SASA =< 15		Loop: SASA =< 25	
	surface = list()
	boundery = list()
	core = list()
	count = 0
	for x , y in lis:
		count = count + 1
		if y <= 25 and (x == '-' or x == 'T' or x == 'S'):		#Loop (DSSP code is - or T or S)
			core.append(count)
		elif 25 < y < 40 and (x == '-' or x == 'T' or x == 'S'):	#Loop (DSSP code is - or T or S)
			boundery.append(count)
		elif y >= 40 and (x == '-' or x == 'T' or x == 'S'):		#Loop (DSSP code is - or T or S)
			surface.append(count)
		elif y <= 15 and (x == 'G' or x == 'H' or x == 'I'):		#Helix (DSSP code is G or H or I)
			core.append(count)
		elif 15 < y < 60 and (x == 'G' or x == 'H' or x == 'I'):	#Helix (DSSP code is G or H or I)
			boundery.append(count)
		elif y >= 60 and (x == 'G' or x == 'H' or x == 'I'):		#Helix (DSSP code is G or H or I)
			surface.append(count)
		elif y <= 15 and (x == 'B' or x == 'E'):			#Sheet (DSSP code is B or E)
			core.append(count)
		elif 15 < y < 60 and (x == 'B' or x == 'E'):			#Sheet (DSSP code is B or E)
			boundery.append(count)
		elif y >= 60 and (x == 'B' or x == 'E'):			#Sheet (DSSP code is B or E)
			surface.append(count)	
	os.remove('ToDesign.pdb')						#Keep working directory clean
	return(surface , boundery , core)					#Return values [0] = Motif_From [1] = Motif_To

class Design():
	def Whole(Pose):
		''' Applies RosettaDesign to change the whole structure's amino acids (the whole structure all at once) while maintaining the same backbone '''
		''' Generates the DesignedWhole.pdb file '''
		pose = pose_from_pdb(Pose)
		#A - Relax original structure
		scorefxn = get_fa_scorefxn()
		score1_original_before_relax = scorefxn(pose)			#Measure score before relaxing
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		relax.apply(pose)
		score2_original_after_relax = scorefxn(pose)			#Measure score after relaxing
		#B - Preform RosettaDesign for whole structure
		for inter in range(3):
			task_pack = standard_packer_task(pose)
			pack_mover = pyrosetta.rosetta.protocols.minimization_packing.PackRotamersMover(scorefxn, task_pack)
			pack_mover.apply(pose)
			#C - Relax Pose
			relax.apply(pose)
		#D - Output Result
		score3_of_design_after_relax = scorefxn(pose)			#Measure score of designed pose
		pose.dump_pdb('DesignedWhole.pdb')				#Export final pose into a .pdb structure file
		print(score1_original_before_relax)
		print(score2_original_after_relax)
		print(score3_of_design_after_relax)

	def Pack(Pose):
		''' Applies FastDesign to change the whole structure's amino acids (one layer at a time as well as designing towards an optimally packed core) while maintaining the same backbone. Should be faster than the Whole method and results in a better final structure than the Layer method '''
		''' Generates the Designed.pdb file '''
		pose = pose_from_pdb(Pose)
		#A - Relax original structure
		scorefxn = get_fa_scorefxn()
		score1_original_before_relax = scorefxn(pose)			#Measure score before relaxing
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		relax.apply(pose)
		score2_original_after_relax = scorefxn(pose)			#Measure score after relaxing
		#B - FastDesign protocol					#Uses Generic Monte Carlo with PackStat as a filter to direct FastDesign towards an optimally packed structure core
		chain = pose.pdb_info().chain(1)				#Identify chain
		layers = [2 , 1 , 0]						#Layer Identity from SASA Surface = [0] , Boundary = [1] , Core = [2]
		for identity in layers:						#Loop through each layer
			#1 - Setup the PackStat filter
			filters = rosetta.protocols.simple_filters.PackStatFilter()
			#2 - Identify The Layers
			sasa = SASA(pose)					#Re-calculate SASA every time because amino acid position can change from one layer to another during the design phase, therefore make sure to design the layer not the amino acid
			layer = sasa[identity]					#Changes every iteration to start with Core (sasa[2]) then Boundary (sasa[1]) then Surface (sasa[0])
			#3 - Generate the resfile				#Will generate a new Resfile for each layer (which is why it is deleted at the end of the loop)
			Resfile = open('Resfile.resfile' , 'w')
			Resfile.write('NATAA\n')
			Resfile.write('start\n')
			for line in layer:
				Resfile.write(str(line) + ' ' + chain + ' ALLAA\n')
			Resfile.close()
			#4 - Setup the FastDesign mover
			read = pyrosetta.rosetta.core.pack.task.operation.ReadResfile('Resfile.resfile')	#Call the generated Resfile
			task = pyrosetta.rosetta.core.pack.task.TaskFactory()					#Setup the TaskFactory
			task.push_back(read)									#Add the Resfile to the TaskFactory
			movemap = MoveMap()									#Setup the MoveMap
			movemap.set_bb(True)									#Do not change the phi and psi BackBone angles
			movemap.set_chi(True)									#Change the chi Side Chain angle
			mover = pyrosetta.rosetta.protocols.denovo_design.movers.FastDesign()			#Call the FastDesign Mover
			mover.set_task_factory(task)								#Add the TaskFactory to it
			mover.set_movemap(movemap)								#Add the MoveMap to it
			mover.set_scorefxn(scorefxn)								#Add the Score Function to it
			#5 - Setup and apply the generic Monte Carlo mover
			MC = pyrosetta.rosetta.protocols.simple_moves.GenericMonteCarloMover()			#Call Monter Carlo Class
			MC.set_mover(mover)									#Load The Mover
			MC.set_scorefxn(scorefxn)								#Set score function
			MC.set_maxtrials(10)									#Set number of monte carlo loops
			MC.set_temperature(1)									#Set temperature
			MC.set_preapply(False)									#To apply Boltzmann accept/reject to all applications of the mover (always use False)
			MC.set_drift(True)									#Make current pose = next iteration pose
			MC.set_sampletype('high')								#Move monte carlo to higher filter score
			MC.add_filter(filters , False , 1.0 , 'high' , True)					#Add a filter (Filter Type , Adaptive , Temperature , Sample Type , Rank By)
			MC.apply(pose)										#Apply Move
			os.remove('Resfile.resfile')								#To keep working directory clean, and to make sure each Resfile has the info for each layer only and they do not get mixed and appended together in one Resfile
		#C - Relax pose
		relax.apply(pose)
		#D - Output result
		score3_of_design_after_relax = scorefxn(pose)							#Measure score of designed pose
		pose.dump_pdb('Designed.pdb')									#Export final pose into a .pdb structure file
		print('---------------------------------------------------------')
		print('Original Structure Score:' , '\t' , score1_original_before_relax)
		print('Relaxed Original Score:' , '\t' , score2_original_after_relax)
		print('Relaxed Design Score:' , '\t\t' , score3_of_design_after_relax)

def Fragments(Pose):
	''' Submits the pose to the Robetta server (http://www.robetta.org) for fragment generation that are used for the Abinitio folding simulation. Then measures the RMSD for each fragment at each position and chooses the lowest RMSD. Then averages out the lowest RMSDs. Then plots the lowest RMSD fragment for each positon '''
	''' Generates the 3-mer file, the 9-mer file, the PsiPred file, the RMSD vs Position PDF plot with the averaged fragment RMSD printed in the plot '''
	#Make the 3-mer and 9-mer fragment files and the PSIPRED file using the Robetta server
	pose = pose_from_pdb(Pose)
	sequence = pose.sequence()
	#Post
	web = requests.get('http://www.robetta.org/fragmentsubmit.jsp')
	payload = {
		'UserName':'ac.research',
		'Email':'',
		'Notes':'structure',
		'Sequence':sequence,
		'Fasta':'',
		'Code':'',
		'ChemicalShifts':'',
		'NoeConstraints':'',
		'DipolarConstraints':'',
		'type':'submit'
	}
	session = requests.session()
	response = session.post('http://www.robetta.org/fragmentsubmit.jsp', data=payload , files=dict(foo='bar'))		
	for line in response:
		line = line.decode()
		if re.search('<a href="(fragmentqueue.jsp\?id=[0-9].*)">' , line):
			JobID = re.findall('<a href="(fragmentqueue.jsp\?id=[0-9].*)">' , line)
	JobURL = 'http://www.robetta.org/' + JobID[0]
	#Check
	ID = JobID[0].split('=')
	print('Job ID: ' + str(ID[1]))
	while True:
		Job = urllib.request.urlopen(JobURL)
		jobdata = bs4.BeautifulSoup(Job , 'lxml')
		status = jobdata.find('td', string='Status: ').find_next().text
		if status == 'Complete':
			print(datetime.datetime.now().strftime('%d %B %Y @ %H:%M') , 'Status:' , status)
			break
		else:
			print(datetime.datetime.now().strftime('%d %B %Y @ %H:%M') , 'Status:' , status)
			time.sleep(1800)
			continue
	#Download
	sequence = pose.sequence()
	fasta = open('structure.fasta' , 'w')
	fasta.write(sequence)
	fasta.close()
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/aat000_03_05.200_v1_3')
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/aat000_09_05.200_v1_3')
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/t000_.psipred_ss2')
	os.rename('aat000_03_05.200_v1_3' , 'frags.200.3mers')
	os.rename('aat000_09_05.200_v1_3' , 'frags.200.9mers')
	os.rename('t000_.psipred_ss2' , 'pre.psipred.ss2')
	#Calculate the best fragment's RMSD at each position
	frag = open('frags.200.9mers' , 'r')
	rmsd = open('temp.dat' , 'w')
	for line in frag:
		if line.lstrip().startswith('position:'):
			line = line.split()
			size = line[1]
	frag.close()
	count = 0
	for x in range (int(size)):
		count +=1
		#Get the pose and make a copy of it to apply changes to
		pose_copy = Pose()
		pose_copy.assign(pose)
		#Setup frame list
		frames = pyrosetta.rosetta.core.fragment.FrameList()
		#Setup the 9-mer fragment (9-mer is better than 3-mer for this analysis)
		fragset = pyrosetta.rosetta.core.fragment.ConstantLengthFragSet(9)
		fragset.read_fragment_file('frags.200.9mers')
		fragset.frames(count , frames)
		#Setup the MoveMap
		movemap = MoveMap()
		movemap.set_bb(True)
		#Setup and apply the fragment inserting mover
		for frame in frames:
			for frag_num in range( 1 , frame.nr_frags() + 1 ):
				frame.apply(movemap , frag_num , pose_copy)
				#Measure the RMSD difference between the original pose and the new changed pose (the copy)
				RMSD = rosetta.core.scoring.CA_rmsd(pose , pose_copy)
				print(RMSD , '\t' , count)
				rmsd.write(str(RMSD) + '\t' + str(count) + '\n')
				#Reset the copy pose to original pose
				pose_copy.assign(pose)
	rmsd.close()
	#Analyse the RMSD file to get the lowest RMSD for each position
	data = open('RMSDvsPosition.dat' , 'w')
	lowest = {} 									#Mapping group number -> lowest value found
	for line in open('temp.dat'):
		parts = line.split()
		if len(parts) != 2:							#Only lines with two items on it
			continue
		first = float(parts[0])
		second = int(parts[1])
		if first == 0: 								#Skip line with 0.0 RMSD (this is an error from the 9-mer fragment file). I don't know why it happens
			continue
		if second not in lowest:
			lowest[second] = first
		else:
			if first < lowest[second]:
				lowest[second] = first
	for position, rmsd in lowest.items():
		#print(str(rmsd) + '\t' + str(position))
		data.write(str(position) + '\t' + str(rmsd) + '\n')
	data.close()
	#Calculate the average RMSD of the fragments
	data = open('RMSDvsPosition.dat' , 'r')
	value = 0
	for line in data:
		line = line.split()
		RMSD = float(line[1])
		value = value + RMSD
		count = int(line[0])
	Average_RMSD = round(value / count , 2)
	#Plot the results
	gnuplot = open('gnuplot_sets' , 'w')
	gnuplot.write("reset\nset terminal postscript\nset output './plot_frag.pdf'\nset encoding iso_8859_1\nset term post eps enh color\nset xlabel 'Position'\nset ylabel 'RMSD (\\305)'\nset yrange [0:]\nset xrange [0:]\nset xtics auto\nset xtics rotate\nset grid front\nunset grid\nset title 'Fragment Quality'\nset key off\nset boxwidth 0.5\nset style fill solid\nset label 'Average RMSD = " + str(Average_RMSD) + "' at graph 0.01 , graph 0.95 tc lt 7 font 'curior 12'\nplot 'RMSDvsPosition.dat' with boxes\nexit")
	gnuplot.close()
	os.system('gnuplot < gnuplot_sets')
	os.remove('gnuplot_sets')
	os.remove('temp.dat')
	return(Average_RMSD)

def Expand(line):
	ax = plt.figure().add_subplot(111 , projection = '3d')
	line = [float(x) for x in line.split(';')]
	iters = int(len(line) / 3)
	new_line = list()
	count = 0
	V1 = numpy.array(line[0:3])
	pV2 = V1
	new_line.append('{};{};{}'.format(V1[0] , V1[1] , V1[2]))
	for vector in range(iters):
		V2 = numpy.array(line[count + 3 : count + 6])
		if len(V2) == 0:
			pass
		else:
			ax.plot([V1[0] , V2[0]] , [V1[1] , V2[1]] , [V1[2] , V2[2]] , marker = 'o')
			Mag = numpy.sqrt(((V2[0] - V1[0])**2) + ((V2[1] - V1[1])**2) + ((V2[2] - V1[2])**2))
			Com = numpy.array([V2[0] - V1[0] , V2[1] - V1[1] , V2[2] - V1[2]])
			Sca = (3.8 / Mag) * Com
			NV2 = numpy.add(pV2 , Sca)
			MagN = numpy.sqrt(((NV2[0] - pV2[0])**2) + ((NV2[1] - pV2[1])**2) + ((NV2[2] - pV2[2])**2))
			print('Vector {}_{}\tMagnitude Increase:\t'.format(vector + 1 , vector + 2) , round(Mag , 3) , '\t--->\t' , round(MagN , 3))
			ax.plot([pV2[0] , NV2[0]] , [pV2[1] , NV2[1]] , [pV2[2] , NV2[2]] , marker = 'o')
			count += 3
			V1 = V2
			pV2 = NV2
			new_line.append('{};{};{}'.format(NV2[0] , NV2[1] , NV2[2]))
	#plt.show()
	new_line = ';'.join(new_line)
	return(new_line)

def DrawPDB(line):
	''' Draws a protein topology in Glycine given each residue's only CA atom's XYZ coordinates '''
	''' Generates the DeNovo.pdb file '''
	#Import the coordinates
	line = line.split(';')
	AAs = int((len(line)) / 3)
	count_x = 0
	count_y = 1
	count_z = 2
	ResCount = 1
	AtoCount = 1
	tag = '+'
	ax = plt.figure().add_subplot(111 , projection = '3d')
	for coordinates in range(AAs):
		if tag == '+':
			Ox = round(float(line[count_x]) , 3)
			Oy = round(float(line[count_y]) , 3)
			Oz = round(float(line[count_z]) , 3)
			if Ox == '0' and Oy == '0' and Oz == '0':
				continue
			count_x += 3
			count_y += 3
			count_z += 3
			AtoCount += 1
			try:
				Px = round(float(line[count_x]) , 3)
				Py = round(float(line[count_y]) , 3)
				Pz = round(float(line[count_z]) , 3)
			except:
				pass
			#Initial and Terminus coordinates
			O = numpy.array([Ox , Oy , Oz])
			P = numpy.array([Px , Py , Pz])
			ax.plot([O[0] , P[0]] , [O[1] , P[1]] , [O[2] , P[2]] , marker = 'o')
			Mag = numpy.sqrt(((P[0] - O[0])**2) + ((P[1] - O[1])**2) + ((P[2] - O[2])**2))				#Magnitude = 3.8
			Com = [P[0] - O[0] , P[1] - O[1] , P[2] - O[2]]
			#The Carbon atom
			#1 - Move To Axis (0 , 0 , 0)
			Cori = P - O
			MagCori = numpy.sqrt(((Cori[0])**2) + ((Cori[1])**2) + ((Cori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Cori[0]] , [0 , Cori[1]] , [0 , Cori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			A = numpy.radians(00.0)		#Phi 	Angle
			B = numpy.radians(20.5)		#Theta	Angle
			Y = numpy.radians(00.0)		#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			CR = [	[numpy.cos(B)	,	-numpy.sin(B)	,	0] , 
				[numpy.sin(B)	, 	 numpy.cos(B)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			CR = [	[numpy.cos(B)			,	numpy.sin(B)*numpy.sin(Y)						,	numpy.sin(B)*numpy.cos(Y)					] , 
				[numpy.sin(B) *numpy.sin(A)	, 	numpy.cos(Y)*numpy.cos(A)-numpy.cos(B)*numpy.sin(Y)*numpy.sin(A)	,	numpy.cos(A)*numpy.sin(Y)-numpy.cos(B)*numpy.cos(Y)*numpy.sin(A)] ,
				[-numpy.sin(B)*numpy.cos(A)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(A)*numpy.cos(Y)	,	numpy.sin(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(Y)*numpy.cos(A)]]
			#XYZ steps Tait-Bryan angles
			CR = [	[numpy.cos(B)*numpy.cos(Y)						,	-numpy.cos(Y)*numpy.sin(B)						,	numpy.sin(B)			] , 
				[numpy.cos(A)*numpy.sin(Y)+numpy.cos(Y)*numpy.sin(A)*numpy.sin(B)	, 	numpy.cos(A)*numpy.cos(Y)-numpy.sin(A)*numpy.sin(B)*numpy.sin(Y)	,	-numpy.cos(B)*numpy.sin(A)	] ,
				[numpy.sin(A)*numpy.sin(Y)-numpy.cos(A)*numpy.cos(Y)*numpy.sin(B)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(A)*numpy.sin(B)*numpy.sin(Y)	,	numpy.cos(A)*numpy.cos(B)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Crot = numpy.dot(CR , Cori)
			MagCrot = numpy.sqrt(((Cori[0])**2) + ((Cori[1])**2) + ((Cori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Crot[0]] , [0 , Crot[1]] , [0 , Crot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Cback = Crot + O
			MagCback = numpy.sqrt(((Cback[0] - O[0])**2) + ((Cback[1] - O[1])**2) + ((Cback[2] - O[2])**2))		#Magnitude = 3.8
			#ax.plot([O[0] , Cback[0]] , [O[1] , Cback[1]] , [O[2] , Cback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			CBack = numpy.array([Cback[0] - O[0] , Cback[1] - O[1] , Cback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			CScaled = (1.5 / 3.8) * CBack										#Multiply by (distance to final C position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			C = numpy.add(O , CScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the C atom)
			ComC = [C[0] - O[0] , C[1] - O[1] , C[2] - O[2]]
			MagC = numpy.sqrt(((C[0] - O[0])**2) + ((C[1] - O[1])**2) + ((C[2] - O[2])**2))				#Magnitude = 1.5
			ax.plot([O[0] , C[0]] , [O[1] , C[1]] , [O[2] , C[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleC = numpy.degrees(numpy.arccos((numpy.dot(ComC , Com)) / (MagC * Mag)))				#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#The Nitrogen atom
			#1 - Move To Axis (0 , 0 , 0)
			Nori = P - O
			MagNori = numpy.sqrt(((Nori[0])**2) + ((Nori[1])**2) + ((Nori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Nori[0]] , [0 , Nori[1]] , [0 , Nori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			AA = numpy.radians(00.0)	#Phi 	Angle
			BB = numpy.radians(351.0)	#Theta	Angle
			YY = numpy.radians(00.0)	#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			NR = [	[numpy.cos(BB)	,	-numpy.sin(BB)	,	0] , 
				[numpy.sin(BB)	, 	 numpy.cos(BB)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			NR = [	[numpy.cos(BB)			,	numpy.sin(BB)*numpy.sin(YY)						,	numpy.sin(BB)*numpy.cos(YY)						] , 
				[numpy.sin(BB) *numpy.sin(AA)	, 	numpy.cos(YY)*numpy.cos(AA)-numpy.cos(BB)*numpy.sin(YY)*numpy.sin(AA)	,	numpy.cos(AA)*numpy.sin(YY)-numpy.cos(BB)*numpy.cos(YY)*numpy.sin(AA)	] ,
				[-numpy.sin(BB)*numpy.cos(AA)	,	numpy.cos(YY)*numpy.sin(AA)+numpy.cos(BB)*numpy.cos(AA)*numpy.cos(YY)	,	numpy.sin(YY)*numpy.sin(AA)+numpy.cos(BB)*numpy.cos(YY)*numpy.cos(AA)	]]
			#XYZ steps Tait-Bryan angles
			NR = [	[numpy.cos(BB)*numpy.cos(YY)						,	-numpy.cos(YY)*numpy.sin(BB)						,	numpy.sin(BB)			] , 
				[numpy.cos(AA)*numpy.sin(YY)+numpy.cos(YY)*numpy.sin(AA)*numpy.sin(BB)	, 	numpy.cos(AA)*numpy.cos(YY)-numpy.sin(AA)*numpy.sin(BB)*numpy.sin(YY)	,	-numpy.cos(BB)*numpy.sin(AA)	] ,
				[numpy.sin(AA)*numpy.sin(YY)-numpy.cos(AA)*numpy.cos(YY)*numpy.sin(BB)	,	numpy.cos(YY)*numpy.sin(AA)+numpy.cos(AA)*numpy.sin(BB)*numpy.sin(YY)	,	numpy.cos(AA)*numpy.cos(BB)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Nrot = numpy.dot(NR , Nori)
			MagNrot = numpy.sqrt(((Nori[0])**2) + ((Nori[1])**2) + ((Nori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Nrot[0]] , [0 , Nrot[1]] , [0 , Nrot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Nback = Nrot + O
			MagNback = numpy.sqrt(((Nback[0] - O[0])**2) + ((Nback[1] - O[1])**2) + ((Nback[2] - O[2])**2))		#Magnitude = 3.8
			#ax.plot([O[0] , Nback[0]] , [O[1] , Nback[1]] , [O[2] , Nback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			NBack = numpy.array([Nback[0] - O[0] , Nback[1] - O[1] , Nback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			NScaled = (2.4 / 3.8) * NBack										#Multiply by (distance to final N position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			N = numpy.add(O , NScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the N atom)
			ComN = [N[0] - O[0] , N[1] - O[1] , N[2] - O[2]]
			MagN = numpy.sqrt(((N[0] - O[0])**2) + ((N[1] - O[1])**2) + ((N[2] - O[2])**2))				#Magnitude = 2.4
			ax.plot([O[0] , N[0]] , [O[1] , N[1]] , [O[2] , N[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleN = numpy.degrees(numpy.arccos((numpy.dot(ComN , Com)) / (MagN * Mag)))				#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#The Oxygen atom
			#1 - Move To Axis (0 , 0 , 0)
			Oxori = P - O
			MagCori = numpy.sqrt(((Oxori[0])**2) + ((Oxori[1])**2) + ((Oxori[2])**2))				#Magnitude = 3.8
			#ax.plot([0 , Oxori[0]] , [0 , Oxori[1]] , [0 , Oxori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			A = numpy.radians(00.0)		#Phi 	Angle
			B = numpy.radians(46.7)		#Theta	Angle
			Y = numpy.radians(00.0)		#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			OxR = [	[numpy.cos(B)	,	-numpy.sin(B)	,	0] , 
				[numpy.sin(B)	, 	 numpy.cos(B)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			OxR = [	[numpy.cos(B)			,	numpy.sin(B)*numpy.sin(Y)						,	numpy.sin(B)*numpy.cos(Y)					] , 
				[numpy.sin(B) *numpy.sin(A)	, 	numpy.cos(Y)*numpy.cos(A)-numpy.cos(B)*numpy.sin(Y)*numpy.sin(A)	,	numpy.cos(A)*numpy.sin(Y)-numpy.cos(B)*numpy.cos(Y)*numpy.sin(A)] ,
				[-numpy.sin(B)*numpy.cos(A)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(A)*numpy.cos(Y)	,	numpy.sin(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(Y)*numpy.cos(A)]]
			#XYZ steps Tait-Bryan angles
			OxR = [	[numpy.cos(B)*numpy.cos(Y)						,	-numpy.cos(Y)*numpy.sin(B)						,	numpy.sin(B)			] , 
				[numpy.cos(A)*numpy.sin(Y)+numpy.cos(Y)*numpy.sin(A)*numpy.sin(B)	, 	numpy.cos(A)*numpy.cos(Y)-numpy.sin(A)*numpy.sin(B)*numpy.sin(Y)	,	-numpy.cos(B)*numpy.sin(A)	] ,
				[numpy.sin(A)*numpy.sin(Y)-numpy.cos(A)*numpy.cos(Y)*numpy.sin(B)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(A)*numpy.sin(B)*numpy.sin(Y)	,	numpy.cos(A)*numpy.cos(B)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Oxrot = numpy.dot(OxR , Oxori)
			MagOxrot = numpy.sqrt(((Oxori[0])**2) + ((Oxori[1])**2) + ((Oxori[2])**2))				#Magnitude = 3.8
			#ax.plot([0 , Oxrot[0]] , [0 , Oxrot[1]] , [0 , Oxrot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Oxback = Oxrot + O
			MagOxback = numpy.sqrt(((Oxback[0] - O[0])**2) + ((Oxback[1] - O[1])**2) + ((Oxback[2] - O[2])**2))	#Magnitude = 3.8
			#ax.plot([O[0] , Oxback[0]] , [O[1] , Oxback[1]] , [O[2] , Oxback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			OxBack = numpy.array([Oxback[0] - O[0] , Oxback[1] - O[1] , Oxback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			OxScaled = (2.4 / 3.8) * OxBack										#Multiply by (distance to final O position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			Oxg = numpy.add(O , OxScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the O atom)
			ComOx = [Oxg[0] - O[0] , Oxg[1] - O[1] , Oxg[2] - O[2]]
			MagOx = numpy.sqrt(((Oxg[0] - O[0])**2) + ((Oxg[1] - O[1])**2) + ((Oxg[2] - O[2])**2))			#Magnitude = 2.4
			ax.plot([O[0] , Oxg[0]] , [O[1] , Oxg[1]] , [O[2] , Oxg[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleOx = numpy.degrees(numpy.arccos((numpy.dot(ComOx , Com)) / (MagOx * Mag)))			#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#Plot to visualise
			ax.scatter(0 , 0 , 0 , marker = 's' , color = 'black' , s = 50)
			ax.set_xlabel('X')
			ax.set_ylabel('Y')
			ax.set_zlabel('Z')
			#plt.show()
			'''
			#Study!!!
			#Find the A B Y angles
			O  =	[1.458 , 0.000 , 0.000]
			C  =	[2.009 , 1.420 , 0.000]
			Oxg=	[1.251 , 2.390 , 0.000]
			N  =	[3.332 , 1.536 , 0.000]
			P  =	[3.988 , 2.839 , 0.000]
			#The Carbon Atom
			MagOP = numpy.sqrt(((P[0] - O[0])**2) + ((P[1] - O[1])**2) + ((P[2] - O[2])**2))			#Magnitude = 3.8
			MagOC = numpy.sqrt(((C[0] - O[0])**2) + ((C[1] - O[1])**2) + ((C[2] - O[2])**2))			#Magnitude = 1.5
			ComOP = [P[0] - O[0] , P[1] - O[1] , P[2] - O[2]]
			ComOC = [C[0] - O[0] , C[1] - O[1] , C[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComOC)) / (MagOC * MagOP)))			#Angle = 20.5			
			print(angle)
			ax.plot([O[0] , P[0]] , [O[1] , P[1]] , [O[2] , P[2]] , marker = 'o')
			ax.plot([O[0] , C[0]] , [O[1] , C[1]] , [O[2] , C[2]] , marker = 'o')
			#The Nitrogen Atom
			MagON = numpy.sqrt(((N[0] - O[0])**2) + ((N[1] - O[1])**2) + ((N[2] - O[2])**2))			#Magnitude = 2.4
			ComON = [N[0] - O[0] , N[1] - O[1] , N[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComON)) / (MagON * MagOP)))			#Angle = 9.0 (360 - 9 = 351)			
			print(angle)
			ax.plot([O[0] , N[0]] , [O[1] , N[1]] , [O[2] , N[2]] , marker = 'o')
			#The Oxygen Atom
			MagOOx = numpy.sqrt(((Ox[0] - O[0])**2) + ((Ox[1] - O[1])**2) + ((Ox[2] - O[2])**2))			#Magnitude = 2.4
			ComOOx = [Ox[0] - O[0] , Ox[1] - O[1] , Ox[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComOOx)) / (MagOOx * MagOP)))			#Angle = 46.7
			print(angle)
			ax.plot([O[0] , Ox[0]] , [O[1] , Ox[1]] , [O[2] , Ox[2]] , marker = 'o')
			plt.show()
			'''
			TheLineCA = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'CA' , '' , 'GLY' , 'A' , ResCount , '' , str(round(Ox , 3)) , str(round(Oy , 3)) , str(round(Oz , 3)) , 1.0 , 0.0 , 'C' , '') + '\n'
			AtoCount += 1
			TheLineC = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'C' , '' , 'GLY' , 'A' , ResCount , '' , str(round(C[0] , 3)) , str(round(C[1] , 3)) , str(round(C[2] , 3)) , 1.0 , 0.0 , 'C' , '') + '\n'
			AtoCount += 1
			TheLineOxg = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'O' , '' , 'GLY' , 'A' , ResCount , '' , str(round(Oxg[0] , 3)) , str(round(Oxg[1] , 3)) , str(round(Oxg[2] , 3)) , 1.0 , 0.0 , 'O' , '') + '\n'
			AtoCount += 1
			ResCount += 1
			TheLineN = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'N' , '' , 'GLY' , 'A' , ResCount , '' , str(round(N[0] , 3)) , str(round(N[1] , 3)) , str(round(N[2] , 3)) , 1.0 , 0.0 , 'N' , '') + '\n'
			output = open('Backbone.pdb' , 'a')
			output.write(TheLineCA)
			output.write(TheLineC)
			output.write(TheLineOxg)
			output.write(TheLineN)
			output.close()
			tag ='-'
		else:
			Ox = round(float(line[count_x]) , 3)
			Oy = round(float(line[count_y]) , 3)
			Oz = round(float(line[count_z]) , 3)
			if Ox == '0' and Oy == '0' and Oz == '0':
				continue
			count_x += 3
			count_y += 3
			count_z += 3
			AtoCount += 1
			try:
				Px = round(float(line[count_x]) , 3)
				Py = round(float(line[count_y]) , 3)
				Pz = round(float(line[count_z]) , 3)
			except:
				pass
			#Initial and Terminus coordinates
			O = numpy.array([Ox , Oy , Oz])
			P = numpy.array([Px , Py , Pz])
			ax.plot([O[0] , P[0]] , [O[1] , P[1]] , [O[2] , P[2]] , marker = 'o')
			Mag = numpy.sqrt(((P[0] - O[0])**2) + ((P[1] - O[1])**2) + ((P[2] - O[2])**2))				#Magnitude = 3.8
			Com = [P[0] - O[0] , P[1] - O[1] , P[2] - O[2]]
			#The Carbon atom
			#1 - Move To Axis (0 , 0 , 0)
			Cori = P - O
			MagCori = numpy.sqrt(((Cori[0])**2) + ((Cori[1])**2) + ((Cori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Cori[0]] , [0 , Cori[1]] , [0 , Cori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			A = numpy.radians(00.0)		#Phi 	Angle
			B = numpy.radians(339.5)	#Theta	Angle
			Y = numpy.radians(00.0)		#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			CR = [	[numpy.cos(B)	,	-numpy.sin(B)	,	0] , 
				[numpy.sin(B)	, 	 numpy.cos(B)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			CR = [	[numpy.cos(B)			,	numpy.sin(B)*numpy.sin(Y)						,	numpy.sin(B)*numpy.cos(Y)					] , 
				[numpy.sin(B) *numpy.sin(A)	, 	numpy.cos(Y)*numpy.cos(A)-numpy.cos(B)*numpy.sin(Y)*numpy.sin(A)	,	numpy.cos(A)*numpy.sin(Y)-numpy.cos(B)*numpy.cos(Y)*numpy.sin(A)] ,
				[-numpy.sin(B)*numpy.cos(A)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(A)*numpy.cos(Y)	,	numpy.sin(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(Y)*numpy.cos(A)]]
			#XYZ steps Tait-Bryan angles
			CR = [	[numpy.cos(B)*numpy.cos(Y)						,	-numpy.cos(Y)*numpy.sin(B)						,	numpy.sin(B)			] , 
				[numpy.cos(A)*numpy.sin(Y)+numpy.cos(Y)*numpy.sin(A)*numpy.sin(B)	, 	numpy.cos(A)*numpy.cos(Y)-numpy.sin(A)*numpy.sin(B)*numpy.sin(Y)	,	-numpy.cos(B)*numpy.sin(A)	] ,
				[numpy.sin(A)*numpy.sin(Y)-numpy.cos(A)*numpy.cos(Y)*numpy.sin(B)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(A)*numpy.sin(B)*numpy.sin(Y)	,	numpy.cos(A)*numpy.cos(B)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Crot = numpy.dot(CR , Cori)
			MagCrot = numpy.sqrt(((Cori[0])**2) + ((Cori[1])**2) + ((Cori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Crot[0]] , [0 , Crot[1]] , [0 , Crot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Cback = Crot + O
			MagCback = numpy.sqrt(((Cback[0] - O[0])**2) + ((Cback[1] - O[1])**2) + ((Cback[2] - O[2])**2))		#Magnitude = 3.8
			#ax.plot([O[0] , Cback[0]] , [O[1] , Cback[1]] , [O[2] , Cback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			CBack = numpy.array([Cback[0] - O[0] , Cback[1] - O[1] , Cback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			CScaled = (1.5 / 3.8) * CBack										#Multiply by (distance to final C position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			C = numpy.add(O , CScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the C atom)
			ComC = [C[0] - O[0] , C[1] - O[1] , C[2] - O[2]]
			MagC = numpy.sqrt(((C[0] - O[0])**2) + ((C[1] - O[1])**2) + ((C[2] - O[2])**2))				#Magnitude = 1.5
			ax.plot([O[0] , C[0]] , [O[1] , C[1]] , [O[2] , C[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleC = numpy.degrees(numpy.arccos((numpy.dot(ComC , Com)) / (MagC * Mag)))				#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#The Nitrogen atom
			#1 - Move To Axis (0 , 0 , 0)
			Nori = P - O
			MagNori = numpy.sqrt(((Nori[0])**2) + ((Nori[1])**2) + ((Nori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Nori[0]] , [0 , Nori[1]] , [0 , Nori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			AA = numpy.radians(00.0)	#Phi 	Angle
			BB = numpy.radians(9.0)		#Theta	Angle
			YY = numpy.radians(00.0)	#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			NR = [	[numpy.cos(BB)	,	-numpy.sin(BB)	,	0] , 
				[numpy.sin(BB)	, 	 numpy.cos(BB)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			NR = [	[numpy.cos(BB)			,	numpy.sin(BB)*numpy.sin(YY)						,	numpy.sin(BB)*numpy.cos(YY)						] , 
				[numpy.sin(BB) *numpy.sin(AA)	, 	numpy.cos(YY)*numpy.cos(AA)-numpy.cos(BB)*numpy.sin(YY)*numpy.sin(AA)	,	numpy.cos(AA)*numpy.sin(YY)-numpy.cos(BB)*numpy.cos(YY)*numpy.sin(AA)	] ,
				[-numpy.sin(BB)*numpy.cos(AA)	,	numpy.cos(YY)*numpy.sin(AA)+numpy.cos(BB)*numpy.cos(AA)*numpy.cos(YY)	,	numpy.sin(YY)*numpy.sin(AA)+numpy.cos(BB)*numpy.cos(YY)*numpy.cos(AA)	]]
			#XYZ steps Tait-Bryan angles
			NR = [	[numpy.cos(BB)*numpy.cos(YY)						,	-numpy.cos(YY)*numpy.sin(BB)						,	numpy.sin(BB)			] , 
				[numpy.cos(AA)*numpy.sin(YY)+numpy.cos(YY)*numpy.sin(AA)*numpy.sin(BB)	, 	numpy.cos(AA)*numpy.cos(YY)-numpy.sin(AA)*numpy.sin(BB)*numpy.sin(YY)	,	-numpy.cos(BB)*numpy.sin(AA)	] ,
				[numpy.sin(AA)*numpy.sin(YY)-numpy.cos(AA)*numpy.cos(YY)*numpy.sin(BB)	,	numpy.cos(YY)*numpy.sin(AA)+numpy.cos(AA)*numpy.sin(BB)*numpy.sin(YY)	,	numpy.cos(AA)*numpy.cos(BB)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Nrot = numpy.dot(NR , Nori)
			MagNrot = numpy.sqrt(((Nori[0])**2) + ((Nori[1])**2) + ((Nori[2])**2))					#Magnitude = 3.8
			#ax.plot([0 , Nrot[0]] , [0 , Nrot[1]] , [0 , Nrot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Nback = Nrot + O
			MagNback = numpy.sqrt(((Nback[0] - O[0])**2) + ((Nback[1] - O[1])**2) + ((Nback[2] - O[2])**2))		#Magnitude = 3.8
			#ax.plot([O[0] , Nback[0]] , [O[1] , Nback[1]] , [O[2] , Nback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			NBack = numpy.array([Nback[0] - O[0] , Nback[1] - O[1] , Nback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			NScaled = (2.4 / 3.8) * NBack										#Multiply by (distance to final N position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			N = numpy.add(O , NScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the N atom)
			ComN = [N[0] - O[0] , N[1] - O[1] , N[2] - O[2]]
			MagN = numpy.sqrt(((N[0] - O[0])**2) + ((N[1] - O[1])**2) + ((N[2] - O[2])**2))				#Magnitude = 2.4
			ax.plot([O[0] , N[0]] , [O[1] , N[1]] , [O[2] , N[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleN = numpy.degrees(numpy.arccos((numpy.dot(ComN , Com)) / (MagN * Mag)))				#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#The Oxygen atom
			#1 - Move To Axis (0 , 0 , 0)
			Oxori = P - O
			MagCori = numpy.sqrt(((Oxori[0])**2) + ((Oxori[1])**2) + ((Oxori[2])**2))				#Magnitude = 3.8
			#ax.plot([0 , Oxori[0]] , [0 , Oxori[1]] , [0 , Oxori[2]] , marker = 'o')
			#2 - Define Rotation Matrix
			A = numpy.radians(00.0)		#Phi 	Angle
			B = numpy.radians(313.3)	#Theta	Angle
			Y = numpy.radians(00.0)		#Psi	Angle
			#2D Rotation Matrix - works best because the peptide bond is on a plane anyway, so there is no change in the Z axis.
			OxR = [	[numpy.cos(B)	,	-numpy.sin(B)	,	0] , 
				[numpy.sin(B)	, 	 numpy.cos(B)	,	0] ,
				[	0	,		0	,	1]]
			"""
			#XYX steps Tait-Bryan angles
			OxR = [	[numpy.cos(B)			,	numpy.sin(B)*numpy.sin(Y)						,	numpy.sin(B)*numpy.cos(Y)					] , 
				[numpy.sin(B) *numpy.sin(A)	, 	numpy.cos(Y)*numpy.cos(A)-numpy.cos(B)*numpy.sin(Y)*numpy.sin(A)	,	numpy.cos(A)*numpy.sin(Y)-numpy.cos(B)*numpy.cos(Y)*numpy.sin(A)] ,
				[-numpy.sin(B)*numpy.cos(A)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(A)*numpy.cos(Y)	,	numpy.sin(Y)*numpy.sin(A)+numpy.cos(B)*numpy.cos(Y)*numpy.cos(A)]]
			#XYZ steps Tait-Bryan angles
			OxR = [	[numpy.cos(B)*numpy.cos(Y)						,	-numpy.cos(Y)*numpy.sin(B)						,	numpy.sin(B)			] , 
				[numpy.cos(A)*numpy.sin(Y)+numpy.cos(Y)*numpy.sin(A)*numpy.sin(B)	, 	numpy.cos(A)*numpy.cos(Y)-numpy.sin(A)*numpy.sin(B)*numpy.sin(Y)	,	-numpy.cos(B)*numpy.sin(A)	] ,
				[numpy.sin(A)*numpy.sin(Y)-numpy.cos(A)*numpy.cos(Y)*numpy.sin(B)	,	numpy.cos(Y)*numpy.sin(A)+numpy.cos(A)*numpy.sin(B)*numpy.sin(Y)	,	numpy.cos(A)*numpy.cos(B)	]]
			"""
			#3 - Rotate Matrix on XY axis, keeping Z unchanged
			Oxrot = numpy.dot(OxR , Oxori)
			MagOxrot = numpy.sqrt(((Oxori[0])**2) + ((Oxori[1])**2) + ((Oxori[2])**2))				#Magnitude = 3.8
			#ax.plot([0 , Oxrot[0]] , [0 , Oxrot[1]] , [0 , Oxrot[2]] , marker = 'o')
			#4 - Move rotated vector back to original start point
			Oxback = Oxrot + O
			MagOxback = numpy.sqrt(((Oxback[0] - O[0])**2) + ((Oxback[1] - O[1])**2) + ((Oxback[2] - O[2])**2))	#Magnitude = 3.8
			#ax.plot([O[0] , Oxback[0]] , [O[1] , Oxback[1]] , [O[2] , Oxback[2]] , marker = 'o')
			#5 - Scale vector to new magnitude
			OxBack = numpy.array([Oxback[0] - O[0] , Oxback[1] - O[1] , Oxback[2] - O[2]])				#Get components of the vector after it was returned to its original starting point "back"
			OxScaled = (2.4 / 3.8) * OxBack										#Multiply by (distance to final O position / distance between the 2 CA atoms) the scaling factor, this gives the value each axis needs to move by to each coordinates that result in the new scaled magnitude
			Oxg = numpy.add(O , OxScaled)										#Add scaled components to the initial coordinates to get new terminus coordinates (the final coordintes of the O atom)
			ComOx = [Oxg[0] - O[0] , Oxg[1] - O[1] , Oxg[2] - O[2]]
			MagOx = numpy.sqrt(((Oxg[0] - O[0])**2) + ((Oxg[1] - O[1])**2) + ((Oxg[2] - O[2])**2))			#Magnitude = 2.4
			ax.plot([O[0] , Oxg[0]] , [O[1] , Oxg[1]] , [O[2] , Oxg[2]] , marker = 'o')
			#6- Confirm angle between vectors
			#angleOx = numpy.degrees(numpy.arccos((numpy.dot(ComOx , Com)) / (MagOx * Mag)))			#Angle of rotation (is != 20.5 because it is calculated with the Z axis giving instead 12.08, but in 2D space the code will give 20.5) - This is commented out because it results in a RuntimeWarning through NumPy, basically the value is very very small is gets rounded up to 0 making the division impposible, it is not a math problem rather more a NumPy problem since it has low resolution
			#Plot to visualise
			ax.scatter(0 , 0 , 0 , marker = 's' , color = 'black' , s = 50)
			ax.set_xlabel('X')
			ax.set_ylabel('Y')
			ax.set_zlabel('Z')
			#plt.show()
			'''
			#Study!!!
			#Find the A B Y angles
			O  =	[1.458 , 0.000 , 0.000]
			C  =	[2.009 , 1.420 , 0.000]
			Oxg=	[1.251 , 2.390 , 0.000]
			N  =	[3.332 , 1.536 , 0.000]
			P  =	[3.988 , 2.839 , 0.000]
			#The Carbon Atom
			MagOP = numpy.sqrt(((P[0] - O[0])**2) + ((P[1] - O[1])**2) + ((P[2] - O[2])**2))			#Magnitude = 3.8
			MagOC = numpy.sqrt(((C[0] - O[0])**2) + ((C[1] - O[1])**2) + ((C[2] - O[2])**2))			#Magnitude = 1.5
			ComOP = [P[0] - O[0] , P[1] - O[1] , P[2] - O[2]]
			ComOC = [C[0] - O[0] , C[1] - O[1] , C[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComOC)) / (MagOC * MagOP)))			#Angle = 20.5			
			print(angle)
			ax.plot([O[0] , P[0]] , [O[1] , P[1]] , [O[2] , P[2]] , marker = 'o')
			ax.plot([O[0] , C[0]] , [O[1] , C[1]] , [O[2] , C[2]] , marker = 'o')
			#The Nitrogen Atom
			MagON = numpy.sqrt(((N[0] - O[0])**2) + ((N[1] - O[1])**2) + ((N[2] - O[2])**2))			#Magnitude = 2.4
			ComON = [N[0] - O[0] , N[1] - O[1] , N[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComON)) / (MagON * MagOP)))			#Angle = 9.0 (360 - 9 = 351)			
			print(angle)
			ax.plot([O[0] , N[0]] , [O[1] , N[1]] , [O[2] , N[2]] , marker = 'o')
			#The Oxygen Atom
			MagOOx = numpy.sqrt(((Ox[0] - O[0])**2) + ((Ox[1] - O[1])**2) + ((Ox[2] - O[2])**2))			#Magnitude = 2.4
			ComOOx = [Ox[0] - O[0] , Ox[1] - O[1] , Ox[2] - O[2]]
			angle = numpy.degrees(numpy.arccos((numpy.dot(ComOP , ComOOx)) / (MagOOx * MagOP)))			#Angle = 46.7
			print(angle)
			ax.plot([O[0] , Ox[0]] , [O[1] , Ox[1]] , [O[2] , Ox[2]] , marker = 'o')
			plt.show()
			'''
			TheLineCA = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'CA' , '' , 'GLY' , 'A' , ResCount , '' , str(round(Ox , 3)) , str(round(Oy , 3)) , str(round(Oz , 3)) , 1.0 , 0.0 , 'C' , '') + '\n'
			AtoCount += 1
			TheLineC = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'C' , '' , 'GLY' , 'A' , ResCount , '' , str(round(C[0] , 3)) , str(round(C[1] , 3)) , str(round(C[2] , 3)) , 1.0 , 0.0 , 'C' , '') + '\n'
			AtoCount += 1
			TheLineOxg = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'O' , '' , 'GLY' , 'A' , ResCount , '' , str(round(Oxg[0] , 3)) , str(round(Oxg[1] , 3)) , str(round(Oxg[2] , 3)) , 1.0 , 0.0 , 'O' , '') + '\n'
			AtoCount += 1
			ResCount += 1
			TheLineN = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'N' , '' , 'GLY' , 'A' , ResCount , '' , str(round(N[0] , 3)) , str(round(N[1] , 3)) , str(round(N[2] , 3)) , 1.0 , 0.0 , 'N' , '') + '\n'
			output = open('Backbone.pdb' , 'a')
			output.write(TheLineCA)
			output.write(TheLineC)
			output.write(TheLineOxg)
			output.write(TheLineN)
			output.close()
			tag ='+'
	#plt.show()
	#Remove the last 3 lines
	os.system("sed -i '$ d' ./Backbone.pdb")
	os.system("sed -i '$ d' ./Backbone.pdb")
	os.system("sed -i '$ d' ./Backbone.pdb")
	#Add the TER as the last line
	Term = open('Backbone.pdb' , 'a')
	Term.write('TER')
	Term.close()
	#The results of the Rotation Matrix is not optimum because the angles rotate on R2 (2D XY space) rather than R3 (3D XYZ space), keeping the Z axis rotation stationary allows for the backbone to be connected, but the C , O , N atoms not quit in the correct place to establish secondary structure hydrogen bonds. A quick solution is to Rosetta FastRelax the structure's cartesian coordinates
	#Relax cartesian coordinates to to fix suboptimal backbone
	pose = pose_from_pdb('Backbone.pdb')
	#Establish cartesian constraints
	mover = pyrosetta.rosetta.protocols.simple_moves.AddConstraintsToCurrentConformationMover()
	mover.CA_only()
	mover.generate_constraints(pose)
	mover.apply(pose)
	#Call a score function that uses cartesian constraint weights
	scorefxn = pyrosetta.rosetta.core.scoring.ScoreFunctionFactory.create_score_function('ref2015_cart')
	scorefxn.set_weight(rosetta.core.scoring.coordinate_constraint , 1.0)
	#FastRelax the structure
	relax = pyrosetta.rosetta.protocols.relax.FastRelax()
	relax.set_scorefxn(scorefxn)
	relax.cartesian(True)
	relax.ramp_down_constraints(False)
	relax.apply(pose)
	#Replace GLY with VAL
	for res in range(len(pose) + 1):
		if res == 0:
			pass
		else:
			mutate_residue(pose , res , 'V')
	#FastRelax the structure
	relax = pyrosetta.rosetta.protocols.relax.FastRelax()
	relax.set_scorefxn(scorefxn)
	relax.cartesian(True)
	relax.ramp_down_constraints(False)
	relax.apply(pose)
	#Save result
	pose.dump_pdb('TempDeNovo.pdb')
	#Renumber the structure
	tempfile = open('TempDeNovo.pdb' , 'r')
	anewfile = open('DeNovo.pdb' , 'a')
	AtoCount = 0
	ResCount = 0
	AA2 = None
	for line in tempfile:
		line = line.split()
		try:
			if line[0] == 'ATOM':
				AtoCount += 1
				AA1 = line[5]
				if not AA1 == AA2:
					ResCount += 1
				AA2 = AA1
				TheLine = TheLineCA = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format(line[0] , AtoCount , line[2] , '' , line[3] , line[4] , ResCount , '' , line[6] , line[7] , line[8] , line[9] , line[10] , line[11] , '') + '\n'
				anewfile.write(TheLine)
		except:
			pass
	tempfile.close()
	anewfile.close()
	os.system('rm Backbone.pdb')
	os.system('rm TempDeNovo.pdb')

def DrawCA(line):
	''' Draws a protein topology given the CA atom's XYZ coordinates of each residue '''
	''' Generates the CA.pdb file '''
	line = line.split(';')
	items = int((len(line) - 2) / 3)
	count_x = 0
	count_y = 1
	count_z = 2
	ResCount = 1
	AtoCount = 1
	for coordinates in range(items):
		x = str(round(float(line[count_x]) , 3))
		y = str(round(float(line[count_y]) , 3))
		z = str(round(float(line[count_z]) , 3))
		if x == '0' and y == '0' and z == '0':
			continue
		TheLine = '{:6}{:5d} {:4}{:1}{:3} {:1}{:4d}{:1}   {:8}{:8}{:8}{:6}{:6}          {:2}{:2}'.format('ATOM' , AtoCount , 'CA' , '' , 'GLY' , 'A' , ResCount , '' , x , y , z , 1.0 , 0.0 , 'C' , '') + '\n'
		output = open('CA.pdb' , 'a')
		output.write(TheLine)
		output.close()
		count_x += 3
		count_y += 3
		count_z += 3
		AtoCount += 1
		ResCount += 1

def GAN():
	pass
#--------------------------------------------------------------------------------------------------------------------------------------
line = '0.3729664981365204;0.6528127193450928;0.34943389892578125;0.7060490250587463;0.5946906208992004;0.8344215750694275;0.7402283549308777;0.7181110382080078;0.9399613738059998;0.474754273891449;0.8659477233886719;0.6731794476509094;0.5860310792922974;0.8269432187080383;0.6621243357658386;0.9018712043762207;0.16715581715106964;0.7798716425895691;0.6982614994049072;0.7238439917564392;0.3195546269416809;0.33606088161468506;0.9407399296760559;0.12761938571929932;0.4983156621456146;0.6218185424804688;0.376723974943161;0.2805907130241394;0.2535332441329956;0.42274144291877747;0.2750594913959503;0.7245036959648132;0.39613473415374756;0.2143271267414093;0.8942157030105591;0.904154896736145;0.5743412375450134;0.8342598676681519;0.38103577494621277;0.378094881772995;0.3904123902320862;0.3552447259426117;0.06399193406105042;0.4152166247367859;0.18316909670829773;0.5279803276062012;0.34462329745292664;0.18379509449005127;0.32667601108551025;0.5761681795120239;0.7347897887229919;0.5167655348777771;0.6422055959701538;0.796186089515686;0.29750776290893555;0.8490681052207947;0.7033715844154358;0.8724914193153381;0.6893782019615173;0.8565508127212524;0.21359650790691376;0.4805832803249359;0.6022573113441467;0.2527337670326233;0.6080479621887207;0.5700401067733765;0.6148760318756104;0.30254653096199036;0.7692290544509888;0.582426130771637;0.41245853900909424;0.15016403794288635;0.5765393972396851;0.10512906312942505;0.49632588028907776;0.7949823141098022;0.4305709898471832;0.12350919097661972;0.18839436769485474;0.6230555176734924;0.3768325746059418;0.3532152771949768;0.9549581408500671;0.49630025029182434;0.6075997948646545;0.13584598898887634;0.827280580997467;0.3856382369995117;0.1912320852279663;0.2699970602989197;0.423796147108078;0.729947030544281;0.5252936482429504;0.4734521806240082;0.23346494138240814;0.7253113985061646;0.43445900082588196;0.47723615169525146;0.8188818693161011;0.5950167179107666;0.7450354099273682;0.25452497601509094;0.19391195476055145;0.6288076043128967;0.4950579106807709;0.7466006278991699;0.57373046875;0.41528478264808655;0.723572850227356;0.6049888134002686;0.7258115410804749;0.16630849242210388;0.5822834968566895;0.6784875392913818;0.4264354407787323;0.8389865756034851;0.8641952276229858;0.5622478723526001;0.08159380406141281;0.6189879179000854;0.5577057003974915;0.6223990321159363;0.21675743162631989;0.6991671323776245;0.16522358357906342;0.6249462962150574;0.7083790898323059;0.34933552145957947;0.977545440196991;0.37116000056266785;0.7449403405189514;0.6440091133117676;0.2998720109462738;0.8731669187545776;0.5879884362220764;0.402153342962265;0.8069369792938232;0.40731126070022583;0.6360102295875549;0.8865074515342712;0.9209293127059937;0.3856956362724304;0.7507022619247437;0.6935693025588989;0.6921491622924805;0.7927030324935913;0.14093494415283203;0.8221965432167053;0.7763500213623047;0.23428697884082794;0.457095742225647;0.7140343189239502;0.7589988112449646;0.13637012243270874;0.3427704870700836;0.5851255655288696;0.8572160005569458;0.23634925484657288;0.7234140038490295;0.6038455367088318;0.16622401773929596;0.8326169848442078;0.6940972208976746;0.5424658060073853;0.43825259804725647;0.8057390451431274;0.4560626745223999;0.6615697741508484;0.2571474611759186;0.44881269335746765;0.5633258819580078;0.7396201491355896;0.27223098278045654;0.4767400324344635;0.2572804391384125;0.49611005187034607;0.3833763003349304;0.3676794767379761;0.18243171274662018;0.7801814079284668;0.6370170712471008;0.3485012650489807;0.28243568539619446;0.3926329016685486;0.6277968883514404;0.6951706409454346;0.8307256698608398;0.12682287395000458;0.11506317555904388;0.29999107122421265;0.8070038557052612;0.8560280203819275;0.7821811437606812;0.9005270004272461;0.8264439105987549;0.6475919485092163;0.8735074996948242;0.3739977180957794;0.7226883769035339;0.5926218628883362;0.877718448638916;0.09953417629003525;0.32689782977104187;0.6549673080444336;0.1692986935377121;0.47318241000175476;0.7680274248123169;0.3282892405986786;0.6635866165161133;0.2332192212343216;0.5281802415847778;0.45868271589279175;0.730778157711029;0.536219596862793;0.18271008133888245;0.5684211254119873;0.3662128150463104;0.7284187078475952;0.39686423540115356;0.4088733196258545;0.2600242495536804;0.6525273323059082;0.3519968092441559;0.1316889226436615;0.22982734441757202;0.29874125123023987;0.5385393500328064;0.6417637467384338;0.306403785943985;0.5589725375175476;0.32303178310394287;0.32794803380966187;0.40766826272010803;0.7760202288627625;0.4301018714904785;0.36636197566986084;0.8068315982818604;0.8983864784240723;0.8675587773323059;0.8858299851417542;0.5820479393005371;0.3261115252971649;0.61245197057724;0.18839238584041595;0.057983554899692535;0.17548373341560364;0.3004657030105591;0.4862184226512909;0.40648752450942993;0.03906034678220749;0.6451963186264038;0.1284782588481903;0.6883745789527893;0.6427353620529175;0.7028566002845764;0.28967875242233276;0.17530010640621185;0.5774348974227905;0.5031706690788269;0.15640252828598022;0.8543764352798462;0.3691538870334625;0.37351754307746887;0.45716139674186707;0.2646753787994385;0.20200379192829132;0.8066661953926086;0.14694714546203613;0.8640887141227722;0.15190812945365906;0.183668315410614;0.4635826647281647;0.25296345353126526;0.2807105481624603;0.03365635126829147;0.28197669982910156;0.5237155556678772;0.2578042149543762;0.12929317355155945;0.058939624577760696;0.04750959202647209;0.14851559698581696;0.050368282943964005;0.12878073751926422;0.006390127819031477;0.08288398385047913;0.018278317525982857;0.06598419696092606;0.20151855051517487;0.016199808567762375;0.061389319598674774;0.04263536259531975;0.011491123586893082;0.01658674329519272;0.042611997574567795;0.01983722113072872;0.0027911204379051924;0.0015444799792021513;0.06918462365865707;0.11372458189725876;0.05027048662304878;0.04779588431119919;0.013035602867603302;0.003749151946976781;0.003924556542187929;0.012047626078128815;0.005050330888479948;0.0005256625008769333;0.005829176865518093;0.004812818951904774;0.005429551005363464;0.0037755875382572412;0.012029862962663174;0.0010672117350623012;0.001497505814768374;0.0004345635825302452;0.0003583100624382496;0.000522080750670284;0.0012925761984661222;0.00211816537193954;0.0005439389497041702;0.0006411633803509176;0.0038387400563806295;0.002095119096338749;0.00011388105485821143;0.0014230716042220592;0.0040051634423434734;0.0002892548800446093;0.00019790699298027903;4.3599531636573374e-05;0.00018885184545069933;3.9857910451246426e-05;8.919644460547715e-05;0.00018657447071745992;5.984870585962199e-05;7.562349492218345e-05;0.00013727345503866673;5.050682375440374e-05;0.00011335516319377348;3.513629053486511e-05;0.000155865796841681;0.0004990343586541712;0.00013611846952699125;0.00020855253387708217;1.718234307190869e-05;0.00010623864363878965;2.2867805455462076e-05;4.5369044528342783e-05;7.00356686138548e-05;0.00014928278687875718;0.0002183359320042655;4.939041900797747e-05;0.00024987495271489024;4.051726500620134e-05;3.178969564032741e-05;9.786349255591631e-05;4.426696978043765e-05;0.00010552451567491516;4.5077256800141186e-05;4.520105358096771e-05;9.533915726933628e-05;0.00021608515817206353;9.043910540640354e-05;2.2357713532983325e-05;2.275425140396692e-05;0.00011961557902395725;7.376066059805453e-05;0.00019079244520980865;4.594388883560896e-05;8.511413761880249e-05;3.742603075806983e-05;3.0865361623000354e-05;8.821799565339461e-05;1.0550208571658004e-05;7.538157660746947e-05;0.0002561160654295236;3.342932541272603e-05;6.793589273001999e-05;9.868600318441167e-05;3.063250187551603e-05;8.840031659929082e-05;0.00011541518324520439;9.752318146638572e-05;7.712610386079177e-05;9.981850598705932e-05;0.00011104129953309894;3.977183223469183e-05;0.00011700733739417046;5.57097046112176e-05;0.0001044633609126322;0.0001970361772691831;5.590656655840576e-05;3.794566146098077e-05;0.0001615644432604313;6.430960638681427e-05;2.7867252356372774e-05;5.25853865838144e-05;0.00013172382023185492;8.033169433474541e-05;0.00019766543118748814;0.0001221445418195799;0.00020569433399941772;3.2761199690867215e-05;5.230501847108826e-05;4.958811405231245e-05;8.604823233326897e-05;0.0001998716325033456;5.354358654585667e-05;3.5072451282758266e-05;8.236509893322363e-05;5.712001075153239e-05;4.620814070221968e-05;5.347960177459754e-05;8.16988613223657e-05;0.00010577839566394687;8.294165309052914e-05;0.00013970026338938624;3.578358155209571e-05;0.00016062850772868842;5.998212145641446e-05;2.7438833058113232e-05;1.923147647175938e-05;0.000133566529257223;2.4766608476056717e-05;3.9850954635767266e-05;3.588473191484809e-05;1.0629902135406155e-05;5.607636194326915e-05;2.581503940746188e-05;2.4760893211350776e-05;5.640082235913724e-05;1.8303331671631895e-05;7.901889330241829e-05;2.5247489247703925e-05;2.5592125894036144e-05;3.3468048059148714e-05;2.5151673980872147e-05;2.3650412913411856e-05;1.2962846085429192e-05;2.1315436242730357e-05;1.0701233804866206e-05;1.0216102054982912e-05;9.369709005113691e-06;1.553429501655046e-05;6.786703579564346e-06;1.0445947737025563e-05;2.344458334846422e-05;9.692879757494666e-06;4.099707803106867e-05;8.286312549898867e-06'

#GAN()
line = Expand(line)
DrawCA(line)
DrawPDB(line)
Design.Whole('DeNovo.pdb')
Design.Pack('DesignedWhole.pdb')
os.system('rm DesignedWhole.pdb')
Fragments('Designed.pdb')
