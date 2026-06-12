from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Agent OS"
    debug: bool = True
    ollama_url: str = "http://localhost:11434"


settings = Settings()
