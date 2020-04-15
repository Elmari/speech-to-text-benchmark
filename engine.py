import json
import os
import string
import time
import uuid
from enum import Enum

import azure.cognitiveservices.speech as speechsdk
import boto3
import numpy as np
import requests
# from deepspeech import Model
import soundfile
from deepspeech import Model
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import SpeechToTextV1


class ASREngines(Enum):
    AMAZON_TRANSCRIBE = "AMAZON_TRANSCRIBE"
    GOOGLE_SPEECH_TO_TEXT = "GOOGLE_SPEECH_TO_TEXT"
    AZURE_SPEECH_TO_TEXT = "AZURE_SPEECH_TO_TEXT"
    WATSON_SPEECH_TO_TEXT = "WATSON_SPEECH_TO_TEXT"
    MOZILLA_DEEP_SPEECH_05 = 'MOZILLA_DEEP_SPEECH_05'
    MOZILLA_DEEP_SPEECH_06 = 'MOZILLA_DEEP_SPEECH_06'
    KALDI_SPEECH_TO_TEXT = 'KALDI_SPEECH_TO_TEXT'


class ASREngine(object):
    def transcribe(self, path):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    @classmethod
    def create(cls, engine_type):
        if engine_type is ASREngines.AMAZON_TRANSCRIBE:
            return AmazonTranscribe()
        elif engine_type is ASREngines.GOOGLE_SPEECH_TO_TEXT:
            return GoogleSpeechToText()
        elif engine_type is ASREngines.WATSON_SPEECH_TO_TEXT:
            return WatsonSpeechToText()
        elif engine_type is ASREngines.MOZILLA_DEEP_SPEECH_05:
            return MozillaDeepSpeech05ASREngine()
        elif engine_type is ASREngines.MOZILLA_DEEP_SPEECH_06:
            return MozillaDeepSpeech06ASREngine()
        elif engine_type is ASREngines.KALDI_SPEECH_TO_TEXT:
            return KaldiSpeechToTextASREngine()
        elif engine_type is ASREngines.AZURE_SPEECH_TO_TEXT:
            return AzureSpeechToText()
        else:
            raise ValueError("cannot create %s of type '%s'" % (cls.__name__, engine_type))


class AmazonTranscribe(ASREngine):
    def __init__(self):
        self._s3 = boto3.client('s3')
        self._s3_bucket = str(uuid.uuid4())
        self._s3.create_bucket(
            ACL='private',
            Bucket=self._s3_bucket,
            CreateBucketConfiguration={'LocationConstraint': 'eu-central-1'})

        self._transcribe = boto3.client('transcribe')

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.aws')

        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        job_name = str(uuid.uuid4())
        s3_object = os.path.basename(path)
        self._s3.upload_file(path, self._s3_bucket, s3_object)

        self._transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': 'https://s3-us-west-2.amazonaws.com/%s/%s' % (self._s3_bucket, s3_object)},
            MediaFormat='wav',
            LanguageCode='de-DE')

        while True:
            status = self._transcribe.get_transcription_job(TranscriptionJobName=job_name)
            print("Status: %s" % status['TranscriptionJob']['TranscriptionJobStatus'])
            if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
                break
            time.sleep(5)

        content = requests.get(status['TranscriptionJob']['Transcript']['TranscriptFileUri'])

        res = json.loads(content.content.decode('utf8'))['results']['transcripts'][0]['transcript']
        res = res.translate(str.maketrans('', '', string.punctuation))

        with open(cache_path, 'w') as f:
            f.write(res)

        return res

    def __str__(self):
        return 'Amazon Transcribe'


class GoogleSpeechToText(ASREngine):
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ""
        self._client = speech.SpeechClient()

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.ggl')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        with open(path, 'rb') as f:
            content = f.read()

        audio = types.RecognitionAudio(content=content)
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='de-DE')

        response = self._client.recognize(config, audio)

        res = ' '.join(result.alternatives[0].transcript for result in response.results)
        res = res.translate(str.maketrans('', '', string.punctuation))

        with open(cache_path, 'w') as f:
            f.write(res)

        return res

    def __str__(self):
        return 'Google Speech-to-Text'


class WatsonSpeechToText(ASREngine):
    def __init__(self):
        self.authenticator = IAMAuthenticator('')
        self.speech_to_text = SpeechToTextV1(authenticator=self.authenticator)
        self.speech_to_text.set_service_url('')

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.watson')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        with open(path, 'rb') as f:
            response = self.speech_to_text.recognize(
                audio=f,
                content_type='audio/wav',
                model='de-DE_BroadbandModel').get_result()

        if 'results' in response and len(response['results']) > 0 and 'alternatives' in response['results'][0]:
            res = response['results'][0]['alternatives'][0]['transcript']
            res = res.translate(str.maketrans('', '', string.punctuation))
        else:
            res = ''
        with open(cache_path, 'w') as f:
            f.write(res)
        return res

    def __str__(self):
        return 'Watson Speech-to-Text'


