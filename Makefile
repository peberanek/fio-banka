.PHONY: linters
linters:
	@pre-commit --version
	pre-commit run ${PRECOMMIT_ARGS}

.PHONY: linters-all-files
linters-all-files: PRECOMMIT_ARGS = --all-files
linters-all-files: linters

.PHONY: venv
venv: pip_install = python3 -m pip install
venv: venv_dir = ./venv
venv:
	python3 -m venv --clear --upgrade-deps ${venv_dir}
	source ${venv_dir}/bin/activate \
		&& ${pip_install} wheel \
		&& ${pip_install} --editable .[development]

.PHONY: build
build:
	python3 -m build .

.PHONY: distribute
distribute:
	twine upload dist/fio_banka-*.tar.gz dist/fio_banka-*-py3-none-any.whl
