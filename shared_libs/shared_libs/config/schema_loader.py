# shared_libs/config/schemas_loader.py
from .base_loader import BaseConfigLoader
from pathlib import Path
from typing import Dict, Any, Optional
from shared_libs.utils.logger import Logger
logger = Logger.get_logger(module_name=__name__)

class SchemaConfigLoader(BaseConfigLoader):
    SCHEMAS_DIR_PATH: Path = Path(__file__).parent / 'schemas/'

    def __init__(self, schemas_path: Optional[str] = None):
        super().__init__()
        self.schemas_path = Path(schemas_path) if schemas_path else self.SCHEMAS_DIR_PATH
        self.schemas = self.load_schemas(self.schemas_path)

    def load_schemas(self, schemas_dir: Path) -> Dict[str, Any]:
        try:
            schemas = {}
            if schemas_dir.exists() and schemas_dir.is_dir():
                for schema_file in schemas_dir.glob("*.yaml"):
                    schema_name = schema_file.stem
                    schemas[schema_name] = self.load_yaml(schema_file)
            else:
                logger.warning(f"Schemas directory not found at '{schemas_dir}'")
            return schemas
        except Exception as e:
            logger.error(f"Error loading schemas: {e}")
            raise

    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        return self.schemas.get(schema_name, {})
