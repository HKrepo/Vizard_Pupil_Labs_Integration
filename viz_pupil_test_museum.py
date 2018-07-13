'''
Vizard 5 (Worldviz) test scene for pupil labs eye tracker with HTC Vive HMD [based on the museum example].

Harun Karimpur, 2018
harun.karimpur@psychol.uni-giessen.de
'''



import viz
import vizact
import vizshape
import sys
import steamvr
import zmq
from msgpack import loads
import numpy as np



# open a port to talk to pupil
context = zmq.Context()
addr = '134.176.175.219'  # remote ip or localhost
req_port = "50020"  # port (check pupil service)
req = context.socket(zmq.REQ)
req.connect("tcp://{}:{}".format(addr, req_port))

# ask for the sub port
req.send_string('SUB_PORT')
sub_port = req.recv_string()

# open a sub port to listen to pupil
sub = context.socket(zmq.SUB)
sub.connect("tcp://{}:{}".format(addr, sub_port))
sub.setsockopt_string(zmq.SUBSCRIBE, u'gaze')



# start viz
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



# create skylight
viz.MainView.getHeadLight().disable()
sky_light = viz.addLight(euler=(0,90,0))
sky_light.position(0,0,-1,0)
sky_light.color(viz.WHITE)
sky_light.ambient([0.9,0.9,1])

# add the gallery model
gallery = viz.addChild('gallery.osgb')

# add audio and video
music = viz.addAudio('bach_air.mid',loop=1)
video = viz.addVideo('vizard.mpg',play=1,loop=1)

# get a handle to Starry Night texture
painting = gallery.getTexture('painting_starry-night')

# add an avatar
avatar = viz.addAvatar('vcc_male2.cfg',pos=[0,0,1])
avatar.state(1)

# create static drop shadow to avatar
shadow_texture = viz.addTexture('shadow.png')
shadow = vizshape.addQuad(parent=avatar,axis=vizshape.AXIS_Y)
shadow.texture(shadow_texture)
shadow.zoffset()

# move avatar around the room with a sequence of walk, turn, and wait actions

# create action to wait 5-10 seconds
RandomWait = vizact.waittime(vizact.randfloat(5,10))

# list of painting locations
avatarMove = [[-3.7,2.2,300],[-3.7,6.5,270],[0,8,0],[3.7,6.5,90],[3.7,2.6,90],[3.7,1,130]]
actions = []
for loc in avatarMove:
	#Add an action to walk to the next painting, turn towards it, and wait a few seconds
	actions.append(vizact.method.playsound('footsteps.wav',viz.LOOP))
	actions.append(vizact.walkTo([loc[0],0,loc[1]],turnSpeed=250.0))
	actions.append(vizact.method.playsound('footsteps.wav',viz.STOP))
	actions.append(vizact.turn(loc[2],250.0))
	actions.append(RandomWait)

# repeat the sequence of actions forever
avatar.addAction(vizact.sequence(actions,viz.FOREVER))



# add gaze marker
m_gaze = vizshape.addSphere(radius=.1, color=viz.GREEN)
m_gaze.disable(viz.INTERSECTION)



def get_gaze(eye_number):
	'''
	checks gaze stream for confident measures of the eye (eye_number) until it finds them
	Args:    eye_number (int): 1=left, 0=right
	Returns: [x, y] (float): normalized x and y values range [0,1]
	'''

	confidence_level = .3
	
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