# Makefile for building Okimotus Monitor executables
# Run from the releases folder: cd releases && make build

.PHONY: help install build-deps build-pyinstaller build-cxfreeze clean test

help:
	@echo "Available targets:"
	@echo "  install       - Install the package in development mode"
	@echo "  build-deps    - Install build dependencies"
	@echo "  build         - Build executable using PyInstaller (default)"
	@echo "  build-cxfreeze- Build executable using cx_Freeze"
	@echo "  clean         - Clean build artifacts"
	@echo "  test          - Run tests"
	@echo "  dist-clean    - Clean all build and distribution files"

install:
	cd .. && pip install -e .

build-deps:
	cd .. && pip install -e .[build]

build: build-pyinstaller

build-pyinstaller: build-deps
	python build_executable.py

build-cxfreeze: build-deps
	pip install cx_Freeze
	python setup_cxfreeze.py build

clean:
	cd .. && rm -rf build/
	cd .. && rm -rf dist/
	cd .. && rm -rf *.spec
	find .. -name "*.pyc" -delete
	find .. -name "__pycache__" -type d -exec rm -rf {} +

dist-clean: clean
	cd .. && rm -rf *.egg-info/

test:
	cd .. && python -m pytest

# Platform-specific builds
build-linux: build-deps
	cd .. && pyinstaller --onefile --name okimotus-monitor-linux src/monitor/monitor.py

build-windows: build-deps
	cd .. && pyinstaller --onefile --windowed --name okimotus-monitor-windows src/monitor/monitor.py

# Quick development test
run:
	python src/monitor/monitor.py

# Install and test the built executable
test-executable:
	./dist/okimotus-monitor --help