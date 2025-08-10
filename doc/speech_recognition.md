Yandex Cloud SpeechKit v3 API for streaming speech-to-text recognition.

Result of recognition process is 
`Iterator[stt_pb2.StreamingResponse]` JSON Object

Format of [`StreamingResponse`](./StreamingResponse.json) Object:

```python
response:stt_pb2.StreamingResponse
response.final.alternatives[0].text
response.partial.alternatives[0].text
response.final_refinement.normalized_text.alternatives[0].text
```

Each `StreamingResponse` Object has fields: 'partial', 'final', 'eou_update', 'final_refinement', 'status_code', 'classifier_update', 'speaker_analysis', 'conversation_analysis', 'summarization'

Results:

* **partial** -

Partial results, server will send them regularly after enough audio data was received from user. This are current text estimation from final_time_ms to partial_time_ms. Could change after new data will arrive.

* **final** -

Final results, the recognition is now fixed until final_time_ms. For now, final is sent only if the EOU event was triggered. This could be change in future releases.

* **final_refinement** -

For each final, if normalization is enabled, sent the normalized text (or some other advanced post-processing). Final normalization will introduce additional latency.


Text of 

Эркин экин эккан экан.

Yuz marta yuzingni yuv,
Yuzingda yuz tabassum bo‘lsin.

Qoʻpin goʻyib
Qor bobo
Qoʻl qopini yedirib
Kiyish uchun qalpogʻin
Qulogʻiga qoʻndirib

Qoʻpin qoʻyib Qor bobo
Qoʻl qopini qidirdi.
Qorgiz qalin qalpog'in
Qulog'iga qo'ndirdi.

Qoʻpin qoʻyib Qorbobo 
Qoʻl qopini qidiradi.
Qorqiz qalin qalpog'in 
Qulog'iga qo'ndirdi.
