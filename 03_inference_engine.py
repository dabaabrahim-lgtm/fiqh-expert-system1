"""
====================================================
  محرك الاستنتاج الفقهي
  Fiqh Inference Engine
====================================================
"""
import re
import math
from dataclasses import dataclass, field
from typing import Optional


# ==========================================
# هياكل البيانات الأساسية
# ==========================================

@dataclass
class FiqhQuery:
    """يمثّل سؤالاً فقهياً وارداً من المستخدم"""
    raw_text: str
    cleaned_text: str = ""
    category: str = ""
    keywords: list = field(default_factory=list)
    madhab_filter: Optional[str] = None  # إذا أراد المستخدم مذهباً بعينه

@dataclass
class MadhhabOpinion:
    """رأي مذهب واحد في مسألة"""
    madhab: str
    hukm: str
    daleel: str
    source: str
    confidence: float = 1.0

@dataclass
class FiqhResponse:
    """إجابة كاملة من النظام الخبير"""
    question: str
    masala_title: str
    masala_id: str
    opinions: list
    rajih: str
    khilaf_type: str
    ijmaa: bool
    overall_confidence: float
    match_score: float
    asbaab_khilaf: list = field(default_factory=list)

    def display(self):
        names = {
            "hanafi":  "المذهب الحنفي",
            "maliki":  "المذهب المالكي",
            "shafii":  "المذهب الشافعي",
            "hanbali": "المذهب الحنبلي"
        }
        sep = "═" * 52
        print(f"\n{sep}")
        print(f"  📖 المسألة: {self.masala_title}")
        print(f"  ❓ سؤالك:   {self.question}")
        print(f"  🎯 تطابق:   {self.match_score*100:.0f}%  |  ثقة: {self.overall_confidence*100:.0f}%")
        print(sep)

        if self.ijmaa:
            print("  ✅ هذه المسألة متفق عليها بين المذاهب (إجماع)\n")

        for op in self.opinions:
            print(f"  [{names.get(op.madhab, op.madhab)}]")
            print(f"    الحكم  : {op.hukm}")
            print(f"    الدليل : {op.daleel}")
            print(f"    المصدر : {op.source}")
            print()

        print(f"  ⚖️  نوع الخلاف : {self.khilaf_type}")
        print(f"  📌 الراجح     : {self.rajih}")

        if self.asbaab_khilaf:
            print(f"\n  🔍 أسباب الخلاف:")
            for s in self.asbaab_khilaf:
                print(f"     • {s}")
        print(sep)


# ==========================================
# المرحلة الأولى: معالجة النص العربي
# ==========================================

class ArabicTextProcessor:
    """تنظيف النص العربي واستخراج الكلمات المفتاحية"""

    STOP_WORDS = {
        "ما","هل","كيف","من","في","على","عن","إلى","هذا","هذه",
        "التي","الذي","وما","أن","إن","كان","يكون","حكم","أو"
    }

    FIQH_SYNONYMS = {
        "صلاة": ["الصلاة", "صلى", "يصلي", "مصلى"],
        "زكاة": ["الزكاة", "زكى", "إخراج الزكاة"],
        "صيام": ["الصيام", "الصوم", "صام", "يصوم"],
        "حج":   ["الحج", "حجّ", "المناسك"],
        "نكاح": ["الزواج", "النكاح", "تزوج", "العقد"],
        "طلاق": ["الطلاق", "طلّق", "الفراق"],
        "بيع":  ["البيع", "الشراء", "التجارة", "المعاملة"],
        "ربا":  ["الربا", "الفائدة", "الزيادة الربوية"],
    }

    def normalize(self, text: str) -> str:
        """تطبيع النص: إزالة التشكيل والتنويع في الكتابة"""
        text = re.sub(r'[\u064B-\u065F]', '', text)   # إزالة التشكيل
        text = re.sub(r'[أإآ]', 'ا', text)             # توحيد الألف
        text = re.sub(r'ة', 'ه', text)                 # توحيد التاء المربوطة
        text = re.sub(r'ى', 'ي', text)                 # توحيد الياء
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_keywords(self, text: str) -> list:
        """استخراج الكلمات المفتاحية الفقهية"""
        normalized = self.normalize(text)
        tokens = normalized.split()
        # إزالة كلمات الوقف
        meaningful = [t for t in tokens if t not in self.STOP_WORDS and len(t) > 2]
        # إضافة المرادفات
        expanded = set(meaningful)
        for token in meaningful:
            for key, synonyms in self.FIQH_SYNONYMS.items():
                norm_syns = [self.normalize(s) for s in synonyms]
                if token in norm_syns or token == self.normalize(key):
                    expanded.add(self.normalize(key))
        return list(expanded)

    def detect_category(self, keywords: list) -> str:
        """تصنيف المسألة تلقائياً"""
        category_map = {
            "عبادات":          ["صلاه","زكاه","صيام","حج","وضوء","طهاره","اذان"],
            "معاملات":         ["بيع","شراء","ربا","عقد","إجاره","شركه","قرض"],
            "أحوال شخصية":    ["نكاح","طلاق","زواج","ميراث","وصيه","نفقه"],
            "جنايات وعقوبات":  ["قتل","سرقه","قصاص","حد","عقوبه","دم"],
            "قضايا معاصرة":    ["بنك","تامين","انترنت","رقمي","عمله","سهم"],
        }
        scores = {cat: 0 for cat in category_map}
        for kw in keywords:
            for cat, terms in category_map.items():
                if any(kw in t or t in kw for t in terms):
                    scores[cat] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "عام"


