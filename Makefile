# Makefile for building Okimotus Monitor executables

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
	pip install -e .

build-deps:
	pip install -e .[build]

build: build-pyinstaller

build-pyinstaller: build-deps
	python build_executable.py

build-cxfreeze: build-deps
	pip install cx_Freeze
	python setup_cxfreeze.py build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.spec
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

dist-clean: clean
	rm -rf *.egg-info/

test:
	python -m pytest

# Platform-specific builds
build-linux: build-deps
	pyinstaller --onefile --name okimotus-monitor-linux src/monitor/monitor.py

build-windows: build-deps
	pyinstaller --onefile --windowed --name okimotus-monitor-windows src/monitor/monitor.py

# Quick development test
run:
	python src/monitor/monitor.py

# Install and test the built executable
test-executable:
	./dist/okimotus-monitor --help