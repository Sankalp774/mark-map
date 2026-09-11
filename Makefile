.PHONY: demo test eval

demo:
	python -m markmap

test:
	python -m pytest -q

eval:
	python -m markmap.eval
