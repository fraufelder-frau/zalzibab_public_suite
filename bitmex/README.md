# Zalzibab Public Suite: bitmex

## What It Is

Collection of python scripts built specifically for Bitmex

Most scripts include Telegram bot integration

### Telegram Bot Integration

#### Create your bot and get API token and your chatID

API - Message @BotFather on Telegram. /start . Follow prompts

chatID - Message @userinfobot on Telegram. /start .

## One-Liner 1st Time VPS Setup

sudo apt update && sudo apt upgrade -y && sudo apt install python3.7 -y && sudo apt-get install python3-pip -y && sudo apt-get install python3-venv -y && git clone https://github.com/zalzibab/zalzibab_public_suite.git && cd zalzibab_public_suite/bitmex

## How To Use

On initial VPS setup, run one-liner above.

Create a new screen session > screen -S bitmex

Run the following one-liner

python3 -m venv env && source env/bin/activate && python -m pip install -r requirements.txt && git clone https://github.com/qtrade-exchange/qtrade-py-client.git && python -m pip install --upgrade --user git+https://github.com/qtrade-exchange/qtrade-py-client.git && mv qtrade-py-client/qtrade_client .

When your session is complete, detach from the screen session with keyboard input > Ctrl+a d

When you come back > screen -r bitmex will reattach your screen session, already in your python virtual environment

#### To Get Updated Repo

screen -r bitmex && git pull





