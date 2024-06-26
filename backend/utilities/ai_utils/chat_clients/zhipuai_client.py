# -*- coding: utf-8 -*-
# @Author: Bi Ying
# @Date:   2023-12-12 15:24:15
# @Last Modified by:   Bi Ying
# @Last Modified time: 2024-06-17 18:29:45
from .openai_compatible_client import OpenAICompatibleChatClient, AsyncOpenAICompatibleChatClient


DEFAULT_MODEL = "glm-4-air"
MODEL_MAX_INPUT_LENGTH = {
    "glm-3-turbo": 128000,
    "glm-4": 128000,
    "glm-4-0520": 128000,
    "glm-4-air": 128000,
    "glm-4-airx": 128000,
    "glm-4-flash": 128000,
    "glm-4v": 2000,
}
MODEL_FUNCTION_CALLING_AVAILABLE = {
    "glm-3-turbo": True,
    "glm-4": True,
    "glm-4-0520": True,
    "glm-4-air": True,
    "glm-4-airx": True,
    "glm-4-flash": True,
    "glm-4v": False,
}

API_KEY_SETTING_NAME = "zhipuai_api_key"
API_BASE_SETTING_NAME = "zhipuai_api_base"


class ZhiPuAIChatClient(OpenAICompatibleChatClient):
    DEFAULT_MODEL = DEFAULT_MODEL
    MODEL_MAX_INPUT_LENGTH = MODEL_MAX_INPUT_LENGTH
    MODEL_FUNCTION_CALLING_AVAILABLE = MODEL_FUNCTION_CALLING_AVAILABLE
    API_KEY_SETTING_NAME = API_KEY_SETTING_NAME
    API_BASE_SETTING_NAME = API_BASE_SETTING_NAME


class AsyncZhiPuAIChatClient(AsyncOpenAICompatibleChatClient):
    DEFAULT_MODEL = DEFAULT_MODEL
    MODEL_MAX_INPUT_LENGTH = MODEL_MAX_INPUT_LENGTH
    MODEL_FUNCTION_CALLING_AVAILABLE = MODEL_FUNCTION_CALLING_AVAILABLE
    API_KEY_SETTING_NAME = API_KEY_SETTING_NAME
    API_BASE_SETTING_NAME = API_BASE_SETTING_NAME