class MozillaDeepSpeech05ASREngine(ASREngine):
    def __init__(self):
        deepspeech_dir = os.path.join(os.path.dirname(__file__), 'resources/deepspeech05')
        model_path = os.path.join(deepspeech_dir, 'model_tuda+voxforge+mozilla.pb')
        alphabet_path = os.path.join(deepspeech_dir, 'alphabet.txt')
        language_model_path = os.path.join(deepspeech_dir, 'lm.binary')
        trie_path = os.path.join(deepspeech_dir, 'trie')

        # https://github.com/mozilla/DeepSpeech/blob/master/native_client/python/client.py
        # Get mfcc coefficients
        # see also https://github.com/AASHISHAG/deepspeech-german/blob/master/pre-processing/find_erroneous_files.py
        self._model = Model(model_path, 26, 9, alphabet_path, 500)
        self._model.enableDecoderWithLM(alphabet_path, language_model_path, trie_path, 0.75, 1.85)

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.moz')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        pcm, sample_rate = soundfile.read(path)
        pcm = (np.iinfo(np.int16).max * pcm).astype(np.int16)
        res = self._model.stt(pcm, sample_rate)

        with open(cache_path, 'w') as f:
            f.write(res)
        return res

    def __str__(self):
        return 'Mozilla DeepSpeech v0.5'


class MozillaDeepSpeech06ASREngine(ASREngine):
    def __init__(self):
        deepspeech_dir = os.path.join(os.path.dirname(__file__), 'resources/deepspeech06')
        model_path = os.path.join(deepspeech_dir, 'output_graph.pb')
        alphabet_path = os.path.join(deepspeech_dir, 'alphabet.txt')
        language_model_path = os.path.join(deepspeech_dir, 'lm.binary')
        trie_path = os.path.join(deepspeech_dir, 'trie')

        # https://github.com/mozilla/DeepSpeech/blob/master/native_client/python/client.py
        self._model = Model(model_path, 500)
        self._model.enableDecoderWithLM(language_model_path, trie_path, 0.75, 1.85)

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.moz6')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        pcm, sample_rate = soundfile.read(path)  # wave.open(path, 'rb')

        pcm = (np.iinfo(np.int16).max * pcm).astype(np.int16)

        res = self._model.stt(pcm)

        with open(cache_path, 'w') as f:
            f.write(res)
        return res

    def __str__(self):
        return 'Mozilla DeepSpeech v0.6'


class KaldiSpeechToTextASREngine(ASREngine):

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.kal')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        url = 'http://localhost:8080/client/dynamic/recognize'
        payload = open(path, 'rb')
        r = requests.post(url, data=payload.read())
        payload.close()
        time.sleep(10)
        if not r.status_code == 200:
            print("Got status %d" % r.status_code)
            return ""
        res = json.loads(r.content.decode('utf8'))

        if res is None or "hypotheses" not in res:
            print("Server returned nothing.")
            res = ""
            return res
        else:
            print(res)
            res = res["hypotheses"][0]['utterance']
            with open(cache_path, 'w') as f:
                f.write(res)

        return res

    def __str__(self):
        return 'Kaldi Speech to Text'


class AzureSpeechToText(ASREngine):

    def transcribe(self, path):
        cache_path = path.replace('.wav', '.az')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                return f.read()

        cancellation_details = None
        audio_input = speechsdk.audio.AudioConfig(filename=path)
        speech_key = ""
        service_region = "northeurope"
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language="de-DE",
                                                       audio_config=audio_input)

        done = False
        result = None

        def set_result(evt):
            nonlocal result
            result = evt.result

        def stop_cb(evt):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            nonlocal done
            done = True

        # Connect callbacks to the events fired by the speech recognizer
        speech_recognizer.recognized.connect(set_result)
        # stop continuous recognition on either session stopped or canceled events
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        while not done:
            time.sleep(.5)

        speech_recognizer.stop_continuous_recognition()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            res = result.text
            res = res.translate(str.maketrans('', '', string.punctuation))
            with open(cache_path, 'w') as f:
                f.write(res)
            return res
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(result.no_match_details))
            return ''

        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))

        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))

        return ''

    def __str__(self):
        return 'Azure Speech-to-Text'
