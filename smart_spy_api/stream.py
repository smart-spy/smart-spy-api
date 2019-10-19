from dataclasses import dataclass
from time import time

from asgiref.sync import sync_to_async
from base64 import b64encode
from cv2 import VideoCapture, imencode, resize
from datetime import datetime, timedelta

from smart_spy_api.yolov3_tf2 import detect_stream

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <img id='im'>
        <script>
            var ws = new WebSocket("ws://192.168.15.12:8000/users/{user_id}/cameras/{camera_id}/stream/smart-spy/ws");
            var im = document.getElementById("im");
            //var ctx = im.getContext("2d");

            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                console.log(data.predicted)
                im.setAttribute("src", "data:image/png;base64," + data.image);
                //ctx.beginPath();
                //ctx.rect(20, 20, 150, 100);
                //ctx.stroke();
            };
        </script>
    </body>
</html>
"""


@dataclass
class Stream:
    video_capture: VideoCapture
    connection_string: str
    active: bool = False
    last_response: str = None
    run_until: datetime = None


class StreamService:
    streams = {}

    @staticmethod
    @sync_to_async
    def add(connection_string):
        if StreamService.streams.get(connection_string):
            return

        cap = VideoCapture(connection_string)
        stream = Stream(video_capture=cap, connection_string=connection_string)
        StreamService.streams[connection_string] = stream

    @staticmethod
    @sync_to_async
    def read(connection_string):
        stream = StreamService.streams[connection_string]
        return stream.last_response

    @staticmethod
    @sync_to_async
    def is_active(connection_string):
        stream = StreamService.streams[connection_string]
        return stream.stop_time > datetime.utcnow()
        return stream.active

    @staticmethod
    def stop_time(seconds):
        return datetime.utcnow() + timedelta(seconds=seconds)

    @staticmethod
    @sync_to_async
    def run_x_seconds(connection_string, fps=1, seconds=30, detect=False):
        stream = StreamService.streams[connection_string]
        stream.stop_time = StreamService.stop_time(seconds)

        if stream.active:
            return

        if not stream.video_capture.isOpened():
            stream.video_capture = VideoCapture(stream.connection_string)

        stream.active = True
        prev = 0
        while datetime.utcnow() < stream.stop_time:
            time_elapsed = time() - prev
            _, frame = stream.video_capture.read()

            if time_elapsed > 1.0 / fps:
                prev = time()

                frame = resize(frame, (320, 320))
                _, buffer = imencode('.jpg', frame)
                jpg_as_text = b64encode(buffer).decode('utf8')

                resp = dict(image=jpg_as_text)
                if detect:
                    resp['predicted'] = detect_stream.DetectorService.predict(frame)
                    print(resp)

                stream.last_response = resp

        stream.active = False
        stream.video_capture.release()
