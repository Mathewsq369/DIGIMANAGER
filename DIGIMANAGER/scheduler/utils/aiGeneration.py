import openai
import base64
import os
from django.core.files.base import ContentFile
from ..models import AIGeneratedAsset

# GPT-4 Image Generation
def generate_image_gpt4(post, prompt):
    response = openai.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        tools=[{"type": "image_generation"}],
    )

    image_data = [
        output.result for output in response.output
        if output.type == "image_generation_call"
    ]

    if image_data:
        image_base64 = image_data[0]
        image_file = ContentFile(base64.b64decode(image_base64), name=f'post_{post.id}_ai.png')
        
        post.image.save(f'post_{post.id}_ai.png', image_file)
        post.generated_image_by = "gpt-4.1-mini"
        post.save()

        AIGeneratedAsset.objects.create(
            post=post,
            asset_type='image',
            source_model='gpt-4.1-mini',
            generation_prompt=prompt,
            output_data=image_base64,
            file=post.image
        )


# GPT-4 Image Refinement
def refine_image_gpt4(post, image_call_id, prompt):
    response = openai.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            {"type": "image_generation_call", "id": image_call_id},
        ],
        tools=[{"type": "image_generation"}],
    )

    image_data = [
        output.result for output in response.output
        if output.type == "image_generation_call"
    ]

    if image_data:
        image_base64 = image_data[0]
        image_file = ContentFile(base64.b64decode(image_base64), name=f'post_{post.id}_refined.png')
        
        post.image.save(f'post_{post.id}_refined.png', image_file)
        post.save()

        AIGeneratedAsset.objects.create(
            post=post,
            asset_type='image',
            source_model='gpt-4.1-mini-refined',
            generation_prompt=prompt,
            output_data=image_base64,
            file=post.image
        )


# Stable Diffusion (GPU Required)
def generate_image_sd(post, prompt):
    from diffusers import StableDiffusionPipeline
    import torch
    from PIL import Image

    model_id = "sd-legacy/stable-diffusion-v1-5"
    pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipe = pipe.to("cuda")

    image = pipe(prompt).images[0]
    image_path = f"media/ai_generated/post_{post.id}_sd.png"
    image.save(image_path)

    with open(image_path, "rb") as img_file:
        post.image.save(f'post_{post.id}_sd.png', ContentFile(img_file.read()))
        post.generated_image_by = "stable-diffusion-v1.5"
        post.save()

        AIGeneratedAsset.objects.create(
            post=post,
            asset_type='image',
            source_model='stable-diffusion-v1.5',
            generation_prompt=prompt,
            output_data=image_path,
            file=f'ai_generated/post_{post.id}_sd.png'
        )