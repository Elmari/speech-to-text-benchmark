# Speech-to-Text Benchmark

Benchmark for german language models, based on the [benchmark]((https://github.com/Picovoice/speech-to-text-benchmark)) of [Picovoice](https://picovoice.ai).
 The speechdata-corpus [Tuda-de v2](https://www.inf.uni-hamburg.de/en/inst/ab/lt/resources/data/acoustic-models.html) is used as the test data set. 

## Installation and Usage

In order to run this benchmark you have to add the Tuda-de_v2 dataset to the resources/data/german-speechdata-package-v2 directory. Also, you have to add credential information for the commercial ASR-engine you want to use. See engine.py as well as the corresponding descriptions of these systems for more details. Via the --engine_type argument you then have to specifiy the engine you want to use. The following values are supported: 
* AMAZON_TRANSCRIBE
* GOOGLE_SPEECH_TO_TEXT
* AZURE_SPEECH_TO_TEXT
* WATSON_SPEECH_TO_TEXT
* MOZILLA_DEEP_SPEECH_05 (uses the deepspeech 0.5 model by Aashish Agarwal and Torsten Zesch - see [deepspeech_german](https://github.com/AASHISHAG/deepspeech-german))
* MOZILLA_DEEP_SPEECH_06 (uses the deepspeech 0.6 model by Aashish Agarwal and Torsten Zesch - see [deepspeech_german](https://github.com/AASHISHAG/deepspeech-german))
* KALDI_SPEECH_TO_TEXT (uses the model by Milde and Köhn - see [kaldi-tuda-de](https://github.com/uhh-lt/kaldi-tuda-de))

In order to use the mozilla models, you have to place the resource files under resources/deepspeech05 or resources/deepspeech06) (see engine.py for details)

In order to use the kaldi model, kaldi has to be accessible via the following url: http://localhost:8080/client/dynamic/recognize. This can be achieved by running kaldi via the [kaldi-gstreamer-server](https://github.com/alumae/kaldi-gstreamer-server) (see engine.py for details). 

## Results

These findings are from May 2020. The following hardware was used for the tests: Mac Mini (2018), 3.6 GHz Quad Core Intel Core i3, 8 GB 2667 MHz DDR4. The average upload speed was 9.5Mbps. The hardware is particularly relevant to the results of Mozilla DeepSpeech and Kaldi, as these were run locally. The other services mentioned are hosted externally and were accessed via API. The total duration is given in the format hour:minute:second.

| | Word error count |	WER, data in percent	| Compound errors |	WER without compound errors, data in percent |	total duration 
|--|--------------|-------------------------|-----------------|----------------------------------------------|------------
Google Speech-to-text |	2143 |	12.32 |	210 |	11.72 |	00:29:48
Amazon Transcribe |	2307 |	13.26 |	428 | 12.05 | 20:26:01
Azure Speech to text |	2114 |	12.15 |	184 |	11.62 |	01:14:02
Watson Speech to text |	3418	| 19.64 |	369 |	18.61 |	00:52:54
Mozilla DeepSpeech 0.5.0 | 	12721 |	73.11 |	91	| 72.85 |	01:56:00
Mozilla DeepSpeech 0.6.0 |	5585 |	32.10 |	184 |	31.63 |	01:05:00
Kaldi |	2965	| 17.04 |	511 |	15.71 |	04:26:42
