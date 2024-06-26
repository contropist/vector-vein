# -*- coding: utf-8 -*-
# @Author: Bi Ying
# @Date:   2023-12-12 15:24:15
# @Last Modified by:   Bi Ying
# @Last Modified time: 2024-06-09 00:19:24
import json

from openai import OpenAI, AsyncOpenAI
from openai._streaming import Stream, AsyncStream
from openai._types import NotGiven, NOT_GIVEN
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from utilities.config import Settings
from .base_client import BaseChatClient, BaseAsyncChatClient
from .utils import (
    cutoff_messages,
    extract_tool_calls,
    generate_tool_use_system_prompt,
    tool_use_re,
)


MODEL_MAX_INPUT_LENGTH = {
    "mixtral-8x22b": 60000,
    "mistral-small": 30000,
    "mistral-medium": 30000,
    "mistral-large": 30000,
}

MODEL_NAME_MAP = {
    "mixtral-8x22b": "open-mixtral-8x22b",
    "mistral-small": "mistral-small-latest",
    "mistral-medium": "mistral-medium-latest",
    "mistral-large": "mistral-large-latest",
}


class MistralChatClient(BaseChatClient):
    DEFAULT_MODEL: str = "mistral-small"

    def __init__(
        self,
        model: str = "mistral-small",
        stream: bool = True,
        temperature: float = 0.7,
        context_length_control: str = "latest",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.stream = stream
        self.temperature = temperature
        self.context_length_control = context_length_control
        settings = Settings()
        self._mistral_ai_client = OpenAI(
            api_key=settings.mistral_api_key,
            base_url=settings.mistral_api_base,
        )
        self._native_function_calling_available = False

    def create_completion(
        self,
        messages: list = list,
        model: str | None = None,
        stream: bool | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        tools: list | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
    ):
        if model is not None:
            self.model = model
        if stream is not None:
            self.stream = stream
        if temperature is not None:
            self.temperature = temperature

        if self.context_length_control == "latest":
            messages = cutoff_messages(messages, max_count=MODEL_MAX_INPUT_LENGTH[self.model])

        if self.model in ("mixtral-8x22b", "mistral-small", "mistral-large"):
            self._native_function_calling_available = True

        if tools:
            if self._native_function_calling_available:
                tools_params = dict(tools=tools, tool_choice=tool_choice)
            else:
                tools_str = json.dumps(tools, ensure_ascii=False, indent=None)
                additional_system_prompt = generate_tool_use_system_prompt(tools=tools_str)
                if messages[0].get("role") == "system":
                    messages[0]["content"] += "\n\n" + additional_system_prompt
                else:
                    messages.insert(0, {"role": "system", "content": additional_system_prompt})
                tools_params = {}
        else:
            tools_params = {}

        client = self._mistral_ai_client

        response: ChatCompletion | Stream[ChatCompletionChunk] = client.chat.completions.create(
            model=MODEL_NAME_MAP[self.model],
            messages=messages,
            stream=self.stream,
            temperature=self.temperature,
            max_tokens=max_tokens,
            **tools_params,
        )

        if self.stream:

            def generator():
                full_content = ""
                result = {}
                for chunk in response:
                    if len(chunk.choices) > 0:
                        if self._native_function_calling_available:
                            yield chunk.choices[0].delta.model_dump()
                        else:
                            message = chunk.choices[0].delta.model_dump()
                            full_content += message["content"] if message["content"] else ""
                            if tools:
                                tool_call_data = extract_tool_calls(full_content.replace("\\_", "_"))
                                if tool_call_data:
                                    message["tool_calls"] = tool_call_data["tool_calls"]
                            if full_content in ("<", "<|", "<|▶", "<|▶|") or full_content.startswith("<|▶|>"):
                                message["content"] = ""
                                result = message
                                continue
                            yield message
                            if result:
                                yield result

            return generator()
        else:
            result = {
                "content": response.choices[0].message.content.replace("\\_", "_"),
                "usage": response.usage.model_dump(),
            }
            if tools:
                tool_call_data = extract_tool_calls(result["content"])
                if tool_call_data:
                    result["tool_calls"] = tool_call_data["tool_calls"]
                    result["content"] = tool_use_re.sub("", result["content"])
            return result


class AsyncMistralChatClient(BaseAsyncChatClient):
    DEFAULT_MODEL: str = "mistral-small"

    def __init__(
        self,
        model: str = "mistral-small",
        stream: bool = True,
        temperature: float = 0.7,
        context_length_control: str = "latest",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.stream = stream
        self.temperature = temperature
        self.context_length_control = context_length_control
        settings = Settings()
        self._mistral_ai_client = AsyncOpenAI(
            api_key=settings.mistral_api_key,
            base_url=settings.mistral_api_base,
        )
        self._native_function_calling_available = False

    async def create_completion(
        self,
        messages: list = list,
        model: str | None = None,
        stream: bool | None = None,
        temperature: float | None = None,
        max_tokens: int = 2000,
        tools: list | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
    ):
        if model is not None:
            self.model = model
        if stream is not None:
            self.stream = stream
        if temperature is not None:
            self.temperature = temperature

        if self.context_length_control == "latest":
            messages = cutoff_messages(messages, max_count=MODEL_MAX_INPUT_LENGTH[self.model])

        if self.model in ("mixtral-8x22b", "mistral-small", "mistral-large"):
            self._native_function_calling_available = True

        if tools:
            if self._native_function_calling_available:
                tools_params = dict(tools=tools, tool_choice=tool_choice)
            else:
                tools_str = json.dumps(tools, ensure_ascii=False, indent=None)
                additional_system_prompt = generate_tool_use_system_prompt(tools=tools_str)
                if messages[0].get("role") == "system":
                    messages[0]["content"] += "\n\n" + additional_system_prompt
                else:
                    messages.insert(0, {"role": "system", "content": additional_system_prompt})
                tools_params = {}
        else:
            tools_params = {}

        client = self._mistral_ai_client

        response: ChatCompletion | AsyncStream[ChatCompletionChunk] = await client.chat.completions.create(
            model=MODEL_NAME_MAP[self.model],
            messages=messages,
            stream=self.stream,
            temperature=self.temperature,
            max_tokens=max_tokens,
            **tools_params,
        )

        if self.stream:

            async def generator():
                full_content = ""
                result = {}
                async for chunk in response:
                    if len(chunk.choices) > 0:
                        if self._native_function_calling_available:
                            yield chunk.choices[0].delta.model_dump()
                        else:
                            message = chunk.choices[0].delta.model_dump()
                            full_content += message["content"] if message["content"] else ""
                            if tools:
                                tool_call_data = extract_tool_calls(full_content.replace("\\_", "_"))
                                if tool_call_data:
                                    message["tool_calls"] = tool_call_data["tool_calls"]
                            if full_content in ("<", "<|", "<|▶", "<|▶|") or full_content.startswith("<|▶|>"):
                                message["content"] = ""
                                result = message
                                continue
                            yield message
                            if result:
                                yield result

            return generator()
        else:
            result = {
                "content": response.choices[0].message.content.replace("\\_", "_"),
                "usage": response.usage.model_dump(),
            }
            if tools:
                tool_call_data = extract_tool_calls(result["content"])
                if tool_call_data:
                    result["tool_calls"] = tool_call_data["tool_calls"]
                    result["content"] = tool_use_re.sub("", result["content"])
            return result
