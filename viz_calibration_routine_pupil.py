''' 
Vizard 5 (Worldviz) Calibration routine for Pupil Labs 120Hz Eye Tracker in connection
with HTC Vive HMD

Harun Karimpur, 2018
harun.karimpur@psychol.uni-giessen.de
'''
#TODO: showmessage func doesn't work in Vive HMD



import sys
import viz
import vizfx
import vizact
import vizinfo
import viztask
import vizshape
import zmq, msgpack, time
from msgpack import loads
import numpy as np
import steamvr



# global parameters

gaze_marker_visible = True # True for debugging
beep = viz.playSound('beep500_200.wav', viz.SOUND_PRELOAD)

norm_positions = [
[.30, .70],#LT
[.70, .70],#RT
[.50, .50],#CC
[.30, .30],#LB
[.70, .30],#RB
[.30, .50],#LC
[.50, .30],#CB
[.70, .50],#RC
[.50, .70]]#CT

sphere_size = .015
depth = 2 # m
confidence_level = .2





# initialize window
viz.setMultiSample(8)
viz.fov(60)
viz.go()

# setup SteamVR HMD
hmd = steamvr.HMD()
if not hmd.getSensor():
	sys.exit('SteamVR HMD not detected')
	
# setup navigation node and link to main view
navigationNode = viz.addGroup()
viewLink = viz.link(navigationNode, viz.MainView)
viewLink.preMultLinkable(hmd.getSensor())



# create a zmq REQ socket to talk to Pupil Service
ctx = zmq.Context()
req = ctx.socket(zmq.REQ)
addr = '134.176.175.219'
sub_port = '50020'
req.connect("tcp://{}:{}".format(addr, sub_port))

# convenience functions
def send_recv_notification(n):
	# REQ REP requirese lock step communication with multipart msg (topic,msgpack_encoded dict)
	req.send_string('notify.%s'%n['subject'], flags=zmq.SNDMORE)
	req.send(msgpack.dumps(n))#, use_bin_type=True))
	return req.recv_string()

def get_pupil_timestamp():
    req.send_string('t')
    return float(req.recv_string())

# set start eye windows
n = {'subject':'eye_process.should_start.0','eye_id':0, 'args':{}}
print(send_recv_notification(n))
n = {'subject':'eye_process.should_start.1','eye_id':1, 'args':{}}
print(send_recv_notification(n))
time.sleep(2)

# set calibration method to hmd calibration
n = {'subject':'start_plugin','name':'HMD_Calibration', 'args':{}}
print(send_recv_notification(n))



def showMessage(msg):
	"""	Show a message in the virtual environment until keypress """
	
	message = vizinfo.InfoPanel(msg, align=viz.ALIGN_CENTER_CENTER, fontSize=22, icon=False, key=None)
	message.setPosition(.5, .5, mode=viz.RELATIVE)
	#hmd.addWindowMessage(message)
	yield viztask.waitKeyDown(' ')
	message.remove()



###########################################################
# CALIBRATION SECTION
###########################################################


