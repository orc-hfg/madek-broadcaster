#!/bin/sh

#xrandr --output VGA-0 --mode 1920x1080
#xrandr --output VGA-1 --rotate right --mode 1920x1080 --right-of VGA-0 --pos 1920x0
#xrandr --output VGA-2 --mode 1920x1080 --right-of VGA-1 --pos 3000x0

/home/itz/.virtualenvs/broadcaster/bin/python /home/itz/madek-broadcaster/player/main.py > /home/itz/log 2>&1