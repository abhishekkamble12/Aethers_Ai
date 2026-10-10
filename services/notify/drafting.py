"""
Notice Drafting & Notification Dispatch Module
Supports:
1. Hindi and English notice generation for Parents and Teachers
2. WhatsApp click-to-share link builder for class teachers
3. Bedrock LLM generation with automatic static template fallback (circuit breaker)
4. Link to the public receipt page (PUBLIC_BASE_URL/verify/{receipt_id}) so anyone can check the decision

Every fact in a notice comes from the approved plan. The only link is our own receipt page; when
PUBLIC_BASE_URL or the receipt ID is missing, the notice simply has no link.
"""

import json
import os
import logging
import re
import urllib.parse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
BEDROCK_REGION = os.environ.get("APP_REGION", "ap-south-1")

STATIC_NOTICES = {
    "english": {
        "parents_plan_b": (
            "Dear Parents, In compliance with GRAP Stage {stage} directives, outdoor sports and physical education "
            "today are replaced by indoor physical sessions (yoga, table tennis, fitness circuits) so children stay "
            "active away from polluted air.{verify_line}"
        ),
        "parents_plan_a": (
            "Dear Parents, Because of high air pollution under GRAP Stage {stage}, some outdoor physical activity "
            "periods today have been moved to times with lower forecast pollution. No classes are cancelled.{verify_line}"
        ),
        "teachers": (
            "Notice to Teachers: Today's timetable ({date}) has been updated under GRAP Stage {stage}. "
            "PE staff: please run the assigned indoor physical sessions in the indoor venues listed in today's plan.{verify_line}"
        ),
        "verify_line": " Verify this decision: {url}",
    },
    "hindi": {
        "parents_plan_b": (
            "आदरणीय अभिभावक, ग्रैप स्टेज {stage} के निर्देशों के अनुसार, "
            "आज खेल-कूद की बाहरी गतिविधियों की जगह इनडोर शारीरिक सत्र (योग, टेबल टेनिस, व्यायाम) होंगे, "
            "ताकि बच्चे प्रदूषित हवा से दूर सक्रिय रहें।{verify_line}"
        ),
        "parents_plan_a": (
            "आदरणीय अभिभावक, ग्रैप स्टेज {stage} के तहत वायु प्रदूषण अधिक होने के कारण आज कुछ शारीरिक गतिविधि के पीरियड "
            "कम प्रदूषण वाले समय पर किए गए हैं। कोई कक्षा रद्द नहीं की गई है।{verify_line}"
        ),
        "teachers": (
            "शिक्षकों के लिए सूचना: ग्रैप स्टेज {stage} के अनुसार आज ({date}) की समय सारिणी अपडेट की गई है। "
            "पीई शिक्षक आज की योजना में दिए गए इनडोर सत्र लें।{verify_line}"
        ),
        "verify_line": " इस निर्णय की जाँच करें: {url}",
    }
}


def verify_url(receipt_id: Optional[str], public_base_url: Optional[str] = None) -> Optional[str]:
    base = (public_base_url if public_base_url is not None else os.environ.get("PUBLIC_BASE_URL", "")).rstrip("/")
    return f"{base}/verify/{receipt_id}" if base and receipt_id else None


def plan_facts(plan: Dict[str, Any]) -> Dict[str, Any]:
    """The only facts a notice may state, all read from the approved plan."""
    pe = plan.get("pe_minutes") or {}
    return {
        "periods_moved": len(plan.get("plan_a", [])),
        "periods_replaced_indoor": len(plan.get("plan_b", [])),
        "pe_minutes_scheduled": pe.get("scheduled"),
        "pe_minutes_kept_active": pe.get("kept_active"),
        "modelled_exposure_reduction_pct": plan.get("exposure_reduction_pct"),
    }


def _invoke_bedrock_nova(
    audience: str,
    language: str,
    stage: str,
    plan_summary: Dict[str, Any],
    link: Optional[str]
) -> Optional[str]:
    """
    Attempts to invoke Amazon Bedrock (Nova Lite) to generate a context-aware safety notice.
    Returns generated text on success, or None on any failure (triggering static fallback).
    """
    try:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

        facts = plan_facts(plan_summary)
        lang_instruction = "in Hindi (Devanagari script)" if language == "hindi" else "in English"
        audience_instruction = "parents of school children" if audience == "parents" else "PE and subject teachers"

        prompt = (
            f"You are drafting an official school safety notice {lang_instruction} for {audience_instruction}.\n\n"
            f"Facts (use only these):\n"
            f"- GRAP Stage {stage} is in force in Delhi-NCR.\n"
            f"- {facts['periods_moved']} outdoor activity periods were moved to times with lower forecast pollution.\n"
            f"- {facts['periods_replaced_indoor']} outdoor activity periods were replaced by indoor physical sessions.\n"
            f"- {facts['pe_minutes_kept_active']} of {facts['pe_minutes_scheduled']} scheduled PE minutes stay physically active.\n"
            + (f"- Anyone can verify this decision at: {link}\n" if link else "")
            + "\nWrite a concise, factual notice (max 3 sentences). Do not add any other numbers, regulations, "
            "health claims or links."
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
    date_str: Optional[str] = None,
    receipt_id: Optional[str] = None,
    public_base_url: Optional[str] = None,
    force_fallback: bool = False
) -> Dict[str, Any]:
    """
    Drafts an official safety notice.
    Attempts Bedrock (Nova Lite) generation first. On any failure — AccessDeniedException,
    missing credentials, throttle, network error — immediately falls back to pre-validated
    static bilingual templates with zero downtime (circuit breaker pattern).
    """
    link = verify_url(receipt_id, public_base_url)
    if date_str is None:  # the decision's own date, e.g. TENANT#demo#2026-10-12#MORN
        m = re.search(r"#(\d{4}-\d{2}-\d{2})#", plan.get("decision_id", ""))
        date_str = m.group(1) if m else "today"
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
            link=link
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
        verify_line = lang_dict["verify_line"].format(url=link) if link else ""

        if audience == "parents":
            template = lang_dict["parents_plan_a"] if has_swaps else lang_dict["parents_plan_b"]
            notice_text = template.format(stage=stage, verify_line=verify_line)
        else:
            template = lang_dict["teachers"]
            notice_text = template.format(stage=stage, date=date_str, verify_line=verify_line)

    # Build WhatsApp Click-to-Share link
    encoded_text = urllib.parse.quote(notice_text)
    whatsapp_share_url = f"https://api.whatsapp.com/send?text={encoded_text}"

    return {
        "audience": audience,
        "language": language,
        "notice_text": notice_text,
        "whatsapp_click_to_share_url": whatsapp_share_url,
        "verify_url": link,
        "facts": plan_facts(plan),
        "model_used": model_used,
        "fallback_used": fallback_used
    }


def generate_parent_broadcast_package(
    plan: Dict[str, Any],
    stage: str = "III",
    receipt_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates complete bilingual notice package for WhatsApp distribution.
    """
    eng_notice = draft_notice(plan, audience="parents", language="english", stage=stage, receipt_id=receipt_id)
    hin_notice = draft_notice(plan, audience="parents", language="hindi", stage=stage, receipt_id=receipt_id)
    teacher_notice = draft_notice(plan, audience="teachers", language="english", stage=stage, receipt_id=receipt_id)

    return {
        "english": eng_notice,
        "hindi": hin_notice,
        "teacher": teacher_notice,
        "whatsapp_url_english": eng_notice["whatsapp_click_to_share_url"],
        "whatsapp_url_hindi": hin_notice["whatsapp_click_to_share_url"]
    }
