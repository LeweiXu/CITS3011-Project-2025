import random
import numpy as np
import os
from game import run_one_game
from agent_baselines import StaticAgent, RandomAgent, GreedyAgent, AttitudeAgent
from agent_23709058 import StudentAgent

# This file provides an example to simulate one game and export the game process for visualization.

if __name__ == "__main__":

	save_path = 'game_for_vis.json'
	if os.path.exists(save_path):
		os.remove(save_path)

	agents_dict = {
		'AUSTRIA': StudentAgent(), 
		'ENGLAND': StaticAgent(), 
		'FRANCE': StaticAgent(), 
		'GERMANY': StaticAgent(), 
		'ITALY': StaticAgent(), 
		'RUSSIA': StaticAgent(), 
		'TURKEY': StaticAgent()
	}

	run_one_game(agents_dict, save_file=save_path)

	'''
	A JSON file will be saved, which can be visualized using the Web Interface provided on https://github.com/diplomacy/diplomacy?tab=readme-ov-file#web-interface
	
	Follow the instructions to setup the Web Interface: https://github.com/diplomacy/diplomacy?tab=readme-ov-file#web-interface, which may take some time. 

	Then click 'load a game from the disk' on the Web Interface, to load and visualize the saved JSON.

	This visualization is not necessary for completing the project. It is mainly to assist the debugging and for fun.

	Note that if there is an existing file with the same name, the game data will be appended to the same file, and causing errors for visualization.

	Need to run the following: NODE_OPTIONS=--openssl-legacy-provider npm start
	'''


