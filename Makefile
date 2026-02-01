CONDA_ENV ?= multiphysics
GRAPH_GRANULARITY ?= module
PYTHON ?= python3
CONDA_BASE := $(shell conda info --base 2>/dev/null)
ifeq ($(strip $(CONDA_BASE)),)
$(error conda not found on PATH. Please ensure conda is installed.)
endif
CONDA_ACTIVATE = . "$(CONDA_BASE)/etc/profile.d/conda.sh" && conda activate $(CONDA_ENV)

.PHONY: install install-core clean test import-lint package-smoke

install:
	@$(CONDA_ACTIVATE)  && SCIONA_INCLUDE_ADDONS=1 && $(PYTHON) -m pip install -e .

install-core:
	@touch .sciona_core_only
	@$(CONDA_ACTIVATE) && SCIONA_INCLUDE_ADDONS=0 $(PYTHON) setup.py develop
	@rm -f .sciona_core_only

clean:
	rm -rf dist build *.egg-info

test:
	@$(CONDA_ACTIVATE) && $(PYTHON) -m pytest

package-smoke:
	@$(CONDA_ACTIVATE) && $(PYTHON) -c "import sys; sys.exit('package-smoke requires Python >= 3.11. Set PYTHON=python3.11.') if sys.version_info < (3, 11) else None"
	@$(CONDA_ACTIVATE) && $(PYTHON) -m pip install -e .
	@$(CONDA_ACTIVATE) && cd /tmp && $(PYTHON) -c "import sciona, sciona.addons, sciona.addons.documentation; print('default-ok')"
	@$(CONDA_ACTIVATE) && $(PYTHON) -m pip uninstall -y sciona
	@touch .sciona_core_only
	@$(CONDA_ACTIVATE) && SCIONA_INCLUDE_ADDONS=0 $(PYTHON) setup.py bdist_wheel -d /tmp/sciona_core_wheel
	@rm -f .sciona_core_only
	@$(CONDA_ACTIVATE) && $(PYTHON) -m pip install /tmp/sciona_core_wheel/sciona-*.whl
	@$(CONDA_ACTIVATE) && cd /tmp && $(PYTHON) -c "code = '''import sciona\ntry:\n    import sciona.addons\nexcept ModuleNotFoundError:\n    print(\"core-only-ok\")\n    raise SystemExit\ntry:\n    import sciona.addons.documentation\nexcept ModuleNotFoundError:\n    print(\"core-only-ok\")\n    raise SystemExit\nraise SystemExit(\"Expected sciona.addons.documentation to be unavailable in core-only build.\")'''; exec(code)"

import-lint:
	@$(CONDA_ACTIVATE) && lint-imports
