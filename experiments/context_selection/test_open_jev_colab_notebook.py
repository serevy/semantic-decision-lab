import json
import unittest
from pathlib import Path


NOTEBOOK = Path(__file__).with_name("open_jev_v0_1_colab.ipynb")


class OpenJevColabNotebookTest(unittest.TestCase):
    def test_code_cell_commands_are_separate_lines(self):
        notebook = json.loads(NOTEBOOK.read_text())
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertEqual(len(code_cells), 1)
        source = code_cells[0]["source"]
        self.assertEqual(
            source,
            [
                "!nvidia-smi\n",
                "!git clone https://github.com/serevy/semantic-decision-lab.git\n",
                "%cd semantic-decision-lab\n",
                "!python experiments/context_selection/run_open_jev_colab.py\n",
            ],
        )
        self.assertNotIn("\\n", "".join(source))

    def test_markdown_does_not_contain_literal_backslash_n(self):
        notebook = json.loads(NOTEBOOK.read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "markdown":
                self.assertNotIn("\\n", "".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
