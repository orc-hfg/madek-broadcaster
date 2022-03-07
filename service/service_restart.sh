#!/bin/sh

# /bin/systemctl --user restart player.service
kill -INT $(ps -C python -o pid=)