# ==========================================
# المرحلة الثانية: محرك البحث والمطابقة
# ==========================================

class SearchEngine:
    """يبحث عن المسائل الأكثر تطابقاً مع السؤال"""

    def __init__(self, processor: ArabicTextProcessor):
        self.processor = processor

    def score(self, query_keywords: list, masala: dict) -> float:
        """حساب درجة التطابق بين السؤال والمسألة"""
        masala_keywords = [self.processor.normalize(k)
                           for k in masala.get("keywords", [])]
        masala_title    = self.processor.normalize(masala.get("title", ""))
        masala_sub      = self.processor.normalize(masala.get("subcategory", ""))

        score = 0.0
        for qk in query_keywords:
            # مطابقة في الكلمات المفتاحية
            if qk in masala_keywords:
                score += 1.0
            # مطابقة جزئية في الكلمات المفتاحية
            elif any(qk in mk or mk in qk for mk in masala_keywords):
                score += 0.6
            # مطابقة في العنوان
            if qk in masala_title:
                score += 0.8
            # مطابقة في الصنف الفرعي
            if qk in masala_sub:
                score += 0.5

        # تطبيع الدرجة
        max_possible = len(query_keywords) * 2.3
        return min(score / max_possible, 1.0) if max_possible > 0 else 0.0

    def find_best(self, query_keywords: list,
                  masail_db: dict, top_n: int = 3) -> list:
        """إيجاد أفضل المسائل تطابقاً"""
        scored = [
            (mid, self.score(query_keywords, m), m)
            for mid, m in masail_db.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(mid, sc, m) for mid, sc, m in scored[:top_n] if sc > 0.1]


# ==========================================
# المرحلة الثالثة: محرك الاستنتاج الرئيسي
# ==========================================

class FiqhInferenceEngine:
    """المحرك الرئيسي: يربط جميع المراحل"""

    MADHAB_NAMES = {
        "hanafi":  "الحنفي",
        "maliki":  "المالكي",
        "shafii":  "الشافعي",
        "hanbali": "الحنبلي"
    }

    def __init__(self, masail_db: dict):
        self.db        = masail_db
        self.processor = ArabicTextProcessor()
        self.searcher  = SearchEngine(self.processor)

    def process(self, question: str,
                madhab_filter: str = None) -> Optional[FiqhResponse]:
        """المعالجة الكاملة من السؤال إلى الجواب"""

        # ── المرحلة 1: تحليل السؤال ──
        keywords = self.processor.extract_keywords(question)
        category = self.processor.detect_category(keywords)

        # ── المرحلة 2: البحث ──
        results = self.searcher.find_best(keywords, self.db)
        if not results:
            return None

        masala_id, match_score, masala = results[0]

        # ── المرحلة 3: بناء الآراء ──
        opinions = []
        for madhab in ["hanafi","maliki","shafii","hanbali"]:
            if madhab_filter and madhab != madhab_filter:
                continue
            data = masala.get("madhabs", {}).get(madhab)
            if data:
                opinions.append(MadhhabOpinion(
                    madhab     = madhab,
                    hukm       = data["hukm"],
                    daleel     = data["daleel"],
                    source     = data["source"],
                    confidence = data.get("confidence", 0.9)
                ))

        # ── المرحلة 4: حساب الثقة الكلية ──
        avg_conf = (sum(o.confidence for o in opinions) / len(opinions)
                    if opinions else 0)
        overall  = round(avg_conf * match_score * 1.1, 3)
        overall  = min(overall, 1.0)

        return FiqhResponse(
            question          = question,
            masala_title      = masala["title"],
            masala_id         = masala_id,
            opinions          = opinions,
            rajih             = masala.get("rajih",""),
            khilaf_type       = masala.get("khilaf_type",""),
            ijmaa             = masala.get("ijmaa", False),
            overall_confidence= overall,
            match_score       = match_score,
            asbaab_khilaf     = masala.get("asbaab_khilaf",[])
        )


# ==========================================
# قاعدة بيانات تجريبية
# ==========================================

