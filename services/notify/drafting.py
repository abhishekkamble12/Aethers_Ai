"""
Notice Drafting & Notification Dispatch Module
Supports:
1. Hindi and English notice generation for Parents and Teachers
2. WhatsApp click-to-share link builder for class teachers
3. Bedrock LLM generation with automatic static template fallback (circuit breaker)
4. Parent acknowledgement link builder
"""

import json
import os
import logging
import urllib.parse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
BEDROCK_REGION = os.environ.get("APP_REGION", "ap-south-1")

STATIC_NOTICES = {
    "english": {
        "parents_plan_b": (
            "Dear Parents, In compliance with GRAP Stage {stage} directives from the Directorate of Education, "
            "outdoor sports and physical education have been moved to indoor wellness sessions (chess, table tennis, yoga) "
            "to keep children safe and active. Please acknowledge receipt: {ack_link}"
        ),
        "parents_plan_a": (
            "Dear Parents, Due to elevated morning air pollution under Stage {stage}, scheduled physical activities have been "
            "rescheduled to lower-exposure afternoon slots. No classes are cancelled. Please acknowledge: {ack_link}"
        ),
        "teachers": (
            "Notice to Teachers: Timetable for {date} has been updated under Stage {stage} directives. "
            "PE staff: Please report to designated indoor halls. View your personalized roster: {roster_link}"
        )
    },
    "hindi": {
        "parents_plan_b": (
            "आदरणीय अभिभावक, शिक्षा निदेशालय के ग्रैप स्टेज {stage} के निर्देशों के अनुसार, "
            "बच्चों के स्वास्थ्य की सुरक्षा के लिए खेल कूद की गतिविधियों को सुरक्षित इनडोर सत्रों (शतरंज, टेबल टेनिस, योग) में स्थानांतरित किया गया है। "
            "कृपया प्राप्ति की पुष्टि करें: {ack_link}"
        ),
        "parents_plan_a": (
            "आदरणीय अभिभावक, स्टेज {stage} के तहत वायु गुणवत्ता को ध्यान में रखते हुए, शारीरिक गतिविधियों का समय बदल दिया गया है ताकि बच्चे सुरक्षित रहें। "
            "कोई भी क्लास रद्द नहीं की गई है। पुष्टि करें: {ack_link}"
        ),
        "teachers": (
            "शिक्षकों के लिए सूचना: स्टेज {stage} निर्देशों के अनुसार {date} की समय सारिणी अपडेट कर दी गई है। "
            "पीई शिक्षक कृपया निर्धारित इनडोर हॉल में उपस्थित रहें।"
        )
    }
}


def _invoke_bedrock_nova(
    audience: str,
    language: str,
    stage: str,
    plan_summary: Dict[str, Any],
    ack_link: str
) -> Optional[str]:
    """
    Attempts to invoke Amazon Bedrock (Nova Lite) to generate a context-aware safety notice.
    Returns generated text on success, or None on any failure (triggering static fallback).
    """
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

        swaps_count = len(plan_summary.get("plan_a", []))
        fallbacks_count = len(plan_summary.get("plan_b", []))
        exposure_reduction = plan_summary.get("exposure_reduction_pct", 0)

        lang_instruction = "in Hindi (Devanagari script)" if language == "hindi" else "in English"
        audience_instruction = "parents of school children" if audience == "parents" else "PE and subject teachers"

        prompt = (
            f"You are drafting an official school safety notice {lang_instruction} for {audience_instruction}.\n\n"
            f"Context:\n"
            f"- GRAP Stage {stage} has been declared by the Commission for Air Quality Management (CAQM) in Delhi-NCR.\n"
            f"- {swaps_count} outdoor periods were rescheduled to lower-pollution time slots (Plan A swaps).\n"
            f"- {fallbacks_count} outdoor periods were converted to indoor wellness sessions (Plan B indoor bank).\n"
            f"- Modelled outdoor exposure was reduced by {exposure_reduction}%.\n"
            f"- 100% of physical education minutes have been preserved through rescheduling.\n"
            f"- Parents should acknowledge receipt at: {ack_link}\n\n"
            f"Write a concise, empathetic, and factual safety notice (max 3 sentences). "
            f"Do NOT include any information not provided above. Do NOT invent regulations."
        )

        # Nova Lite uses Converse API format
        request_body = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 300,
                "temperature": 0.3,
                "topP": 0.9
            }
        })

        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=request_body
        )

        response_body = json.loads(response["body"].read())
        # Extract text from Nova Lite response format
        generated_text = response_body.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "").strip()

        if generated_text and len(generated_text) > 20:
            logger.info("Bedrock Nova Lite generated notice successfully (len=%d)", len(generated_text))
            return generated_text
        else:
            logger.warning("Bedrock returned empty or too-short response; falling back to static template")
            return None

    except ImportError:
        logger.info("boto3 not available; falling back to static template")
        return None
    except Exception as e:
        # Circuit breaker: any Bedrock failure (AccessDenied, throttle, network, credentials)
        # triggers immediate fallback to static templates with zero interruption
        logger.warning("Bedrock invocation failed (%s: %s); falling back to static template", type(e).__name__, str(e))
        return None


