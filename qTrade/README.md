# Zalzibab Public Suite: qTrade Tools

## What It Is

Automated csv export of individual qTrade markets with Telegram Bot integration

### One-Liner 1st Time VPS Setup

sudo apt update && sudo apt upgrade -y && sudo apt install python3.7 -y && sudo apt-get install python3-pip -y && sudo apt-get install python3-venv -y && git clone https://github.com/zalzibab/zalzibab_public_suite.git && cd zalzibab_public_suite/qTrade

### How To Use

On initial VPS setup, run one-liner above.

Create a new screen session > screen -S qTrade

Run the following one-liner

python3 -m venv env && source env/bin/activate && python -m pip install -r requirements.txt && git clone https://github.com/qtrade-exchange/qtrade-py-client.git && python -m pip install --upgrade --user git+https://github.com/qtrade-exchange/qtrade-py-client.git && mv qtrade-py-client/qtrade_client .

When your session is complete, detach from the screen session with keyboard input > Ctrl+a d

When you come back > screen -r qTrade will reattach your screen session, already in your python virtual environment

#### To Get Updated Repo

screen -r qTrade && git pull





