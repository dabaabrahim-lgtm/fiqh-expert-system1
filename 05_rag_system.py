"""
====================================================
  نظام RAG الفقهي — دمج الذكاء الاصطناعي
  Fiqh RAG System — AI Integration
  يعمل مع Anthropic Claude API
====================================================
"""
import json
import math
import urllib.request
import urllib.error

# ==========================================
# 1. محاكاة Embeddings (بدون مكتبات خارجية)
#    في الإنتاج: استخدم AraBERT أو sentence-transformers
# ==========================================

class SimpleEmbedder:
    """
    محاكاة بسيطة لتحويل النص إلى متجه رقمي.
    في المشروع الحقيقي: استبدل بـ AraBERT أو
    sentence-transformers مع نموذج عربي.
    """
    VOCAB = [
        "صلاة","زكاة","صيام","حج","وضوء","طهارة",
        "بيع","شراء","ربا","عقد","نكاح","طلاق",
        "سفر","مرض","ضرورة","مشقة","جمع","قصر",
        "ذهب","نصاب","مثقال","إمام","جماعة","فاسق",
        "أسهم","بورصة","بنك","فائدة","تأمين","رقمي"
    ]

    def embed(self, text: str) -> list:
        """تحويل النص إلى متجه بناءً على تكرار المفردات"""
        text_lower = text
        vec = []
        for word in self.VOCAB:
            # حساب TF بسيط مع وزن للمطابقة الجزئية
            exact  = text_lower.count(word)
            partial = sum(1 for w in text_lower.split() if word in w or w in word)
            vec.append(exact * 1.0 + partial * 0.4)
        # تطبيع المتجه
        norm = math.sqrt(sum(v**2 for v in vec)) or 1.0
        return [v / norm for v in vec]

    def cosine_similarity(self, v1: list, v2: list) -> float:
        """حساب التشابه بين متجهين"""
        dot   = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a**2 for a in v1)) or 1e-9
        norm2 = math.sqrt(sum(b**2 for b in v2)) or 1e-9
        return dot / (norm1 * norm2)


# ==========================================
# 2. قاعدة المتجهات (Vector Store)
# ==========================================

class VectorStore:
    """
    تخزين واسترجاع المسائل بالتشابه الدلالي.
    في الإنتاج: استخدم FAISS أو ChromaDB.
    """
    def __init__(self, embedder: SimpleEmbedder):
        self.embedder = embedder
        self.index    = []   # [(masala_id, vector, masala_data)]

    def add(self, masala_id: str, masala: dict):
        """إضافة مسألة مع متجهها"""
        text = (masala.get("title","") + " " +
                " ".join(masala.get("keywords",[])) + " " +
                masala.get("subcategory",""))
        vec = self.embedder.embed(text)
        self.index.append((masala_id, vec, masala))

    def search(self, query: str, top_k: int = 3) -> list:
        """استرجاع أقرب المسائل للسؤال"""
        q_vec = self.embedder.embed(query)
        scored = [
            (mid, self.embedder.cosine_similarity(q_vec, vec), data)
            for mid, vec, data in self.index
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(mid, sim, data) for mid, sim, data in scored[:top_k] if sim > 0.05]

    def build_from_db(self, masail_db: dict):
        """بناء الفهرس من قاعدة البيانات"""
        for mid, masala in masail_db.items():
            self.add(mid, masala)
        print(f"  ✅ تم فهرسة {len(self.index)} مسألة فقهية")


# ==========================================
# 3. بناء السياق (Context Builder)
# ==========================================

