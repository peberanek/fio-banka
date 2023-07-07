.PHONY: linters
linters:
	@pre-commit --version
	pre-commit run ${PRECOMMIT_ARGS}

.PHONY: linters-all-files
linters-all-files: PRECOMMIT_ARGS = --all-files
linters-all-files: linters

.PHONY: build
build:
	python3 -m build .

.PHONY: distribute
distribute:
	twine upload dist/fio_banka-*.tar.gz dist/fio_banka-*-py3-none-any.whl
