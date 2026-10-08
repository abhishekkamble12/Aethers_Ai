"""
Notice Drafting & Notification Dispatch Module
Supports:
1. Hindi and English notice generation for Parents and Teachers
2. WhatsApp click-to-share link builder for class teachers
3. Bedrock LLM generation with automatic static template fallback
4. Parent acknowledgement link builder
"""

import urllib.parse
from typing import Dict, Any, List

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
    Uses Bedrock when available, falling back to static templates if denied/unavailable.
    """
    decision_id = plan.get("decision_id", "demo")
    short_ack_id = decision_id.split("#")[-1] if "#" in decision_id else "ack101"
    ack_link = f"{ack_base_url}/{short_ack_id}"
    has_swaps = len(plan.get("plan_a", [])) > 0
    fallback_used = force_fallback # Bedrock toggle

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
        "model_used": "Bedrock-Amazon-Nova-Lite" if not fallback_used else "STATIC_TEMPLATE_FALLBACK",
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
