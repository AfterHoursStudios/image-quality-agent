import json
from openai import OpenAI
from app.config import get_settings
from app.models.schemas import ImageScores, ScoreDetail


ANALYSIS_PROMPT = """Analyze this image for quality and provide scores from 1-100 for each criterion.
Return your analysis as a JSON object with this exact structure:

{
    "sharpness": {"score": <1-100>, "explanation": "<brief explanation>"},
    "lighting": {"score": <1-100>, "explanation": "<brief explanation>"},
    "composition": {"score": <1-100>, "explanation": "<brief explanation>"},
    "color": {"score": <1-100>, "explanation": "<brief explanation>"},
    "exposure": {"score": <1-100>, "explanation": "<brief explanation>"},
    "faces": {"score": <1-100>, "explanation": "<brief explanation>"} OR null if no faces present,
    "overall": {"score": <1-100>, "explanation": "<brief overall assessment>"}
}

Scoring criteria:
- sharpness: Focus and clarity of the image
- lighting: Quality and balance of lighting
- composition: Framing, rule of thirds, visual balance
- color: Color accuracy, white balance, saturation appropriateness
- exposure: Proper exposure, no blown highlights or crushed blacks
- faces: Quality of any faces (expression, focus, lighting on face). Set to null if no faces.
- overall: Weighted average considering all factors, with brief overall assessment

Keep explanations concise (1-2 sentences max). Return ONLY the JSON object, no additional text."""


async def analyze_image(image_url: str) -> ImageScores:
    """
    Analyze an image using OpenAI's vision model.

    Args:
        image_url: Public URL of the image to analyze

    Returns:
        ImageScores: Structured scoring results
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ],
        max_tokens=1000
    )

    content = response.choices[0].message.content

    # Parse the JSON response
    # Handle potential markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    scores_data = json.loads(content.strip())

    # Build ImageScores from parsed data
    return ImageScores(
        sharpness=ScoreDetail(**scores_data["sharpness"]),
        lighting=ScoreDetail(**scores_data["lighting"]),
        composition=ScoreDetail(**scores_data["composition"]),
        color=ScoreDetail(**scores_data["color"]),
        exposure=ScoreDetail(**scores_data["exposure"]),
        faces=ScoreDetail(**scores_data["faces"]) if scores_data.get("faces") else None,
        overall=ScoreDetail(**scores_data["overall"])
    )
