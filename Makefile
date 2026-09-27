.PHONY: test compile doctor dry-run all

test:
	python -m pytest

compile:
	python -m compileall -q main.py src tests

doctor:
	python main.py --doctor

dry-run:
	python main.py --dry-run

all:
	python main.py --all
