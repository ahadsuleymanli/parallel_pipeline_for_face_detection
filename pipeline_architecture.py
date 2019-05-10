# pipeline architecture designed for real-time face detection and more
# the architecture is designed to allow multiple simultaneous consumer threads operate on each frame
# frames are produced by the producer thread
# not every frame gets consumed, only as many as the processing power allows
# this allows for a low latency processing of frames in real time
# this is an architecture for real-time systems
# designed by Ahad Suleymanli using principles from the
# Pipeline design pattern mentioned in McCool Et Al.s Structured Parallel Programming (Morgan Kaufmann, 2012)

from imutils import paths
import numpy as np
import argparse
import imutils
import pickle
import cv2
import os
import queue
import threading
import time

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-fps", "--fps", type=int, default=10, required=True,
    help="target output fps for the pipeline")
ap.add_argument("-det", "--detect_faces", type=int, required=True,
    help="whether or not do face detection")
args = vars(ap.parse_args())


class Pipeline:
    def __init__(self):
        self.wake_up_front_buffer = threading.Event()
        self.wake_up_rear_buffer = threading.Event()

        self.producer_output_queue_lock = threading.Lock()
        self.front_buffer_frame_taken_flag = False

        self.producer_output_queue = queue.Queue()
        self.consumer1_input_queue = queue.Queue()
        self.consumer1_output_queue = queue.Queue()
        self.consumer2_input_queue = queue.Queue()
        self.consumer2_output_queue = queue.Queue()
        self.pipeline_output_queue = queue.Queue()

        self.target_fps = args["fps"]
        self.DETECT_FACES = args["detect_faces"]
        self.vs = None
    def producer(self):
        frame_time_target = 1 / self.target_fps
        start_time = time.time()

        self.vs = cv2.VideoCapture(0)

        while self.vs.isOpened():
            # Capture frame-by-frame
            ret, frame = self.vs.read()
            if ret:
                self.producer_output_queue_lock.acquire()
                if self.producer_output_queue.empty() and ((time.time() - start_time) > (frame_time_target)):
                    # implementing an fps cap
                    start_time = time.time()
                    self.producer_output_queue.put(frame)
                    self.wake_up_front_buffer.set()
                self.producer_output_queue_lock.release()
        self.vs.release()

    def front_buffer(self):
        self.wake_up_front_buffer.set()
        while True:
            self.wake_up_front_buffer.wait()
            # taking the frame from the producer
            # and putting them into ques of consumers

            if self.consumer1_input_queue.empty() and self.consumer2_input_queue.empty():
                self.producer_output_queue_lock.acquire()
                try:
                    frame = self.producer_output_queue.get_nowait()
                    self.consumer1_input_queue.put(frame)
                    self.consumer2_input_queue.put(frame)
                except:
                    pass
                self.producer_output_queue_lock.release()

            self.wake_up_front_buffer.clear()

    def rear_buffer(self):
        self.wake_up_rear_buffer.set()
        consumer1_output_taken = False
        consumer2_output_taken = False
        while True:
            self.wake_up_rear_buffer.wait()
            try:
                frame, completion_time1 = self.consumer1_output_queue.get_nowait()
                consumer1_output_taken = True
            except:
                pass
            try:
                faces, completion_time2 = self.consumer2_output_queue.get_nowait()
                consumer2_output_taken = True
            except:
                pass

            if consumer1_output_taken and consumer2_output_taken:
                print("consumer1:%.0fms" % (completion_time1*1000), "consumer2:%.0fms" % (completion_time2*1000))
                self.pipeline_output_queue.put((frame,faces))

                self.wake_up_front_buffer.set()
                consumer1_output_taken = False
                consumer2_output_taken = False

            self.wake_up_rear_buffer.clear()

    # dummy consumer, fake waiting for 0.05s, add your own process
    def consumer1(self):
        while True:
            frame = self.consumer1_input_queue.get()
            time1 = time.time()

            # fake waiting, here goes the processing intensive task
            time.sleep(0.05)

            x = 10
            y = 10
            w = 330
            h = 30
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
            cv2.putText(frame, 'drawn in consumer1', (x, y+25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            completion_time = time.time() - time1
            self.consumer1_output_queue.put((frame, completion_time))
            self.wake_up_rear_buffer.set()

    # does face detection using opencv's haarcascade
    def consumer2(self):
        if self.DETECT_FACES:
            face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            #eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
        while True:
            frame = self.consumer2_input_queue.get()
            time1 = time.time()

            # comment out face detection and pass an empty array if you have trouble with OpenCV
            if self.DETECT_FACES:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            else:
                faces = []
                x = 10
                y = 40
                w = 330
                h = 30
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
                cv2.putText(frame, 'drawn in consumer2', (x, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,
                            cv2.LINE_AA)

            completion_time = time.time() - time1
            self.consumer2_output_queue.put((faces, completion_time))
            self.wake_up_rear_buffer.set()

    def run_pipeline(self):
        threads = []
        threads.append(threading.Thread(target=self.producer))
        threads.append(threading.Thread(target=self.front_buffer))
        threads.append(threading.Thread(target=self.rear_buffer))
        threads.append(threading.Thread(target=self.consumer1))
        threads.append(threading.Thread(target=self.consumer2))

        print("Starting the pipeline with a target fps of", self.target_fps)
        for thread in threads:
            thread.start()


def output(output_queue):
    while(True):
        frame, faces = output_queue.get()
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            #roi_gray = gray[y:y + h, x:x + w]
            #roi_color = img[y:y + h, x:x + w]
        # Display the resulting frame
        cv2.imshow('frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    # When everything done, release the capture

    cv2.destroyAllWindows()

pipeline = Pipeline()


pipeline.run_pipeline()

output(pipeline.pipeline_output_queue)