class ContextBuilder:
    """يبني النص الكامل الذي سيُرسل إلى نموذج الذكاء الاصطناعي"""

    MADHAB_AR = {
        "hanafi": "الحنفي", "maliki": "المالكي",
        "shafii": "الشافعي", "hanbali": "الحنبلي"
    }

    def build(self, question: str, retrieved: list) -> str:
        """بناء السياق من المسائل المسترجعة"""
        context_parts = []
        for rank, (mid, sim, masala) in enumerate(retrieved, 1):
            part = [f"[مسألة {rank} | تطابق: {sim*100:.0f}%]"]
            part.append(f"العنوان: {masala['title']}")
            part.append(f"الباب: {masala.get('category','')} > {masala.get('subcategory','')}")
            part.append("آراء المذاهب:")
            for madhab, data in masala.get("madhabs", {}).items():
                name = self.MADHAB_AR.get(madhab, madhab)
                part.append(f"  - {name}: {data['hukm']}")
                part.append(f"    الدليل: {data['daleel']}")
                part.append(f"    المصدر: {data['source']}")
            part.append(f"الراجح: {masala.get('rajih','')}")
            part.append(f"نوع الخلاف: {masala.get('khilaf_type','')}")
            if masala.get('ijmaa'):
                part.append("⚠️ هذه المسألة متفق عليها بالإجماع")
            context_parts.append("\n".join(part))

        return "\n\n".join(context_parts)

    def build_prompt(self, question: str, context: str) -> str:
        """بناء البرومبت الكامل"""
        return f"""أنت نظام خبير متخصص في الفقه الإسلامي المقارن.
مهمتك: الإجابة على الأسئلة الفقهية بدقة علمية وموضوعية، مع ذكر آراء المذاهب الأربعة وأدلتها.

المعلومات المسترجعة من قاعدة المعرفة الفقهية:
{context}

السؤال: {question}

قدّم إجابة منظمة تشمل:
1. تحديد المسألة وتصنيفها
2. آراء المذاهب الأربعة مع الأدلة
3. أسباب الخلاف (إن وجد)
4. الرأي الراجح مع التعليل
5. تنبيه بأن الفتوى الشخصية تستلزم مراجعة عالم متخصص

التزم بالأسلوب العلمي الفقهي، واستند فقط إلى المعلومات الواردة في قاعدة المعرفة أعلاه."""


# ==========================================
# 4. نظام RAG المتكامل
# ==========================================

