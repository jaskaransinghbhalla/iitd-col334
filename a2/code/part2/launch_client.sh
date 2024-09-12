#!/bin/bash
osascript -e "tell app \"Terminal\" to do script \"$PWD/client $1; read -p 'Press Enter to close...'\"" &