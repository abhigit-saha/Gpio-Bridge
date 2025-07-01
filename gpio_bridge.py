#!/usr/bin/env python3
"""
GPIO Bridge: Safe version that works alongside existing GPIO usage
This version uses direct GPIO file system access to avoid conflicts
"""

import sys
import tty
import termios
import select
import time
import threading
import logging
import os
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GPIOBridge:
    def __init__(self):
        """Initialize GPIO Bridge using direct file system access"""
        
        # GPIO pin mapping (Board to BCM conversion)
        self.board_to_bcm = {
            31: 6,   # UP
            35: 19,  # DOWN
            29: 5,   # LEFT
            37: 26,  # RIGHT
            33: 13,  # PRESS
            40: 21,  # KEY1
            38: 20,  # KEY2
            36: 16   # KEY3
        }
        
        # GPIO pin mapping (matches your Waveshare module)
        self.gpio_pins = {
            'up': 31,
            'down': 35,
            'left': 29,
            'right': 37,
            'press': 33,
            'key1': 40,
            'key2': 38,
            'key3': 36
        }
        
        # Character to GPIO mapping
        self.key_mapping = {
            '\x1b[A': 'up',      # Up arrow
            '\x1b[B': 'down',    # Down arrow
            '\x1b[D': 'left',    # Left arrow
            '\x1b[C': 'right',   # Right arrow
            ' ': 'press',        # Space bar
            '\r': 'press',       # Enter key
            '1': 'key1',
            '2': 'key2',
            '3': 'key3',
            'w': 'up',           # WASD alternative
            's': 'down',
            'a': 'left',
            'd': 'right',
            'q': 'quit'          # Quit key
        }
        
        self.is_running = False
        self.button_press_duration = 0.1  # 100ms button press
        
    def setup_gpio_sysfs(self):
        """Setup GPIO using sysfs (file system interface)"""
        try:
            gpio_base = "/sys/class/gpio"
            
            for action, board_pin in self.gpio_pins.items():
                bcm_pin = self.board_to_bcm[board_pin]
                gpio_path = f"{gpio_base}/gpio{bcm_pin}"
                
                # Export the GPIO pin if not already exported
                if not os.path.exists(gpio_path):
                    try:
                        with open(f"{gpio_base}/export", 'w') as f:
                            f.write(str(bcm_pin))
                        logger.info(f"Exported GPIO {bcm_pin} for {action.upper()}")
                    except Exception as e:
                        logger.warning(f"Could not export GPIO {bcm_pin}: {e}")
                
                # Set as output
                try:
                    with open(f"{gpio_path}/direction", 'w') as f:
                        f.write("out")
                    
                    # Set initial value to HIGH (button not pressed)
                    with open(f"{gpio_path}/value", 'w') as f:
                        f.write("1")
                    
                    logger.info(f"Configured GPIO {bcm_pin} (Board {board_pin}) for {action.upper()}")
                    
                except Exception as e:
                    logger.warning(f"Could not configure GPIO {bcm_pin}: {e}")
            
            logger.info("GPIO setup completed using sysfs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup GPIO via sysfs: {e}")
            return False
    
    def gpio_write(self, board_pin: int, value: int):
        """Write value to GPIO pin using sysfs"""
        try:
            bcm_pin = self.board_to_bcm[board_pin]
            gpio_path = f"/sys/class/gpio/gpio{bcm_pin}/value"
            
            with open(gpio_path, 'w') as f:
                f.write(str(value))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write to GPIO {board_pin}: {e}")
            return False
    
    def simulate_button_press(self, action: str, pin: int):
        """Simulate a button press on the specified GPIO pin"""
        try:
            logger.info(f"Simulating {action.upper()} button press on Board pin {pin}")
            
            # Ensure pin is HIGH first (button not pressed)
            self.gpio_write(pin, 1)
            time.sleep(0.01)  # Small delay
            
            # Button press (LOW signal)
            if self.gpio_write(pin, 0):
                logger.info(f"  Button {action.upper()} pressed (Board {pin} -> LOW)")
                
                # Hold the button for the specified duration
                time.sleep(self.button_press_duration)
                
                # Button release (HIGH signal)
                if self.gpio_write(pin, 1):
                    logger.info(f"  Button {action.upper()} released (Board {pin} -> HIGH)")
                else:
                    logger.error(f"  Failed to release button {action.upper()}")
            else:
                logger.error(f"  Failed to press button {action.upper()}")
            
        except Exception as e:
            logger.error(f"Failed to simulate button press: {e}")
    
    def get_char(self):
        """Get a single character from stdin without waiting for Enter"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            
            # Check if data is available
            if select.select([sys.stdin], [], [], 0.1):
                ch = sys.stdin.read(1)
                
                # Handle escape sequences (arrow keys)
                if ch == '\x1b':
                    # Read the next two characters for arrow keys
                    if select.select([sys.stdin], [], [], 0.1):
                        ch += sys.stdin.read(1)
                        if select.select([sys.stdin], [], [], 0.1):
                            ch += sys.stdin.read(1)
                
                return ch
            return None
            
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def cleanup_gpio(self):
        """Clean up GPIO pins safely"""
        try:
            logger.info("Starting safe GPIO cleanup...")
            
            # Set all pins to HIGH (button not pressed) 
            for action, pin in self.gpio_pins.items():
                self.gpio_write(pin, 1)
                logger.info(f"  Set {action.upper()} (Board {pin}) to HIGH")
            
            # Small delay to ensure signals are stable
            time.sleep(0.1)
            
            logger.info("GPIO cleanup completed (pins left in HIGH state)")
            
        except Exception as e:
            logger.error(f"GPIO cleanup error: {e}")
    
    def print_instructions(self):
        """Print usage instructions"""
        print("\n" + "="*60)
        print("GPIO Bridge: Safe Keyboard to Hardware Button Simulation")
        print("="*60)
        print("Key Mappings:")
        print("  Arrow Keys    -> Directional buttons")
        print("  WASD          -> Alternative directional buttons")
        print("  SPACE/ENTER   -> Press/Select button")
        print("  1, 2, 3       -> KEY1, KEY2, KEY3")
        print("  Q             -> Quit")
        print("-"*60)
        print("GPIO Pin Mapping:")
        for action, pin in self.gpio_pins.items():
            bcm_pin = self.board_to_bcm[pin]
            print(f"  {action.upper():<8} -> Board Pin {pin} (BCM {bcm_pin})")
        print("="*60)
        print("This version uses sysfs and won't conflict with your main.py")
        print("Press keys to simulate button presses...")
        print("(Press 'q' to quit)")
        print()
    
    def start_bridge(self):
        """Start the GPIO bridge"""
        if not self.setup_gpio_sysfs():
            logger.error("Failed to setup GPIO. Trying alternative method...")
            return False
        
        self.is_running = True
        self.print_instructions()
        
        try:
            while self.is_running:
                char = self.get_char()
                
                if char is None:
                    continue
                
                # Handle quit command
                if char.lower() == 'q':
                    logger.info("Quit command received")
                    break
                
                # Check if the character maps to a GPIO action
                if char in self.key_mapping:
                    action = self.key_mapping[char]
                    
                    if action == 'quit':
                        break
                    
                    if action in self.gpio_pins:
                        pin = self.gpio_pins[action]
                        
                        # Run button press in a separate thread to avoid blocking
                        threading.Thread(
                            target=self.simulate_button_press,
                            args=(action, pin),
                            daemon=True
                        ).start()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user (Ctrl+C)")
        
        finally:
            self.stop_bridge()
        
        return True
    
    def stop_bridge(self):
        """Stop the GPIO bridge and cleanup"""
        self.is_running = False
        self.cleanup_gpio()
        logger.info("GPIO Bridge stopped")

def main():
    """Main function"""
    print("Starting Safe GPIO Bridge...")
    
    # Create and start the bridge
    bridge = GPIOBridge()
    
    try:
        if bridge.start_bridge():
            logger.info("Bridge completed successfully")
        else:
            logger.error("Failed to start bridge")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