class FiqhRAGSystem:
    """النظام المتكامل: بحث + توليد"""

    def __init__(self, masail_db: dict, api_key: str = None):
        self.embedder = SimpleEmbedder()
        self.store    = VectorStore(self.embedder)
        self.builder  = ContextBuilder()
        self.api_key  = api_key
        self.api_url  = "https://api.anthropic.com/v1/messages"

        print("🔧 تهيئة نظام RAG الفقهي...")
        self.store.build_from_db(masail_db)

    def retrieve(self, question: str, top_k: int = 2) -> list:
        """مرحلة الاسترجاع"""
        return self.store.search(question, top_k)

    def generate(self, prompt: str) -> str:
        """مرحلة التوليد عبر Claude API"""
        if not self.api_key:
            return "[وضع المحاكاة: يتطلب مفتاح API للتوليد الفعلي]"

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data    = payload,
            headers = {
                "Content-Type":      "application/json",
                "x-api-key":         self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            return f"خطأ في الاتصال بـ API: {e.code}"

    def ask(self, question: str) -> dict:
        """السؤال الكامل: استرجاع + سياق + توليد"""
        print(f"\n{'─'*52}")
        print(f"❓ السؤال: {question}")
        print(f"{'─'*52}")

        # ── الاسترجاع ──
        print("🔍 البحث في قاعدة المعرفة...")
        retrieved = self.retrieve(question)

        if not retrieved:
            return {"error": "لم يُعثر على مسائل مشابهة"}

        for mid, sim, m in retrieved:
            print(f"   ✓ [{mid}] {m['title']} — تطابق: {sim*100:.0f}%")

        # ── بناء السياق ──
        context = self.builder.build(question, retrieved)
        prompt  = self.builder.build_prompt(question, context)

        # ── التوليد ──
        print("🤖 توليد الإجابة...")
        answer = self.generate(prompt)

        # ── النتيجة ──
        result = {
            "question":  question,
            "retrieved": [{"id": m, "title": d["title"], "score": f"{s*100:.0f}%"}
                          for m, s, d in retrieved],
            "answer":    answer,
            "context_used": context[:300] + "..."
        }

        print(f"\n📋 المسائل المُستخدمة:")
        for r in result["retrieved"]:
            print(f"   • {r['title']} ({r['score']})")
        print(f"\n💬 الإجابة:\n{answer}")
        return result


# ==========================================
# 5. قاعدة البيانات + الاختبار
# ==========================================

MASAIL_DB = {
    "M001": {
        "title": "حكم الجمع بين الصلاتين",
        "category": "عبادات", "subcategory": "الصلاة",
        "keywords": ["جمع","صلاة","سفر","مرض","تقديم","تأخير"],
        "madhabs": {
            "hanafi":  {"hukm":"لا يجوز إلا للحاج في عرفة ومزدلفة",          "daleel":"حديث: صلوا كما رأيتموني أصلي","source":"الهداية ج1 ص85"},
            "maliki":  {"hukm":"يجوز للمسافر والمريض وفي المطر",              "daleel":"حديث معاذ في الجمع",          "source":"المدونة ج1 ص102"},
            "shafii":  {"hukm":"يجوز في السفر والمرض والمطر والخوف",          "daleel":"حديث ابن عباس في مسلم",       "source":"المجموع ج4 ص372"},
            "hanbali": {"hukm":"يجوز بأسباب متعددة منها السفر والشغل الشديد","daleel":"حديث ابن عباس: جمع من غير خوف","source":"المغني ج2 ص124"},
        },
        "khilaf_type":"خلاف حقيقي","rajih":"الجواز في السفر والمرض","ijmaa":False
    },
    "M002": {
        "title": "نصاب زكاة الذهب",
        "category": "عبادات", "subcategory": "الزكاة",
        "keywords": ["زكاة","ذهب","نصاب","مثقال","مقدار","غرام"],
        "madhabs": {
            "hanafi":  {"hukm":"عشرون مثقالاً (85غ)","daleel":"حديث علي رضي الله عنه","source":"بدائع الصنائع ج2"},
            "maliki":  {"hukm":"عشرون مثقالاً",       "daleel":"الإجماع والأثر",        "source":"الكافي لابن عبد البر"},
            "shafii":  {"hukm":"عشرون مثقالاً",       "daleel":"الإجماع",              "source":"الأم للشافعي ج2"},
            "hanbali": {"hukm":"عشرون مثقالاً",       "daleel":"الإجماع والأثر",       "source":"المغني ج3"},
        },
        "khilaf_type":"إجماع","rajih":"عشرون مثقالاً (85 غراماً)","ijmaa":True
    },
    "M003": {
        "title": "الصلاة خلف الإمام الفاسق",
        "category": "عبادات", "subcategory": "الصلاة",
        "keywords": ["إمام","فاسق","صلاة","جماعة","اقتداء","خلف"],
        "madhabs": {
            "hanafi":  {"hukm":"تصح مع الكراهة التحريمية",      "daleel":"حديث: صلوا خلف كل بر وفاجر","source":"الهداية ج1 ص56"},
            "maliki":  {"hukm":"تصح مع الكراهة",                "daleel":"عمل الصحابة",                "source":"المدونة ج1 ص82"},
            "shafii":  {"hukm":"تصح مع الكراهة",                "daleel":"إجماع الصحابة",              "source":"المجموع ج4 ص255"},
            "hanbali": {"hukm":"لا تصح إذا كان فسقه ظاهراً",   "daleel":"شرط العدالة في الإمام",      "source":"المغني ج2 ص7"},
        },
        "khilaf_type":"خلاف حقيقي","rajih":"الصحة مع الكراهة عند الجمهور","ijmaa":False
    },
    "M004": {
        "title": "حكم بيع الأسهم في البورصة",
        "category": "قضايا معاصرة", "subcategory": "المعاملات المالية",
        "keywords": ["أسهم","بورصة","بيع","شراء","استثمار","شركة","سهم"],
        "madhabs": {
            "hanafi":  {"hukm":"يجوز إن خلت الشركة من الربا",        "daleel":"القياس على بيع الحصص",              "source":"مجمع الفقه ق7"},
            "maliki":  {"hukm":"يجوز بشرط طهارة نشاط الشركة",        "daleel":"الأصل في المعاملات الإباحة",        "source":"مجلة مجمع الفقه ع7"},
            "shafii":  {"hukm":"يجوز في شركات النشاط الحلال",         "daleel":"الإذن الشرعي بالمشاركة",           "source":"قرار مجمع رقم 63"},
            "hanbali": {"hukm":"يجوز إن لم يزد الدين على ثلث الأصول","daleel":"شرط الخلو من الربا",                "source":"فتاوى ابن عثيمين ج18"},
        },
        "khilaf_type":"خلاف نسبي","rajih":"الجواز بشروط — قرار مجمع الفقه الإسلامي","ijmaa":False
    },
}

if __name__ == "__main__":
    # تهيئة النظام بدون API (وضع المحاكاة)
    rag = FiqhRAGSystem(MASAIL_DB, api_key=None)

    questions = [
        "ما حكم الصلاة خلف الإمام الفاسق؟",
        "هل يجوز شراء الأسهم في سوق البورصة؟",
        "كم نصاب زكاة الذهب بالغرام؟",
    ]

    for q in questions:
        rag.ask(q)
        print()
