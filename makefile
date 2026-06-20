venv:
	python3 -m venv .venv

install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

format:
	.venv/bin/black .

lint:
	.venv/bin/black --check app tests

test:
	.venv/bin/pytest -vv