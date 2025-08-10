class SpeechRecognizer:
    def __init__(self, recognizer, source_provider):
        self.source_provider = source_provider
        self.recognizer = recognizer