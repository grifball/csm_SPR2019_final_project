SHELL := /bin/bash
default:
	@echo -e "to test:\n\tmake example\nto setup build env:\n\tmake build"
example:
	python3 scott_synth.py
build:
	python3 -m venv ./venv
	source ./venv/bin/activate && python3 -m pip install -r ./requirements.txt
	@echo -e "\nrun 'source ./venv/bin/activate' before running the program"
