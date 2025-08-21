# Opentrons_2025
## ℹ️ Overview
This repository contains four Python scripts developed during an internship on the Science team at Opentrons. These scripts automate key tasks to help lower production time and costs associated with developing Opentrons protocols. Specifically, the scripts facilitate batch auditing and simulation.


## 📜 Scripts

Here is a breakdown of the scripts included in this repository:

* **Audit.py**: This script analyzes all protocols in a specified folder. It provides a comprehensive report for each protocol, including:
    * Metadata
    * Required modules
    * Run-time parameters (RTP)
    * Potential z-height issues
    * Required reservoir types

* **Find_Replace_Z.py**: This script addresses z-height issues by finding and replacing problematic z-height values with a user-defined threshold. This can be run across an entire folder of protocols.

* **Randomized_RTP.py**: This script generates randomized protocol files to test various extreme combinations of run-time parameters. This is useful for ensuring your protocol is robust and can handle a wide range of inputs.

* **Mass_Simulation.py**: This script performs mass simulation of protocols and requires `Randomized_RTP.py`. It also requires the Opentrons API to be installed and configured.


### ✍️ Authors
I'm proud to share these scripts I developed during my rewarding internship at Opentrons. I'm incredibly grateful for the opportunity to contribute and for the valuable skills I gained.

Matthew Jednacz: [Github](https://github.com/Draco2550)

Opentrons: [Website](https://opentrons.com/?srsltid=AfmBOooFPVLcU-ZwKOn6bhCLG0O56HeCHSJF9L3-y0bB3tStsgH-KZBS)



## 🚀 Usage
1. Prior to first use of the scripts please download the scripts into one folder, this folder should also contain the folder of protocols you wish to use the scripts on.
2. Go to any of the scripts and modify the line to fit the name of the folder holding the protocols:
```py
protocols_directory = 'Protocol Full Batch'
```
3. Save the changes. *Keep the folders consistent of what you want to do with them to avoid making too much of a mess.*
4. All the scripts can be run in a terminal or ide, simply go to the directory housing the scripts + folder of protcols and run this line. *They can all be run the same way, just change the file after the argument "python3" to run.*
```bash
python3 Randomized_RTP.py
```
**Note**: You will have to change the file that you want to work with in `Randomized_RTP.py`, please modify the line:
```py
filename = 'file.py'
```
To a file in the folder you provided in step 2.


## ⬇️ Installation
### Prerequisites
* Python 3.10.0 or higher.
* The Opentrons API (required for **Mass_Simulation.py**). See [Simulation Help](https://support.opentrons.com/s/article/Simulating-OT-2-protocols-on-your-computer) for installation steps.
* It is recommended to use [pyenv](https://github.com/pyenv/pyenv) to manage Python versions locally.
  
Install these files individually or as a group. Keep them in a folder that contains a folder of protocols you would like to work with.
**Mass_Simulation.py requires Randomized_RTP.py to be installed in the same folder.**


## 📝 License
This project is licensed under the Apache-2.0 License. See the `LICENSE` file for more details.
