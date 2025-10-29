from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    deepl_token: str
    tavily_token: str
    owm_token: str
    ymaps_token: str = "ad7c40a7-7096-43c9-b6e2-5e1f6d06b9ec"

    llamacpp_ip: str = "127.0.0.1"
    llamacpp_port: int = 6669

    token_system_start: str = "<sss>"
    token_system_end: str = "</sss>"
    token_assistant_start: str = "<ass>"
    token_assistant_end: str = "</ass>"
    token_user_start: str = "<uss>"
    token_user_end: str = "</uss>"
    token_tool_resp_start: str = "<tll>"
    token_tool_resp_end: str = "</tll>"
    token_tool_call_start: str = "<atl>"
    token_tool_call_end: str = "</atl>"
    token_newline: str = "<nwln>"

config = Config()