def calibration():
	''' The heart of the calibration routine. Presents points and collects data. '''


	# start calibration routine and sample data
	n = {'subject':'calibration.should_start', 'hmd_video_frame_size':(2160,1200), 'outlier_threshold':35}
	print(send_recv_notification(n))


	ref_data = []
	
	yield showMessage('Zum Starten die Leertaste drücken')
	
	for p in norm_positions:
		
		print('calibration point: ', p)
	
		norm_x = p[0]
		norm_y = p[1]
		
		first_run = True
		
		if first_run:
			
			first_run = False
		
			'''set up a plane 'right in front of user' on which we want to project the dots'''
	
			# target the current center of view
			p_line = viz.MainWindow.screenToWorld(.5, .5)
		
			# let's modify the line and call it line 2. Here we let the line end at the "depth" value
			p_line_2 = viz.Line(begin=p_line.begin, end=p_line.end, dir=p_line.dir, length=depth)
						
			# Add the plane and apply the matrix of our viewpoint to the plane
			plane = vizshape.addBox(size=[3.6, 2, .1])
			mymat = viz.MainView.getMatrix()
			plane.setMatrix(mymat)
			
			# Reposition the plane to the end of line 2
			plane.setPosition(p_line_2.end)
			plane.color([.25,.25,.25])
			plane.alpha(.95)
			
			# Lock it to user
			plane_link = viz.grab(viz.MainView, plane)
		
		
		# interpolate a line from norm values to 3d coordinates
		line = viz.MainWindow.screenToWorld([norm_x, norm_y])
		
		# find the intersection
		intersection = viz.intersect(line.begin, line.end)
		
		# place a dot (at depth level of line) 
		dot = vizshape.addSphere(radius=sphere_size)
		dot.setPosition(intersection.point)
		
		# lock dot to user
		view_link = viz.grab(viz.MainView, dot)
		
		print('ready')
		viz.playSound('beep500_200.wav')
		yield viztask.waitKeyDown(' ')
				
		for s in range(60):
			
			# get the current pupil time (pupil uses CLOCK_MONOTONIC with adjustable timebase).
			# You can set the pupil timebase to another clock and use that.
			t = get_pupil_timestamp()

			# here the left and right screen marker positions are identical.
			datum0 = {'norm_pos':p,'timestamp':t,'id':0}
			datum1 = {'norm_pos':p,'timestamp':t,'id':1}
			ref_data.append(datum0)
			ref_data.append(datum1)
			yield viztask.waitTime(1/60.)
			print(t)
		
		dot.color(viz.RED)
		
		print('waiting for next position...')
		
		yield viztask.waitKeyDown(' ')
		
		yield dot.remove()
		
	

	# send ref data to Pupil Capture/Service:
	# this notification can be sent once at the end or multiple times.
	# during one calibraiton all new data will be appended.
	n = {'subject':'calibration.add_ref_data','ref_data':ref_data}
	print(send_recv_notification(n))

	# stop calibration
	# pupil will correlate pupil and ref data based on timestamps,
	# compute the gaze mapping params, and start a new gaze mapper.
	n = {'subject':'calibration.should_stop'}
	print(send_recv_notification(n))

	time.sleep(2)
		
	vizinfo.InfoPanel('calibration done!')

	plane.remove()
	
	yield viztask.waitTime(2)

	vizinfo.InfoPanel.remove()



###########################################################
# VALIDATION SECTION
###########################################################


