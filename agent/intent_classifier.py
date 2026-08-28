"""
Fuzzy Intent Classifier for Inbound Customer Turns.
Supports bilingual Romanized Hinglish, Indian English, and Devanagari Hindi.
"""
import re
from typing import Literal, Dict, Any

CustomerIntent = Literal[
    "agree_to_pay",
    "dispute_charge",
    "reschedule_request",
    "ghost_no_response",
    "aggressive_pushback",
    "partial_payment_offer",
    "payment_completed",
    "link_issue_retry",
    "payment_method_query",
    "gratitude_close",
    "neutral_query"
]


class HinglishIntentClassifier:
    def __init__(self):
        self.intent_patterns = {
            "ghost_no_response": [
                r"^\s*$", r"^\.+$", r"no response", r"silent", r"ghost", r"^\.{3,}$"
            ],
            "dispute_charge": [
                r"cancel", r"galat", r"fraud", r"wrong charge", r"nahi liya",
                r"dispute", r"already paid", r"rectify", r"dobara kyu",
                r"कैंसिल", r"गलत", r"फ्रॉड", r"विवाद", r"नहीं लिया", r"पहले ही", r"दोबारा"
            ],
            "reschedule_request": [
                r"salary", r"tight", r"next week", r"friday", r"time de",
                r"paise nahi", r"baad mein", r"reschedule", r"kal", r"parso",
                r"सैलरी", r"समय", r"टाइम", r"शुक्रवार", r"फ्राइडे", r"पैसे नहीं", r"बाद में", r"कल", r"परसों", r"रीशेड्यूल"
            ],
            "partial_payment_offer": [
                r"half", r"adha", r"partial", r"aadha", r"part payment",
                r"installment", r"abhi 50%", r"kuch amount",
                r"आधा", r"किस्त", r"पार्टियल", r"५०%", r"50%"
            ],
            "aggressive_pushback": [
                r"baar baar", r"harass", r"call mat karo", r"tamiz", r"police",
                r"complaint", r"dimag mat khao", r"chilla",
                r"कॉल मत करो", r"तमीज", r"पुलिस", r"शिकायत", r"परेशान", r"दिमाग मत"
            ],
            "link_issue_retry": [
                r"link nahi", r"not working", r"expired", r"invalid", r"send again",
                r"dusra link", r"fir se bhejo", r"resend", r"open nahi ho raha", r"nahi khul raha",
                r"लिंक नहीं", r"फिर से भेजो", r"खुल नहीं रहा", r"रीसेंड", r"काम नहीं कर रहा"
            ],
            "payment_method_query": [
                r"kaise pay", r"qr code", r"gpay", r"phonepe", r"paytm", r"netbanking",
                r"credit card", r"debit card", r"method", r"kisme karu", r"options",
                r"गूगल पे", r"फोन पे", r"कार्ड", r"कैसे पे करूं"
            ],
            "gratitude_close": [
                r"thank you", r"thanks", r"dhanyawad", r"shukriya", r"bye", r"take care",
                r"धन्यवाद", r"शुक्रिया", r"अलविदा"
            ],
            "agree_to_pay": [
                # Affirmations & English agreements
                r"yes", r"please", r"sure", r"do it", r"okay", r"ok", r"go ahead", r"share it",
                r"send it", r"proceed", r"i will pay", r"ready to pay",
                # Hinglish agreements
                r"link", r"bhej do", r"abhi kar deta", r"bhejo", r"pay karta",
                r"done", r"upi", r"kar diya", r"karta hoon", r"send link",
                r"qr code", r"karo", r"haan bhai", r"theek hai", r"pay", r"payment", r"bhej",
                r"haan ji", r"han ji", r"kar dijiye", r"kr dijeye", r"kar do", r"kardo",
                r"bhej दीजिए", r"chalega", r"thik hai", r"bhejiye",
                # Devanagari agreements
                r"लिंक", r"भेज", r"पेमेंट", r"पे", r"हाँ", r"कर देता", r"कर दूंगा", r"कर दुंगा",
                r"कर दीजिए", r"कर दो", r"भेज दीजिए", r"हाँ जी", r"यूपीआई", r"डन", r"सेंड", r"क्यूआर", r"ठीक है"
            ],
            "payment_completed": [
                r"payment ho gaya", r"i have paid", r"paid via link",
                r"check karo", r"check kar lo", r"transfer kar diya",
                r"पेमेंट हो गया", r"चेक कर लो", r"पैसे भेज दिए"
            ]
        }

    def classify(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip().lower()
        
        if not cleaned or cleaned in ["...", "none", "silent", "[silence]"]:
            return {"intent": "ghost_no_response", "confidence": 0.99, "matched_pattern": "silence"}

        for intent, patterns in self.intent_patterns.items():
            for pat in patterns:
                if re.search(pat, cleaned, re.IGNORECASE):
                    return {
                        "intent": intent,
                        "confidence": 0.95,
                        "matched_pattern": pat
                    }

        return {"intent": "neutral_query", "confidence": 0.60, "matched_pattern": "fallback"}
