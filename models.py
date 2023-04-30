from datetime import datetime

class PrivacyChannel():

    def __init__(self, role, voice, text, password, duration):
        self.role = role
        self.voice = voice
        self.text = text
        self.password = password
        self.duration = duration
        self.time = datetime.now()

    def expired(self):
        delta = datetime.now() - self.time
        return delta.total_seconds() >= self.duration

    def __repr__(self):
        return f'{self.role=} {self.voice=} {self.text=} {self.password=} {self.duration=} {self.time=}'
