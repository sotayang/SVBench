# -*- coding: utf-8 -*-
"""A thin, dependency-light wrapper around the OpenAI Chat Completions API.

All data-construction and evaluation scripts in this repository rely on a
``GPT`` client that exposes two methods:

* ``chat(prompt, max_cycle=...)`` -- send a plain text prompt.
* ``vision(prompt, image_paths, max_cycle=...)`` -- send a prompt together with
  one or more local images (used to caption / build QA chains from video
  frames).

Both methods return the model's textual response on success, or ``None`` when
every retry attempt fails. Callers in this repo generally loop until a
non-``None`` value is returned, so returning ``None`` (instead of raising) keeps
that contract intact.

Configuration is read from environment variables so no secrets are hard-coded:

* ``OPENAI_API_KEY``  -- required, your API key.
* ``OPENAI_API_BASE`` -- optional, custom endpoint (e.g. an Azure/proxy URL).
* ``GPT_MODEL``       -- optional, model name (defaults to ``gpt-4o``).
"""

import base64
import mimetypes
import os
import time

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - surfaced only without the dep
    raise ImportError(
        "The 'openai' package (>=1.0) is required to use the GPT client. "
        "Install it with `pip install openai`."
    ) from exc


class GPT:
    """Minimal OpenAI chat/vision client with built-in retries."""

    def __init__(self, model=None, api_key=None, base_url=None, temperature=0.2):
        self.model = model or os.environ.get("GPT_MODEL", "gpt-4o")
        self.temperature = temperature

        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "No OpenAI API key found. Set the OPENAI_API_KEY environment "
                "variable or pass api_key=... to GPT()."
            )
        base_url = base_url or os.environ.get("OPENAI_API_BASE")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _encode_image(image_path):
        """Read a local image file and return a base64 data URL."""
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None:
            mime_type = "image/jpeg"
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _create(self, messages, max_cycle):
        """Call the chat completion endpoint, retrying up to ``max_cycle`` times."""
        for attempt in range(1, max_cycle + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
                return response.choices[0].message.content
            except Exception as error:  # noqa: BLE001 - retry on any API error
                wait = min(2 ** attempt, 60)
                print(f"[GPT] request failed (attempt {attempt}/{max_cycle}): {error}. "
                      f"Retrying in {wait}s...")
                time.sleep(wait)
        return None

    def chat(self, prompt, max_cycle=20):
        """Send a text-only prompt and return the response text (or ``None``)."""
        messages = [{"role": "user", "content": prompt}]
        return self._create(messages, max_cycle)

    def vision(self, prompt, image_paths, max_cycle=20):
        """Send a prompt with one or more local images.

        ``image_paths`` may be a single path or an iterable of paths.
        """
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        content = [{"type": "text", "text": prompt}]
        for image_path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._encode_image(image_path)},
                }
            )

        messages = [{"role": "user", "content": content}]
        return self._create(messages, max_cycle)
