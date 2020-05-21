# Zalzibab Public Suite: Bitmex & Bybit XBT/BTC Risk Calculator

## What It Is

Position size calculator, order exececution, position management, for all XBT Bitmex contracts and BTCUSD Bybit contract

### One-Liner 1st Time VPS Setup

sudo apt update && sudo apt upgrade -y && sudo apt install python3.7 -y && sudo apt-get install python3-pip -y && sudo apt-get install python3-venv -y && git clone https://github.com/zalzibab/zalzibab_public_suite.git && cd ~/zalzibab_public_suite/risk_management

### How To Use

On initial VPS setup, run one-liner above.

Create a new screen session > screen -S risk_management

Run the following one-liner

python3 -m venv risk_management && source risk_management/bin/activate && python3 -m pip install -r requirements.txt && python risk_calculator.py

When your session is complete, detach from the screen session with keyboard input > Ctrl+a d

When you come back > screen -r risk_management will reattach your screen session, already in your python virtual environment

#### To Get Updated Repo

screen -r risk_management

cd ~/zalzibab_public_suite/risk_management && git pull && python risk_calculator.py







