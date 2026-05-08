"""
====================================================
  دمج Claude API — التوليد الفعلي
  كود جاهز للنسخ في مشروع الماستر
====================================================
"""
import json, urllib.request, urllib.error

# ==========================================
# الطريقة 1: Claude API (Anthropic)
# ==========================================

class ClaudeFiqhGenerator:
    """
    يستخدم Claude لتوليد الإجابات الفقهية.
    الاستخدام:
        gen = ClaudeFiqhGenerator(api_key="YOUR_KEY")
        answer = gen.generate(question, context)
    """
    API_URL = "https://api.anthropic.com/v1/messages"
    MODEL   = "claude-sonnet-4-20250514"

    # System prompt متخصص في الفقه
    SYSTEM = """أنت نظام خبير متخصص في الفقه الإسلامي المقارن.
قواعد الإجابة:
- استند حصراً إلى المعلومات الواردة في السياق المُعطى
- اذكر آراء المذاهب الأربعة مرتبةً: الحنفي ← المالكي ← الشافعي ← الحنبلي
- اذكر الدليل والمصدر لكل رأي
- اختم بالرأي الراجح مع التعليل
- نبّه دائماً أن الفتوى الشخصية تستلزم مراجعة عالم متخصص
- أسلوبك علمي رصين، تجنب التحيز لمذهب دون دليل"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, question: str, context: str,
                 max_tokens: int = 1024) -> str:
        user_prompt = f"""المعلومات المسترجعة من قاعدة المعرفة:
{context}

السؤال الفقهي: {question}

أجب بأسلوب علمي منظم مستنداً إلى المعلومات أعلاه فقط."""

        payload = json.dumps({
            "model":      self.MODEL,
            "max_tokens": max_tokens,
            "system":     self.SYSTEM,
            "messages":   [{"role": "user", "content": user_prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["content"][0]["text"]


# ==========================================
# الطريقة 2: OpenAI GPT-4 (بديل)
# ==========================================

class GPTFiqhGenerator:
    """بديل باستخدام OpenAI API"""
    API_URL = "https://api.openai.com/v1/chat/completions"
    MODEL   = "gpt-4o"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, question: str, context: str,
                 max_tokens: int = 1024) -> str:
        messages = [
            {"role": "system",
             "content": "أنت نظام خبير في الفقه الإسلامي المقارن. "
                        "أجب بدقة علمية مستنداً إلى السياق المعطى فقط."},
            {"role": "user",
             "content": f"السياق:\n{context}\n\nالسؤال: {question}"}
        ]
        payload = json.dumps({
            "model": self.MODEL,
            "messages": messages,
            "max_tokens": max_tokens
        }).encode("utf-8")

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]


# ==========================================
# الطريقة 3: نموذج محلي مفتوح المصدر
#   (للطلاب الذين لا يملكون مفتاح API)
# ==========================================

OFFLINE_TEMPLATE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  الفتوى الفقهية المقارنة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
المسألة: {title}
الباب  : {category}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{ijmaa_note}
آراء المذاهب:
{opinions}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
نوع الخلاف : {khilaf_type}
الراجح     : {rajih}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  هذا تحليل أكاديمي مقارن. للفتوى الشخصية
   يرجى مراجعة عالم متخصص.
"""

class OfflineGenerator:
    """
    توليد محلي بدون API — للاستخدام الأكاديمي.
    يُنسّق البيانات الفقهية في قالب جاهز.
    """
    MADHAB_AR = {
        "hanafi":"الحنفي","maliki":"المالكي",
        "shafii":"الشافعي","hanbali":"الحنبلي"
    }

    def generate_from_masala(self, masala: dict) -> str:
        opinions_lines = []
        for madhab, data in masala.get("madhabs", {}).items():
            name = self.MADHAB_AR.get(madhab, madhab)
            opinions_lines.append(
                f"• [{name}]\n"
                f"  الحكم  : {data['hukm']}\n"
                f"  الدليل : {data['daleel']}\n"
                f"  المصدر : {data['source']}"
            )
        ijmaa_note = "✅ هذه المسألة إجماعية متفق عليها\n" \
                     if masala.get("ijmaa") else ""
        return OFFLINE_TEMPLATE.format(
            title       = masala.get("title",""),
            category    = masala.get("category","") + " > " + masala.get("subcategory",""),
            ijmaa_note  = ijmaa_note,
            opinions    = "\n\n".join(opinions_lines),
            khilaf_type = masala.get("khilaf_type",""),
            rajih       = masala.get("rajih","")
        )


# ==========================================
# مثال تشغيلي (وضع Offline)
# ==========================================

if __name__ == "__main__":
    gen = OfflineGenerator()

    masala_test = {
        "title": "الصلاة خلف الإمام الفاسق",
        "category": "عبادات", "subcategory": "الصلاة",
        "madhabs": {
            "hanafi":  {"hukm":"تصح مع الكراهة التحريمية",    "daleel":"حديث: صلوا خلف كل بر وفاجر","source":"الهداية ج1 ص56"},
            "maliki":  {"hukm":"تصح مع الكراهة",              "daleel":"عمل الصحابة",                "source":"المدونة ج1 ص82"},
            "shafii":  {"hukm":"تصح مع الكراهة",              "daleel":"إجماع الصحابة",              "source":"المجموع ج4 ص255"},
            "hanbali": {"hukm":"لا تصح إن كان فسقه ظاهراً",  "daleel":"شرط العدالة في الإمام",      "source":"المغني ج2 ص7"},
        },
        "khilaf_type":"خلاف حقيقي",
        "rajih":"الصحة مع الكراهة عند الجمهور (حنفي، مالكي، شافعي)",
        "ijmaa": False
    }

    print(gen.generate_from_masala(masala_test))

    print("\n" + "="*52)
    print("  دليل استخدام الـ API في مشروعك")
    print("="*52)
    print("""
  للاستخدام مع Claude API:
  ─────────────────────────
  from api_integration import ClaudeFiqhGenerator

  gen = ClaudeFiqhGenerator(api_key="sk-ant-...")
  answer = gen.generate(question, context)

  للاستخدام مع GPT-4:
  ─────────────────────────
  from api_integration import GPTFiqhGenerator

  gen = GPTFiqhGenerator(api_key="sk-...")
  answer = gen.generate(question, context)

  بدون API (أكاديمي):
  ─────────────────────────
  from api_integration import OfflineGenerator

  gen = OfflineGenerator()
  answer = gen.generate_from_masala(masala_dict)
""")
