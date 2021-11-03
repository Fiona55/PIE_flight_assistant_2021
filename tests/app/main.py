# Start with a basic flask app webpage.
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, url_for, copy_current_request_context, request
from random import random
from time import sleep
from threading import Thread, Event

from flight_data_handler import *

import logging


# ========= FLASK APP INIT ============
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True
log = logging.getLogger('werkzeug')
log.disabled = True
sio = SocketIO(app, async_mode=None, logger=False, engineio_logger=False)

thread = Thread()
thread_stop_event = Event()

airspace_worker = None
thread = Thread()
USE_RADAR = True


# ============ BACKGROUND TASKS =================
class AirspaceBackgroundWorker:
    switch = False

    def __init__(self, sio, box=None, center=None):
        self.sio = sio
        self.switch = True
        self.box = box
        self.center = center
        self.flight_data_process = FlightRadar24Handler()
        fprint("----- Background airspace worker initialized -----")

    def do_work(self):
        namespace = '/test'
        fprint("----- Begin trafic worker -----")
        while self.switch:
            try:
                # Handle traffic
                if USE_RADAR:
                    dict_message = self.flight_data_process.get_current_airspace(center=self.center)
                else:
                    dict_message = self.flight_data_process.get_current_airspace(box=self.box)
            
                # Handle airports
                # get_near_airports(dict_message, self.center)
                dict_message['list_airports'] = []
                
                self.sio.emit('airspace', dict_message)
                fprint(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), f"# Flights : {dict_message['number_flights']}", f"# Airports : {len(dict_message['list_airports'])}")
                self.sio.sleep(1)

            except Exception as e:
                fprint(f"Error : {str(e)}")
    
    
    def update_box(self, box):
        self.box = box
    
    def update_center(self, center):
        self.center = center

    def stop(self):
        self.switch = False



@app.route('/')
def index():
    print(request)
    start_work("start")
    return render_template('index.html')



def start_work(sid):
    global thread, airspace_worker
    toulouse_lat, toulouse_long = 43.59972466458162, 1.4492797572165728
    min_lat, max_lat = toulouse_lat - 1, toulouse_lat + 1
    min_long, max_long = toulouse_long - 2, toulouse_long + 2
    box = (min_lat, max_lat, min_long, max_long)
    center = (toulouse_lat, toulouse_long)

    if not thread.is_alive():
        if airspace_worker is not None:
            if USE_RADAR: airspace_worker.update_center(center)
            else: airspace_worker.update_box(box)
        else:
            airspace_worker = AirspaceBackgroundWorker(sio, box=box, center=center)
            sio.start_background_task(airspace_worker.do_work)
    


@sio.on('change_focus')
def get_change_focus(data):
    fprint(f"Change focus : {data}")
    if USE_RADAR:
        center = (data['latitude'], data['longitude'])
        airspace_worker.update_center(center)
    else:
        min_lat, max_lat = data['latitude'] - 1, data['latitude'] + 1
        min_long, max_long = data['longitude'] - 2, data['longitude'] + 2
        box = (min_lat, max_lat, min_long, max_long)
        airspace_worker.update_box(box)



@sio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    sio.run(app)