def validation():
	'''
	Show same calibration points and compare calulated gaze point to ground truth. 
	(Displays both + angular error)
	'''
	
	# ask for the sub port
	req.send_string('SUB_PORT')
	sub_port = req.recv_string()

	# open a sub port to listen to pupil
	sub = ctx.socket(zmq.SUB)
	sub.connect("tcp://{}:{}".format(addr, sub_port))
	sub.setsockopt_string(zmq.SUBSCRIBE, u'gaze')

	# add gaze marker
	m_gaze = vizshape.addSphere(radius=sphere_size, color=viz.GREEN)
	m_gaze.disable(viz.INTERSECTION)
	if not gaze_marker_visible:
		m_gaze.disable(viz.RENDER) # invisible but phyisically present



	def get_gaze(eye_number):
		'''
		checks gaze stream for confident measures of the eye (eye_number) until it finds them
		Args:    eye_number (int): 1=left, 0=right
		Returns: [x, y] (float): normalized x and y values range [0,1]
		'''
		found_confident_val = False
		
		while found_confident_val == False:

			topic = sub.recv_string() # unused
			msg = sub.recv()
			msg = loads(msg, encoding='utf-8')
			
			confidence = msg['confidence']
			
			if msg['id'] == eye_number:
				
				if confidence > confidence_level:
				
					found_confident_val = True
					
					t = msg['timestamp'] # unused
					npx = msg['norm_pos'][0]
					npy = msg['norm_pos'][1]
					
					return [npx, npy]


	def updateGaze():	
		'''
		calls 'get_gaze function' and takes the average of two
		eyes for the normal values - they will be used to project a 
		sphere on where subjects look at
		'''
		
		# get gaze data
		norm_pos_x = np.mean([get_gaze(1)[0], get_gaze(0)[0]])
		norm_pos_y = np.mean([get_gaze(1)[1], get_gaze(0)[1]])
				
		# find the intersection and project sphere
		line = viz.MainWindow.screenToWorld([norm_pos_x, norm_pos_y])
		intersection = viz.intersect(line.begin, line.end)
		m_gaze.setPosition(intersection.point)
		
	# update cursor location on every sample		
	vizact.onupdate(viz.PRIORITY_LINKS+1, updateGaze)


	dot_norm_pos=[]
	gaze_norm_pos=[]
	ang_error = []


	yield showMessage('Zum Starten der Validierung die Leertaste drücken')
	
	for p in norm_positions:
		
		print('calibration point: ', p)
	
		norm_x = p[0]
		norm_y = p[1]
		
		first_run = True
		
		if first_run:
			
			first_run = False
		
			'''set up a plane 'right in front of user' on which we want to project the dots'''
	
			# target the current center of view
			p_line = viz.MainWindow.screenToWorld(.5, .5)
		
			# let's modify the line and call it line 2. Here we let the line end at the "depth" value
			p_line_2 = viz.Line(begin=p_line.begin, end=p_line.end, dir=p_line.dir, length=depth)
						
			# Add the plane and apply the matrix of our viewpoint to the plane
			plane = vizshape.addBox(size=[3.6, 2, .1])
			mymat = viz.MainView.getMatrix()
			plane.setMatrix(mymat)
			
			# Reposition the plane to the end of line 2
			plane.setPosition(p_line_2.end)
			plane.color([.25,.25,.25])
			plane.alpha(.95)
			
			# Lock it to user
			plane_link = viz.grab(viz.MainView, plane)
		
		
		# interpolate a line from norm values to 3d coordinates
		line = viz.MainWindow.screenToWorld([norm_x, norm_y])
		
		# find the intersection
		intersection = viz.intersect(line.begin, line.end)
		
		# place a dot (at depth level of line) 
		dot = vizshape.addSphere(radius=sphere_size)
		dot.setPosition(intersection.point)
		
		# lock dot to user
		view_link = viz.grab(viz.MainView, dot)
		
		print('ready')
		viz.playSound('beep500_200.wav')
		yield viztask.waitKeyDown(' ')
				
		for s in range(60):
			
			# get the current pupil time (pupil uses CLOCK_MONOTONIC with adjustable timebase).
			# You can set the pupil timebase to another clock and use that.
			t = get_pupil_timestamp()

			dot_norm_pos.append(p)
			gaze_norm_pos.append(viz.MainWindow.worldToScreen(m_gaze.getPosition()))

			yield viztask.waitTime(1/60.)
			print(t)
		
		dot.color(viz.RED)
		
		print('waiting for next position...')
		
		yield viztask.waitKeyDown(' ')
		
		yield dot.remove()
				
	time.sleep(2)
		
	vizinfo.InfoPanel('validation done!')
	
	for p in norm_positions:
		
		i = norm_positions.index(p)
		chunk = range(i*60, (i+1)*60)
		print(i)
		dmx = np.mean([gaze_norm_pos[x][0] for x in chunk])
		dmy = np.mean([gaze_norm_pos[y][1] for y in chunk])
		
		# interpolate a line from norm values to 3d coordinates
		line = viz.MainWindow.screenToWorld([p[0], p[1]])
		line_v = viz.MainWindow.screenToWorld([dmx, dmy])
		
		# find the intersection
		intersection = viz.intersect(line.begin, line.end)
		intersection_v = viz.intersect(line_v.begin, line_v.end)
		
		# place a dots (at depth level of line) for both ground truth and gaze point
		dot = vizshape.addSphere(radius=sphere_size)
		dot.setPosition(intersection.point)
		dot.color(viz.BLUE)
		
		dot_v = vizshape.addSphere(radius=sphere_size*0.75)
		dot_v.setPosition(intersection_v.point)
		dot_v.color(viz.YELLOW_ORANGE)
		
		# lock dots to user
		view_link = viz.grab(viz.MainView, dot)
		viel_link2 = viz.grab(viz.MainView, dot_v)
		
		# calculate angular error
		a = line
		b = line_v
		cosangle = np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))
		angle = np.arccos(cosangle)
		error = np.degrees(angle)
		
		ang_error.append(error)
		
		print('angle is: ', error, 'for ', p)
	
	print('mean angular error is: ', np.mean(ang_error), ' deg/ visual angle')

# run in sequence
def validation_schedule():
	yield calibration()
	yield validation()

validation_task = viztask.schedule(validation_schedule)