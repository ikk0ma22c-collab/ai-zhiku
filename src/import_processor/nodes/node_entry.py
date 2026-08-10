import json
import logging
from pathlib import Path

from src.import_processor.exceptions import ValidationError, StateFieldError, FileProcessingError
from src.import_processor.base import BaseNode, setup_logging
from src.import_processor.state import ImportGraphState


class NodeEntry(BaseNode):
    """
    入口节点：任务分发
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):
        import_file_path = state.get("import_file_path")

        if not import_file_path:
            raise StateFieldError( field_name = 'import_file_path', expected_type = str)

        import_file_path_obj = Path(import_file_path)
        if not import_file_path_obj.suffix==".pdf":
            state["is_pdf_read_enabled"] = True
            state["pdf_path"] = import_file_path
        elif import_file_path_obj.suffix==".md":
            state["is_md_read_enabled"] = True
            state["md_path"] = import_file_path
        else:
            raise FileProcessingError(message = f"文件格式不支持: {import_file_path}")
        state["file_title"] = import_file_path_obj.stem

        return state