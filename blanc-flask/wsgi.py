from app import create_app
from config import QaConfig, ProdConfig, DevConfig
import os

env = os.environ.get("OP_ENV", "dev")
print("Configuration is set up for ${0} mode".format(env))

if env == "prod":
    config = ProdConfig
elif env == "qa":
    config = QaConfig
else:
    config = DevConfig

app = create_app(config=config)
