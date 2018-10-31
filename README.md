# viz_pupil_integration (beta status)
Harun Karimpur, 2018
harun.karimpur@psychol.uni-giessen.de

Integration for Pupil Labs Eye Tracker (120Hz) in Vizard with HTC Vive HMD. 



## Calibration routine
##### Preparations
 1. Open Vizard (run as administrator) and pupil service
 2. Open file in vizard _(top left via „open…“)_
 3. Compare IP-adresses in file and pupil service (and in your experiment file). 

>If they don’t match, change the IP-adress in the file „calibration routine“!

4. Setup "pupil service" and make sure that eyes are tracked corretly.   

##### Calibration

1. Start the calibration routine through _clicking  on the green arrow_ in Vizard 
* by pressing the _space bar_ you start the 9-point-calibration routine. 
* On your monitor you can see the same scene as the subject: a white dot (which represents the point of fixation) on a grey background. 
2. By pressing the _space bar_ once, you start the sampling process of one specific point in space. 
* Here, the subjects' task is to fixate the dot until it turns red. After the sampling process has finished, the subjects are allowed to blink again to make the calibration procedure as comfortable as possible. 
3. You can press the _space bar_ to start the next trial (i.e., point).

> Let the subjects signalize when they are ready to fixate the next dot. But keep in mind that it is **important** that they move their head as less as possible during the whole procedure!

##### Notes on calibration

After the **subjects' signal** (see above) you press the _space bar_ to measure _(calibration step 2)_.
* If subjects report a bar or a splash screen signalling loading, pupil signals may be missing. Check **pupil service** and start the calibration process again.

* If the dot remains white...
  * even after pressing the _space bar_ to measure and subjects' fixation
  * or subjects indicate to see a „light cone“ or a „line“ instead of a dot it could be that the peripherie is too blurred,
* ...the position of the VR-glasses has to be checked.
  
  >Remember to click „reset 3d model“ in pupil service if you change the position of the glasses or anything in the settings! 

 Calibration ends automatically after collected data of all nine dots.

##### Validation
Validation, which is similar to the calibration sequence, starts automatically by _pressing the space bar_.

At the end of the validation routine a grid of blue and orange dots appears. The blue dots represent the ground truth (9 calibration points), the orange dots are subjects average gaze points.

In the _Vizard console_ the **mean angular error** will be reported. On average the error should be smaller than 1.0°.