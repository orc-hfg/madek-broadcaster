#!/bin/sh

age=$(stat -c %Y ~/player_log/last_media_entry.txt)
now=$(date +"%s")
age=$((now - age))
if [ "$age" -gt 300 ]; then
    /home/itz/madek-broadcaster/service/service_restart.sh
fi
