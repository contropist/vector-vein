# @Author: Bi Ying
# @Date:   2024-03-29 01:34:55
from vectorvein.types import BackendType
from .base_llm import BaseLLMTask


class GeminiTask(BaseLLMTask):
    MODEL_TYPE: BackendType = BackendType.Gemini
