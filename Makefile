setup:
	brew install python3
	python3 -m ensurepip --upgrade
	pip install virtualenv
	virtualenv SlackExtract
	source SlackExtract/bin/activate && pip install -r requirements.txt

test:
	source SlackExtract/bin/activate && python slack.py
