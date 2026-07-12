from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.db import Base
from app.models import models
config = context.config
if config.config_file_name is not None: fileConfig(config.config_file_name)
target_metadata = Base.metadata

