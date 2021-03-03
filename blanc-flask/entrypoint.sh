#!/bin/bash
exec gunicorn --config /blanc/gunicorn_config.py wsgi:app