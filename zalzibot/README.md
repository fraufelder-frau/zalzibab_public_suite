# Zalzibab Public Suite: Zalzibot

## What It Is

Telgram Bot for Hourly Bitmex XBTUSD Updates, 8hr Bitmex Funding Updates, and Daily Bitmex, FTX, and Bybit Updates

### One-Liner 1st Time VPS Setup

sudo apt update && sudo apt upgrade -y && sudo apt install python3.7 -y && sudo apt-get install python3-pip -y && git clone https://github.com/zalzibab/zalzibab_public_suite.git && cd ~/zalzibab_public_suite/zalzibot

### How To Use

On initial VPS setup, run one-liner above.

Create a new screen session > screen -S zalzibot

Run the following one-liner

sudo apt-get install python3-venv -y && python3 -m venv zalzibot && source zalzibot/bin/activate && python3 -m pip install -r requirements.txt && python zalzibot.py

When your session is complete, detach from the screen session with keyboard input > Ctrl+a d

When you come back > screen -r zalzibot will reattach your screen session, already in your python virtual environment

#### To Get Updated Repo

screen -r risk_management

cd ~/zalzibab_public_suite/zalzibot && git pull && python zalzibot.py







