#!/bin/sh
gunicorn --worker-class eventlet -w 1 app:app -b 0.0.0.0:$PORT