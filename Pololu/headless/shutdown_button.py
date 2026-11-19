#!/usr/bin/env python3
import os
import sys
import logging
from gpiozero import Button
from signal import pause

# Configure logging to journalctl
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# BCM GPIO 21 is Physical Pin 40
SHUTDOWN_PIN = 21
HOLD_TIME = 2.0  # Require 2-second hold to prevent accidental bumps

def initiate_shutdown():
    logging.info('Shutdown button held. Initiating safe system halt...')
    # Note: When run via systemd as root, sudo is not required
    os.system('shutdown -h now')

try:
    # pull_up=True uses internal resistor. bounce_time=0.2 prevents switch chatter.
    shutdown_btn = Button(
        SHUTDOWN_PIN,
        pull_up=True,
        bounce_time=0.2,
        hold_time=HOLD_TIME
    )
    shutdown_btn.when_held = initiate_shutdown
    logging.info(f'Power off button listener active on BCM {SHUTDOWN_PIN}.')
    
    # Keep the script running in the background
    pause()

except RuntimeError as e:
    logging.error(f'GPIO Hardware Error: {e}')
    sys.exit(1)
except Exception as e:
    logging.error(f'Unexpected failure: {e}')
    sys.exit(1)

