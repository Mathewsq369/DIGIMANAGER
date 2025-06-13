import base64
import os
import uuid
from django.conf import settings
from openai import OpenAI
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
import requests

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def save_base64_image(base64_data, filename=None):
    if not filename:
        filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(settings.MEDIA_ROOT, "ai_generated", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(base64_data))
    return path, f"ai_generated/{filename}"  # Returns file path & relative path

def generate_dalle_image(prompt):
    response = client.images.generate(
        model="dall-e-3",  # or "dall-e-2"
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    image_url = response.data[0].url

    # Download and save locally
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(settings.MEDIA_ROOT, "ai_generated", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    img_data = requests.get(image_url).content
    with open(path, 'wb') as f:
        f.write(img_data)

    return path  # full path to saved image


def refine_image_gpt4(post, image_call_id, prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
            {"type": "image_generation_call", "id": image_call_id},
        ],
        tools=[{"type": "image_generation"}],
    )

    for output in response.output:
        if output.type == "image_generation_call":
            return save_base64_image(output.result)


def generate_image_sd(post, prompt):
    model_id = "sd-legacy/stable-diffusion-v1-5"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        cache_dir=settings.HUGGINGFACE_CACHE_DIR,
        torch_dtype=torch.float16
    )
    pipe = pipe.to("cuda")

    image = pipe(prompt).images[0]
    path = os.path.join(settings.MEDIA_ROOT, "ai_generated")
    os.makedirs(path, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    image_path = os.path.join(path, filename)
    image.save(image_path)

    return settings.MEDIA_URL + f"ai_generated/{filename}"