def draft_notice(
    plan: Dict[str, Any],
    audience: str = "parents", # "parents" or "teachers"
    language: str = "english", # "english" or "hindi"
    stage: str = "III",
    date_str: str = "2026-10-12",
    ack_base_url: str = "https://saans.delhi.gov.in/ack",
    force_fallback: bool = False
) -> Dict[str, Any]:
    """
    Drafts an official safety notice.
    Attempts Bedrock (Nova Lite) generation first. On any failure — AccessDeniedException,
    missing credentials, throttle, network error — immediately falls back to pre-validated
    static bilingual templates with zero downtime (circuit breaker pattern).
    """
    decision_id = plan.get("decision_id", "demo")
    short_ack_id = decision_id.split("#")[-1] if "#" in decision_id else "ack101"
    ack_link = f"{ack_base_url}/{short_ack_id}"
    has_swaps = len(plan.get("plan_a", [])) > 0
    fallback_used = force_fallback
    model_used = "STATIC_TEMPLATE_FALLBACK"
    notice_text = None

    # 1. Attempt Bedrock generation (unless force_fallback is set)
    if not force_fallback:
        bedrock_result = _invoke_bedrock_nova(
            audience=audience,
            language=language,
            stage=stage,
            plan_summary=plan,
            ack_link=ack_link
        )
        if bedrock_result:
            notice_text = bedrock_result
            model_used = f"Bedrock-{BEDROCK_MODEL_ID}"
            fallback_used = False

    # 2. Static template fallback (circuit breaker)
    if notice_text is None:
        fallback_used = True
        model_used = "STATIC_TEMPLATE_FALLBACK"
        lang_dict = STATIC_NOTICES.get(language, STATIC_NOTICES["english"])

        if audience == "parents":
            template = lang_dict["parents_plan_a"] if has_swaps else lang_dict["parents_plan_b"]
            notice_text = template.format(stage=stage, ack_link=ack_link)
        else:
            template = lang_dict["teachers"]
            notice_text = template.format(stage=stage, date=date_str, roster_link=f"https://saans.delhi.gov.in/roster/{decision_id}")

    # Build WhatsApp Click-to-Share link
    encoded_text = urllib.parse.quote(notice_text)
    whatsapp_share_url = f"https://api.whatsapp.com/send?text={encoded_text}"

    return {
        "audience": audience,
        "language": language,
        "notice_text": notice_text,
        "whatsapp_click_to_share_url": whatsapp_share_url,
        "ack_link": ack_link,
        "model_used": model_used,
        "fallback_used": fallback_used
    }


def generate_parent_broadcast_package(
    plan: Dict[str, Any],
    stage: str = "III"
) -> Dict[str, Any]:
    """
    Creates complete bilingual notice package for WhatsApp distribution.
    """
    eng_notice = draft_notice(plan, audience="parents", language="english", stage=stage)
    hin_notice = draft_notice(plan, audience="parents", language="hindi", stage=stage)
    teacher_notice = draft_notice(plan, audience="teachers", language="english", stage=stage)

    return {
        "english": eng_notice,
        "hindi": hin_notice,
        "teacher": teacher_notice,
        "whatsapp_url_english": eng_notice["whatsapp_click_to_share_url"],
        "whatsapp_url_hindi": hin_notice["whatsapp_click_to_share_url"]
    }
