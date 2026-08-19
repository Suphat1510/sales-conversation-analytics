from src.db import init_db
from src.exporter import export_conversation_dataset
init_db()
print(export_conversation_dataset())
