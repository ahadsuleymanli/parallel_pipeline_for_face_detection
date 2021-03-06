# parallel_pipeline_for_face_detection
Pipeline architecture designed for real-time face and object detection applications.

The architecture is designed to allow multiple simultaneous consumer threads operate on each frame.
Frames are produced by the producer thread.
Not every frame gets consumed, only as many as the processing power allows.
This allows for a low latency processing of frames in real time.
This is an architecture for real-time systems.

Designed by Ahad Suleymanli using principles from the 
Pipeline design pattern mentioned in McCool Et Al.s Structured Parallel Programming (Morgan Kaufmann, 2012)

# To run:
python pipeline_architecture.py -fps 10 -det 1

# Troubleshooting:
Use -det 0 if you get problems with openCV

If you're familiar with openCV face detection, it's easy to fix if face detection doesn't work on your machine.
