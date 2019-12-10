from hcrutils.subsystem import subsystem
from hcrutils.message import messagebody
from .stateMachine import StateMachine
from .flags import Flag
from time import sleep, time
from datetime import datetime
from collections import deque

class ai(subsystem):
    """Main statemachine ai process"""

    def __init__(self, default_state_subs=[], loop_time=0.5):
        self.state_subs = default_state_subs
        self.loop_time = loop_time
        self.last_face_number = 0
        self.last_emotion_read = ""
        self.movement = ("", "")
        self.colour = ("", "")
        self.eyes = ("", "")
        super().__init__("ai", "id_only")


    def _run(self):
        self.robot = StateMachine()
        t1 = time()
        self.status = "Idle()"
        self.last_state = "Idle()"
        while True:
            slp = self.loop_time - (time() - t1)
            if slp > 0:
                sleep(slp)
            t1 = time()
            self.check_messages()
            self.robot.event()
            new_state = self.robot.state
            if self.last_state != new_state:
                #print("state update:", new_state)
                self.last_state = new_state
                self.send_state_update(new_state)

    def check_messages(self):
        # Recieve data
        # Emotion
        emotion = self.get_messages(ref="speech_emotion")
        emotion = emotion[0] if len(emotion) else []
        # Set flags.emotion
        self.robot.flags.emotion = emotion.message
        # Set internal last_eomtion_read
        if emotion and emotion != self.last_emotion_read:
            self.last_emotion_read = emotion.message

        # Question Answers
        answer = self.get_messages(ref="question_answer")
        answer = answer[0] if len(answer) else []

        # Number of faces
        num_faces = self.get_messages(ref="num_faces")
        num_faces = num_faces[0] if len(num_faces) else []
        # Set flags.person
        self.robot.flags.person = bool(num_faces)
        # Set internal last_face_number
        if num_faces and self.last_face_number != num_faces.message:
            self.last_face_number = num_faces.message

        # Log question and answer
        if self.robot.flags.processing == True:
            log = "%i, %i, %i" % (datetime.now(), self.robot.flags.question, answer)
            try:
                f = open("log.csv", 'w')
                f.write(log)
            finally:
                f.close()
            # Tell ai subsystem that processing is done so it will go back to WatchingWaiting()
            self.robot.flags.processing = False

        # prepare movement information
        if self.robot.flags.currentState == "Idle":
            movement_data = ["move", 0] # 0 means idling
            self.movement = (self.movement[1], "idle")
        elif self.robot.flags.currentState == "WatchingWaiting":
            movement_data = ["move", 1] # 1 means following
            self.movement = (self.movement[1], "following")
        elif self.robot.flags.currentState == "WatchingGreeting":
            movement_data = ["move", 1]
            self.movement = (self.movement[1], "following")
        elif self.robot.flags.currentState == "WatchingAskingQuestion":
            movement_data = ["move", 1]
            self.movement = (self.movement[1], "following")
        elif self.robot.flags.currentState == "Timeout":
            movement_data = ["move", 1]
            self.movement = (self.movement[1], "following")

        # Prepare colour and eye information
        if self.robot.flags.emotion == "happy":
            colour_data = ["colour", "yellow"]
            eye_data = ["eye_lids", "bottom_covered"]
            self.colour = (self.colour[1], "yellow")
            self.eyes = (self.eyes[1], "bottom_covered")
        elif self.robot.flags.emotion == "sad":
            colour_data = ["colour", "orange"]
            eye_data = ["eye_lids", "top_covered"]
            self.colour = (self.colour[1], "orange")
            self.eyes = (self.eyes[1], "top_covered")
        elif self.robot.flags.emotion == "thinking":
            colour_data = ["colour", "grey"]
            eye_data = ["eye_lids", "look_to_corner"]
            self.colour = (self.colour[1], "grey")
            self.eyes = (self.eyes[1], "look_to_corner")
        elif self.robot.flags.emotion == "content":
            colour_data = ["colour", "blue"]
            eye_data = ["eye_lids", "wide_open"]
            self.colour = (self.colour[1], "blue")
            self.eyes = (self.eyes[1], "wide_open")
        
        # Case for no interactivity
        if self.robot.flags.interactivity == 0:
            eye_data = ["eye_lids", "no_movement"]

        # Send messages as required
        if self.movement[0] != self.movement[1] and self.robot.flags.interactivity == 2:
            self.send_message("serial_interface", "movement", movement_data)

        if self.colour[0] != self.colour[1] and self.robot.flags.interactivity > 0:
            self.send_message("serial_interface", "colour", colour_data)

        if self.eyes[0] != self.eyes[1] and self.robot.flags.interactivity > 0:
            self.send_message("touch_screen", "eyes", eye_data)

        #Handle remaining messages
        messages = self.get_messages()
        #Subscriber updates
        for m in messages:
            if m.ref == "state_update_subscribe":
                self.state_subs.append(m.sender_id)
            if m.ref == "state_update_unsubscribe" and m.sender_id in self.state_subs:
                self.state_subs.remove(m.sender_id)

    def send_state_update(self, state):
        self.status = state
        for s in self.state_subs:
            self.send_message(s, "ai_state_update", state)
       