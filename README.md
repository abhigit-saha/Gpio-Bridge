##Instructions
1. Connect your raspberry pi device (must be a Pi Zero) to your system using ssh, and clone this repo there.
2. cd into the directory and just run the file using '''python gpio_bridge.py'''.
3. If you are using any firmware that requires gpio pin usage, first start that firmware, and then try
   to run this file. It might not work the first time but in a couple of tries it should work

Note: this is entirely vibe coded in about a couple of hours, and please review the code yourself as well to be sure that it isn't doing
something fishy in your scenario. I don't recommend using this in hardwares with funds in them (like air-gapped 
wallets). This was just something I was testing out to make my development easier. 