MASAIL_DB = {
    "M001": {
        "title": "حكم الجمع بين الصلاتين",
        "category": "عبادات", "subcategory": "الصلاة",
        "keywords": ["جمع","صلاة","سفر","مرض","تقديم","تأخير","صلوات"],
        "madhabs": {
            "hanafi":  {"hukm":"لا يجوز إلا للحاج في عرفة ومزدلفة",          "daleel":"حديث: صلوا كما رأيتموني أصلي","source":"الهداية ج1 ص85",      "confidence":0.95},
            "maliki":  {"hukm":"يجوز للمسافر والمريض وفي المطر",              "daleel":"حديث معاذ في الجمع",          "source":"المدونة ج1 ص102",     "confidence":0.92},
            "shafii":  {"hukm":"يجوز في السفر والمرض والمطر والخوف",          "daleel":"حديث ابن عباس في مسلم",       "source":"المجموع ج4 ص372",     "confidence":0.93},
            "hanbali": {"hukm":"يجوز بأسباب متعددة منها السفر والشغل الشديد","daleel":"حديث ابن عباس: جمع من غير خوف","source":"المغني ج2 ص124",     "confidence":0.90},
        },
        "khilaf_type":"خلاف حقيقي",
        "rajih":"الجواز في السفر والمرض وهو قول الجمهور",
        "ijmaa":False,
        "asbaab_khilaf":["اختلاف في تأويل الأحاديث","تعارض ظاهر بين النصوص"]
    },
    "M002": {
        "title": "نصاب زكاة الذهب",
        "category": "عبادات", "subcategory": "الزكاة",
        "keywords": ["زكاة","ذهب","نصاب","مقدار","عشرون","مثقال"],
        "madhabs": {
            "hanafi":  {"hukm":"عشرون مثقالاً (85 غراماً تقريباً)","daleel":"حديث علي رضي الله عنه","source":"بدائع الصنائع ج2 ص95","confidence":0.98},
            "maliki":  {"hukm":"عشرون مثقالاً",                    "daleel":"حديث علي والإجماع",    "source":"الكافي لابن عبد البر","confidence":0.98},
            "shafii":  {"hukm":"عشرون مثقالاً",                    "daleel":"الإجماع",              "source":"الأم للشافعي ج2",     "confidence":0.99},
            "hanbali": {"hukm":"عشرون مثقالاً",                    "daleel":"الإجماع والأثر",       "source":"المغني ج3 ص6",        "confidence":0.99},
        },
        "khilaf_type":"إجماع", "rajih":"عشرون مثقالاً (85 غراماً)", "ijmaa":True, "asbaab_khilaf":[]
    },
    "M003": {
        "title": "حكم بيع الأسهم في البورصة",
        "category": "قضايا معاصرة", "subcategory": "المعاملات المالية",
        "keywords": ["أسهم","بورصة","بيع","شراء","سهم","شركة","استثمار"],
        "madhabs": {
            "hanafi":  {"hukm":"يجوز إذا كانت أصول الشركة حلالاً وخالية من الربا","daleel":"القياس على بيع الحصص",      "source":"مجمع الفقه الإسلامي ق7","confidence":0.82},
            "maliki":  {"hukm":"يجوز بشروط منها طهارة نشاط الشركة",             "daleel":"قاعدة: الأصل في المعاملات الإباحة","source":"مجلة مجمع الفقه ع7",   "confidence":0.80},
            "shafii":  {"hukm":"يجوز في شركات النشاط الحلال",                   "daleel":"الإذن الشرعي بالمشاركة",    "source":"قرار مجمع رقم 63",      "confidence":0.81},
            "hanbali": {"hukm":"يجوز بشرط أن لا يزيد الدين على ثلث الأصول",     "daleel":"شرط الخلو من الربا",        "source":"فتاوى ابن عثيمين ج18",   "confidence":0.79},
        },
        "khilaf_type":"خلاف نسبي",
        "rajih":"الجواز بشروط — قرار مجمع الفقه الإسلامي",
        "ijmaa":False,
        "asbaab_khilaf":["مسألة مستحدثة","اختلاف في تطبيق القواعد على الواقع"]
    }
}


# ==========================================
# الاختبار الشامل
# ==========================================

if __name__ == "__main__":
    engine = FiqhInferenceEngine(MASAIL_DB)

    test_questions = [
        ("هل يجوز الجمع بين المغرب والعشاء في السفر؟",  None),
        ("ما هو نصاب الزكاة على الذهب؟",                 None),
        ("ما حكم شراء الأسهم في شركات البورصة؟",         "shafii"),
    ]

    for question, madhab in test_questions:
        print(f"\n{'▶'*3} السؤال: {question}")
        if madhab:
            print(f"    (مذهب محدد: {madhab})")
        response = engine.process(question, madhab_filter=madhab)
        if response:
            response.display()
        else:
            print("  ⚠️  لم يُعثر على إجابة في قاعدة البيانات")
