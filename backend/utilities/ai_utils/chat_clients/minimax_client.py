# -*- coding: utf-8 -*-
# @Author: Bi Ying
# @Date:   2023-12-12 15:23:26
# @Last Modified by:   Bi Ying
# @Last Modified time: 2024-06-18 01:28:36
import json

import httpx

from utilities.config import Settings
from .base_client import BaseChatClient, BaseAsyncChatClient
from .utils import cutoff_messages


MODEL_MAX_INPUT_LENGTH = {
    "abab5-chat": 6144,
    "abab5.5-chat": 16384,
    "abab6-chat": 32768,
    "abab6.5s-chat": 245760,
}


def extract_tool_calls(response):
    try:
        message = response["choices"][0].get("delta") or response["choices"][0].get("message", {})
        tool_calls = message.get("tool_calls")
        if tool_calls:
            return {
                "tool_calls": [
                    {
                        "index": index,
                        "id": tool_call["id"],
                        "function": tool_call["function"],
                        "type": tool_call["type"],
                    }
                    for index, tool_call in enumerate(tool_calls)
                ]
            }
        else:
            return {}
    except Exception:
        return {}


class MiniMaxChatClient(BaseChatClient):
    DEFAULT_MODEL: str = "abab5.5-chat"

    def __init__(
        self,
        model: str = "abab5.5-chat",
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
        self.url = settings.minimax_api_base
        self.headers = {"Authorization": f"Bearer {settings.minimax_api_key}", "Content-Type": "application/json"}

    def create_completion(
        self,
        messages: list = list,
        model: str | None = None,
        stream: bool | None = None,
        temperature: float | None = None,
        max_tokens: int = 2048,
        tools: list | None = None,
        tool_choice: str = "auto",
    ):
        if model is not None:
            self.model = model
        if stream is not None:
            self.stream = stream
        if temperature is not None:
            self.temperature = temperature

        messages = cutoff_messages(messages, max_count=MODEL_MAX_INPUT_LENGTH[self.model], model=self.model)

        if tools is not None:
            tools_params = {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool["function"]["name"],
                            "description": tool["function"].get("description", ""),
                            "parameters": json.dumps(
                                tool["function"].get("parameters", {})
                            ),  # 非要搞不同，parameters 是个字符串
                        },
                    }
                    for tool in tools
                ],
                "tool_choice": tool_choice,
            }
        else:
            tools_params = {}

        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
            "mask_sensitive_info": False,
            **tools_params,
        }

        response = httpx.post(
            url=self.url,
            headers=self.headers,
            json=request_body,
            timeout=60,
        )

        if self.stream:

            def generator():
                for chunk in response.iter_lines():
                    if chunk:
                        chunk_data = json.loads(chunk[6:])
                        tool_calls_params = extract_tool_calls(chunk_data)
                        has_tool_calls = True if tool_calls_params else False
                        if has_tool_calls:
                            if "usage" not in chunk_data:
                                continue
                            else:
                                yield {
                                    "content": chunk_data["choices"][0]["message"].get("content"),
                                    "role": "assistant",
                                    **tool_calls_params,
                                }
                        else:
                            if "usage" in chunk_data:
                                continue
                            yield {
                                "content": chunk_data["choices"][0]["delta"]["content"],
                                "role": "assistant",
                            }

            return generator()
        else:
            result = response.json()
            tool_calls_params = extract_tool_calls(result)
            return {
                "content": result["choices"][0]["message"].get("content"),
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": result["usage"]["total_tokens"],
                    "total_tokens": result["usage"]["total_tokens"],
                },
                "role": "assistant",
                **tool_calls_params,
            }


class AsyncMiniMaxChatClient(BaseAsyncChatClient):
    DEFAULT_MODEL: str = "abab5.5-chat"

    def __init__(
        self,
        model: str = "abab5.5-chat",
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
        self.url = settings.minimax_api_base
        self.headers = {"Authorization": f"Bearer {settings.minimax_api_key}", "Content-Type": "application/json"}
        self.http_client = httpx.AsyncClient()

    async def create_completion(
        self,
        messages: list = list,
        model: str | None = None,
        stream: bool | None = None,
        temperature: float | None = None,
        max_tokens: int = 2048,
        tools: list | None = None,
        tool_choice: str = "auto",
    ):
        if model is not None:
            self.model = model
        if stream is not None:
            self.stream = stream
        if temperature is not None:
            self.temperature = temperature

        messages = cutoff_messages(messages, max_count=MODEL_MAX_INPUT_LENGTH[self.model], model=self.model)

        if tools is not None:
            tools_params = {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool["function"]["name"],
                            "description": tool["function"].get("description", ""),
                            "parameters": json.dumps(tool["function"].get("parameters", {})),
                        },
                    }
                    for tool in tools
                ],
                "tool_choice": tool_choice,
            }
        else:
            tools_params = {}

        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
            "mask_sensitive_info": False,
            **tools_params,
        }

        if self.stream:

            async def generator():
                async with self.http_client.stream(
                    "POST",
                    url=self.url,
                    headers=self.headers,
                    json=request_body,
                    timeout=60,
                ) as response:
                    has_tool_calls = False
                    async for chunk in response.aiter_lines():
                        if chunk:
                            chunk_data = json.loads(chunk[6:])
                            tool_calls_params = extract_tool_calls(chunk_data)
                            has_tool_calls = True if tool_calls_params else False
                            if has_tool_calls:
                                if "usage" not in chunk_data:
                                    continue
                                else:
                                    yield {
                                        "content": chunk_data["choices"][0]["message"].get("content"),
                                        "role": "assistant",
                                        **tool_calls_params,
                                    }
                            else:
                                if "usage" in chunk_data:
                                    continue
                                yield {
                                    "content": chunk_data["choices"][0]["delta"]["content"],
                                    "role": "assistant",
                                }

            return generator()
        else:
            response = await self.http_client.post(
                url=self.url,
                headers=self.headers,
                json=request_body,
                timeout=60,
            )
            result = response.json()
            tool_calls_params = extract_tool_calls(result)
            return {
                "content": result["choices"][0]["message"].get("content"),
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": result["usage"]["total_tokens"],
                    "total_tokens": result["usage"]["total_tokens"],
                },
                "role": "assistant",
                **tool_calls_params,
            }

    async def __aexit__(self, exc_type, exc, tb):
        await self.http_client.aclose()
