from django.shortcuts import render, redirect
from .forms import ContentPromptForm
from .models import ContentPrompt
from transformers import pipeline
from django.contrib.auth.decorators import login_required
#############################
#######suspicious############
#############################
import base64
import os
import uuid
from django.http import JsonResponse
from django.conf import settings
from PIL import Image
from io import BytesIO
#############################
#############################
#############################

captionGenerator = pipeline('text-generation', model='gpt2')

@login_required
def generateCaption(request):
    if request.method == 'POST':
        form = ContentPromptForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            # Tone hint
            tone_prefix = f"Make this {obj.tone}: "
            generated = captionGenerator(tone_prefix + obj.prompt, max_length=50, num_return_sequences=1)
            obj.generated_caption = generated[0]['generated_text']
            obj.save()
            return redirect('captionDetail', obj.id)
    else:
        form = ContentPromptForm()
    return render(request, 'contentgen/generateCaption.html', {'form': form})

@login_required
def captionDetail(request, pk):
    prompt = ContentPrompt.objects.get(pk=pk, user=request.user)
    return render(request, 'contentgen/captionDetail.html', {'prompt': prompt})






def generate_ai_image(request):
    if request.method == "POST":
        caption = request.POST.get("caption")
        model = request.POST.get("model", "dalle")

        if not caption:
            return JsonResponse({"error": "Caption is required."}, status=400)

        # Simulated AI image generation logic (replace with actual AI API)
        image = Image.new('RGB', (512, 512), color='lightblue')
        draw = ImageDraw.Draw(image)
        draw.text((10, 250), caption, fill='black')

        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"{uuid.uuid4()}.png"
        save_path = os.path.join(settings.MEDIA_ROOT, "ai_temp", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(buffer.getvalue())

        return JsonResponse({
            "image_url": settings.MEDIA_URL + f"ai_temp/{filename}"
        })

    return JsonResponse({"error": "Invalid request."}, status=400)
