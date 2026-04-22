import os
import pytest

from core.config import PROJECT_ROOT, DATA_DIR, OUTPUT_DIR


class TestConfig:
    def test_project_root_exists(self):
        assert os.path.isdir(PROJECT_ROOT)

    def test_project_root_has_pyproject(self):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, "pyproject.toml"))

    def test_data_dir_path(self):
        assert DATA_DIR == os.path.join(PROJECT_ROOT, "data")

    def test_output_dir_path(self):
        assert OUTPUT_DIR == os.path.join(PROJECT_ROOT, "output")

    def test_data_dir_exists(self):
        assert os.path.isdir(DATA_DIR)
