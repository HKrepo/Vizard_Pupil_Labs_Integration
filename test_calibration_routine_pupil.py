''' 
Vizard 5 (Worldviz) Calibration routine for Pupil Labs 120Hz Eye Tracker in connection
with HTC Vive HMD

Harun Karimpur, 2018
harun.karimpur@psychol.uni-giessen.de

TODO: 'implement validation'
'''



import sys
import viz
import vizfx
import vizact
import vizinfo
import viztask
import vizshape
import zmq, msgpack, time
import numpy as np
import steamvr



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
req.connect('tcp://134.176.175.219:50020')

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

# start calibration routine with params. This will make pupil start sampeling pupil data.
n = {'subject':'calibration.should_start', 'hmd_video_frame_size':(2160,1200), 'outlier_threshold':35}
print(send_recv_notification(n))



def showMessage(msg):
	"""	Show a message in the virtual environment until keypress """
	
	message = vizinfo.InfoPanel(msg, align=viz.ALIGN_CENTER_CENTER, fontSize=22, icon=False, key=None)
	message.setPosition(.5, .5, mode=viz.RELATIVE)
	#hmd.addWindowMessage(message)
	yield viztask.waitKeyDown(' ')
	message.remove()



beep = viz.playSound('beep500_200.wav', viz.SOUND_PRELOAD)

norm_positions = [
[.20, .80],#LT
[.80, .80],#RT
[.50, .50],#CC
[.20, .20],#LB
[.80, .20],#RB
[.20, .50],#LC
[.50, .20],#CB
[.80, .50],#RC
[.50, .80]]#CT



def calibration():
	''' The heart of the calibration routine. Presents points and collects data. '''

	ref_data = []

	depth = 2 # m	

	sphere_size = .015
	
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

mytask = viztask.schedule( calibration )