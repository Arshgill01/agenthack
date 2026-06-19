from __future__ import annotations
import json
import os
import time
import logging
from pathlib import Path
from PIL import Image
import requests
from cache import ResponseCache
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model_client")

class ModelClient:
    def __init__(self, cache_enabled: bool = True):
        self.cache = ResponseCache() if cache_enabled else None
        self.text_model = os.environ.get("TEXT_MODEL", "gemini-3.5-flash")
        self.vlm_model = os.environ.get("VLM_MODEL", "gemini-3.5-flash")
        # Setup Gemini
        self.has_gemini = False
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                self.has_gemini = True
                logger.info("Gemini API initialized using google-generativeai package.")
            except ImportError:
                logger.warning("google-generativeai package not installed, will use requests for Gemini if needed.")
        
        # Setup unified google-genai client (supports API keys and Vertex AI ADC credentials)
        self.genai_client = None
        self.use_vertex = False
        
        # Try to resolve GCP Project ID for Vertex AI
        gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_PROJECT")
        
        # 1. Try config_default INI
        if not gcp_project:
            gcloud_config_path = Path.home() / ".config" / "gcloud" / "configurations" / "config_default"
            if gcloud_config_path.exists():
                try:
                    import configparser
                    config = configparser.ConfigParser()
                    config.read(gcloud_config_path)
                    if "core" in config and "project" in config["core"]:
                        gcp_project = config["core"]["project"]
                except Exception:
                    pass

        # 2. Try ADC JSON file
        if not gcp_project:
            adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
            if adc_path.exists():
                try:
                    with open(adc_path) as f:
                        adc_data = json.load(f)
                        gcp_project = adc_data.get("quota_project_id") or adc_data.get("project_id")
                except Exception:
                    pass

        # 3. Try subprocess fallback to gcloud
        if not gcp_project:
            try:
                import subprocess
                for gcloud_cmd in ["gcloud", str(Path.home() / "google-cloud-sdk" / "bin" / "gcloud")]:
                    try:
                        res = subprocess.run(
                            [gcloud_cmd, "config", "get-value", "project"],
                            capture_output=True, text=True, timeout=5
                        )
                        if res.returncode == 0 and res.stdout.strip():
                            gcp_project = res.stdout.strip()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        try:
            from google import genai
            adc_path = Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
            has_adc = adc_path.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
            
            if has_adc:
                self.genai_client = genai.Client(
                    vertexai=True,
                    project=gcp_project,
                    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
                )
                self.use_vertex = True
                logger.info(f"google-genai Client initialized using Vertex AI (project={gcp_project}).")
            elif gemini_key:
                self.genai_client = genai.Client(api_key=gemini_key)
                logger.info("google-genai Client initialized using API key.")
        except Exception as e:
            logger.warning(f"Could not initialize google-genai Client: {e}")

        # Setup Keys
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.gemini_key = gemini_key

    def _is_rate_limit(self, e: Exception) -> bool:
        err_str = str(e).lower()
        return any(x in err_str for x in ["429", "quota", "resourceexhausted", "rate limit", "too many requests"])

    def _execute_with_retry(self, api_func, *args, **kwargs):
        max_retries = 6
        backoff = 3.0
        for attempt in range(max_retries):
            try:
                return api_func(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = any(x in err_str for x in ["429", "quota", "resourceexhausted", "rate limit", "too many requests"])
                
                # Check for explicit sleep instruction in Gemini exception
                sleep_time = backoff * (2 ** attempt)
                match = re.search(r"retry in ([\d\.]+)s", err_str)
                if match:
                    sleep_time = float(match.group(1)) + 1.5
                
                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(f"Rate limit / Quota hit. Retrying in {sleep_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(sleep_time)
                else:
                    raise e

    def call_text_model(self, prompt: str, system_instruction: str = "") -> str:
        # Check Cache
        full_prompt = f"System: {system_instruction}\nPrompt: {prompt}" if system_instruction else prompt
        if self.cache:
            cached = self.cache.get(full_prompt)
            if cached is not None:
                logger.info("Text response retrieved from cache.")
                return cached

        response = self._execute_with_retry(self._invoke_text_api, prompt, system_instruction)
        
        # Save to Cache
        if self.cache and response:
            self.cache.set(full_prompt, response)
        return response

    def call_vlm_model(self, prompt: str, image_paths: list[str]) -> str:
        # Check Cache
        if self.cache:
            cached = self.cache.get(prompt, image_paths)
            if cached is not None:
                logger.info("VLM response retrieved from cache.")
                return cached

        response = self._execute_with_retry(self._invoke_vlm_api, prompt, image_paths)
        
        # Save to Cache
        if self.cache and response:
            self.cache.set(prompt, response, image_paths)
        return response


    def _invoke_text_api(self, prompt: str, system_instruction: str) -> str:
        # Attempt via unified google-genai Client (API key or Vertex AI)
        if self.genai_client:
            try:
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction
                
                res = self.genai_client.models.generate_content(
                    model=self.text_model,
                    contents=prompt,
                    config=config
                )
                if res.text:
                    return res.text.strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"google-genai Client text generate failed: {e}")

        # Attempt Gemini via package
        if self.has_gemini:
            try:
                import google.generativeai as genai
                # Use configured text model
                model = genai.GenerativeModel(
                    model_name=self.text_model,
                    system_instruction=system_instruction if system_instruction else None
                )
                res = model.generate_content(prompt)
                return res.text.strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"Gemini package text generate failed: {e}")

        # Attempt Gemini via raw REST HTTP requests (useful fallback)
        if self.gemini_key:
            try:
                # Direct HTTP call to Gemini
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.text_model}:generateContent?key={self.gemini_key}"
                headers = {"Content-Type": "application/json"}
                contents = [{"parts": [{"text": prompt}]}]
                if system_instruction:
                    # Note: system instruction structure for REST
                    payload = {
                        "contents": contents,
                        "systemInstruction": {"parts": [{"text": system_instruction}]}
                    }
                else:
                    payload = {"contents": contents}
                
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                res.raise_for_status()
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"Gemini REST text API call failed: {e}")

        # Attempt OpenAI via raw REST HTTP requests
        if self.openai_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}"
                }
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.0
                }
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"OpenAI REST text API call failed: {e}")

        # Attempt Anthropic via REST
        if self.anthropic_key:
            try:
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01"
                }
                payload = {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}]
                }
                if system_instruction:
                    payload["system"] = system_instruction
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                res.raise_for_status()
                return res.json()["content"][0]["text"].strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"Anthropic REST text API call failed: {e}")

        raise RuntimeError("No configured API keys or all model calls failed.")

    def _invoke_vlm_api(self, prompt: str, image_paths: list[str]) -> str:
        # Load Images
        pil_images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                # Ensure read so PIL caches or parses format
                img.verify()
                # Reopen for actual use since verify() invalidates the file handle
                img = Image.open(path)
                pil_images.append((img, Path(path).name))
            except Exception as e:
                logger.error(f"Failed to open image {path}: {e}")
                # We still append None or format failure, but let's let VLM try to handle others if available

        if not pil_images:
            raise RuntimeError(f"No valid images could be opened from paths: {image_paths}")

        # Attempt via unified google-genai Client (API key or Vertex AI)
        if self.genai_client:
            try:
                contents = [img for img, _ in pil_images] + [prompt]
                res = self.genai_client.models.generate_content(
                    model=self.vlm_model,
                    contents=contents
                )
                if res.text:
                    return res.text.strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"google-genai Client VLM generate failed: {e}")

        # Attempt Gemini via package
        if self.has_gemini:
            try:
                import google.generativeai as genai
                # Use configured VLM model
                model = genai.GenerativeModel(self.vlm_model)
                # Prepare contents list
                contents = [prompt]
                for img, _ in pil_images:
                    contents.append(img)
                
                res = model.generate_content(contents)
                return res.text.strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"Gemini package VLM generate failed: {e}")

        # Attempt Gemini via REST API (using base64 inlineData)
        if self.gemini_key:
            try:
                import base64
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.vlm_model}:generateContent?key={self.gemini_key}"
                headers = {"Content-Type": "application/json"}
                
                parts = []
                for img_path in image_paths:
                    with open(img_path, "rb") as f:
                        img_data = f.read()
                    b64_data = base64.b64encode(img_data).decode("utf-8")
                    # Dynamically inspect format
                    # Pillow can detect format, let's use a quick header helper or fallback to image/jpeg
                    mime_type = "image/jpeg"
                    if img_path.lower().endswith(".png"):
                        mime_type = "image/png"
                    elif img_path.lower().endswith(".webp"):
                        mime_type = "image/webp"
                    
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data
                        }
                    })
                parts.append({"text": prompt})
                
                payload = {
                    "contents": [{
                        "parts": parts
                    }]
                }
                
                res = requests.post(url, headers=headers, json=payload, timeout=45)
                res.raise_for_status()
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"Gemini REST VLM API call failed: {e}")

        # Attempt OpenAI via raw REST HTTP requests (base64 image payload)
        if self.openai_key:
            try:
                import base64
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}"
                }
                content_list = [{"type": "text", "text": prompt}]
                for img_path in image_paths:
                    with open(img_path, "rb") as f:
                        img_data = f.read()
                    b64_data = base64.b64encode(img_data).decode("utf-8")
                    mime_type = "image/jpeg"
                    if img_path.lower().endswith(".png"):
                        mime_type = "image/png"
                    elif img_path.lower().endswith(".webp"):
                        mime_type = "image/webp"
                    
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_data}"
                        }
                    })
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": content_list}
                    ],
                    "temperature": 0.0
                }
                res = requests.post(url, headers=headers, json=payload, timeout=45)
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if self._is_rate_limit(e):
                    raise e
                logger.error(f"OpenAI REST VLM API call failed: {e}")

        raise RuntimeError("No VLM-capable API keys configured or all calls failed.")
