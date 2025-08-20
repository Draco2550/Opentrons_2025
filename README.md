# Opentrons_2025
I'm proud to share the scripts I developed during my rewarding internship at Opentrons. I'm incredibly grateful for the opportunity to contribute and for the valuable skills I gained. These scripts should lower production time and cost for working with protocols by making it easier to batch audit and simulate.

## 🌟 Highlights

The best part of these tools would be the amount of time it could save you!
- It can look over all your protocols in a folder with the Audit.py script.
  - Providing details on things such as the metadata, what modules it uses, the R.T.P in the file, inform you about possible z-height issues, and lastly, what type of resoivors it requires.
- The Find_Replace_Z.py file that does what it says, it will find instances of z-height issues and replace them for you with the threshold that you provide within a folder.
- If you need to generate randomized files to test out all different extreme combinations that are possible with your protocol use Randomized_RTP.py


## ℹ️ Overview

A paragraph explaining your work, who you are, and why you made it.


### ✍️ Authors

Mention who you are and link to your GitHub or organization's website.


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


## ⬇️ Installation

Install these files individually or as a group. Keep them in a folder that contains a folder of protocol you would like to work with.
**Mass_Simulation.py requires Randomized_RTP.py to be installed in the same folder.**

Minimum python verison 3.10.0
To use **Mass_Simulation.py** the Opentrons API needs to be installed and configured. Steps for that can be found here:
[Simulation Help](https://support.opentrons.com/s/article/Simulating-OT-2-protocols-on-your-computer)



## 💭 Feedback and Contributing

Add a link to the Discussions tab in your repo and invite users to open issues for bugs/feature requests.

This is also a great place to invite others to contribute in any ways that make sense for your project. Point people to your DEVELOPMENT and/or CONTRIBUTING guides if you have them.
