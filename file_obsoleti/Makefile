# Makefile per Peptide Management System

.PHONY: help install test clean backup

help:
	@echo "Comandi disponibili:"
	@echo "  make install    - Installa dipendenze"
	@echo "  make test       - Esegue test"
	@echo "  make clean      - Pulisce file temporanei"
	@echo "  make backup     - Backup database"
	@echo "  make format     - Formatta codice"

install:
	pip install -r requirements.txt
	python setup.py develop

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

backup:
	python scripts/backup_database.py

format:
	black peptide_manager/ cli/ tests/ scripts/
	flake8 peptide_manager/ cli/ tests/
