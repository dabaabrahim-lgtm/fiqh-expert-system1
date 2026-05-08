"""
====================================================
  عمليات قاعدة البيانات — بدون اتصال فعلي
  (نموذج تعليمي يعمل بدون MongoDB مثبّت)
====================================================
"""
import json
from datetime import datetime

# محاكاة قاعدة البيانات في الذاكرة
class FiqhDatabase:
    def __init__(self):
        self.masail = {}
        self.sources = {}
        self.qawaid = {}
        print("✅ تم تهيئة قاعدة البيانات الفقهية (وضع التجريب)")

    # ===== إضافة مسألة =====
    def add_masala(self, masala: dict) -> str:
        mid = masala["_id"]
        self.masail[mid] = masala
        return mid

    # ===== البحث بالكلمات المفتاحية =====
    def search_by_keyword(self, keyword: str) -> list:
        results = []
        for m in self.masail.values():
            if keyword in m.get("keywords", []) or \
               keyword in m.get("title", "") or \
               keyword in m.get("subcategory", ""):
                results.append({
                    "id": m["_id"],
                    "title": m["title"],
                    "category": m["category"]
                })
        return results

    # ===== استرجاع مسألة بالمعرف =====
    def get_masala(self, mid: str) -> dict:
        return self.masail.get(mid, None)

    # ===== البحث حسب المذهب =====
    def get_by_madhab(self, madhab: str, hukm_contains: str = "") -> list:
        results = []
        for m in self.masail.values():
            madhab_data = m.get("madhabs", {}).get(madhab, {})
            if madhab_data:
                if not hukm_contains or hukm_contains in madhab_data.get("hukm",""):
                    results.append({
                        "masala": m["title"],
                        "hukm": madhab_data["hukm"],
                        "source": madhab_data["source"]
                    })
        return results

    # ===== مقارنة المذاهب في مسألة =====
    def compare_madhabs(self, mid: str) -> dict:
        m = self.get_masala(mid)
        if not m:
            return {"error": "المسألة غير موجودة"}
        comparison = {
            "title": m["title"],
            "madhabs": {}
        }
        for madhab, data in m.get("madhabs", {}).items():
            comparison["madhabs"][madhab] = {
                "الحكم": data["hukm"],
                "الدليل": data["daleel"],
                "المصدر": data["source"]
            }
        comparison["خلاصة"] = m.get("rajih", "")
        comparison["نوع الخلاف"] = m.get("khilaf_type", "")
        return comparison

    # ===== إحصاءات قاعدة البيانات =====
    def stats(self) -> dict:
        cats = {}
        for m in self.masail.values():
            c = m.get("category", "غير مصنف")
            cats[c] = cats.get(c, 0) + 1
        return {
            "إجمالي المسائل": len(self.masail),
            "التصنيفات": cats,
            "المصادر": len(self.sources),
            "القواعد الفقهية": len(self.qawaid)
        }


# ===== تشغيل تجريبي =====
db = FiqhDatabase()

# إضافة مسألة نموذجية
masala_salah = {
    "_id": "M001",
    "title": "حكم الجمع بين الصلاتين",
    "category": "عبادات",
    "subcategory": "الصلاة",
    "keywords": ["جمع", "صلاة", "سفر", "مرض", "تقديم", "تأخير"],
    "madhabs": {
        "hanafi":  {"hukm": "لا يجوز إلا للحاج في عرفة ومزدلفة", "daleel": "حديث: صلوا كما رأيتموني أصلي", "source": "الهداية ج1 ص85"},
        "maliki":  {"hukm": "يجوز للمسافر والمريض وفي المطر",    "daleel": "حديث معاذ في الجمع في السفر",     "source": "المدونة ج1 ص102"},
        "shafii":  {"hukm": "يجوز في السفر والمرض والمطر والخوف","daleel": "حديث ابن عباس في صحيح مسلم",      "source": "المجموع ج4 ص372"},
        "hanbali": {"hukm": "يجوز بأسباب متعددة منها الشغل",     "daleel": "حديث ابن عباس: جمع من غير خوف",  "source": "المغني ج2 ص124"},
    },
    "khilaf_type": "خلاف حقيقي",
    "rajih": "القول بالجواز في السفر والمرض وهو قول الجمهور",
    "ijmaa": False
}

masala_zakat = {
    "_id": "M002",
    "title": "نصاب زكاة الذهب",
    "category": "عبادات",
    "subcategory": "الزكاة",
    "keywords": ["زكاة", "ذهب", "نصاب", "مقدار"],
    "madhabs": {
        "hanafi":  {"hukm": "عشرون مثقالاً أو ما يعادلها", "daleel": "حديث علي رضي الله عنه", "source": "بدائع الصنائع ج2"},
        "maliki":  {"hukm": "عشرون مثقالاً",                "daleel": "حديث علي",               "source": "الكافي لابن عبد البر"},
        "shafii":  {"hukm": "عشرون مثقالاً",                "daleel": "الإجماع",                 "source": "الأم للشافعي ج2"},
        "hanbali": {"hukm": "عشرون مثقالاً",                "daleel": "الإجماع والأثر",          "source": "المغني ج3"},
    },
    "khilaf_type": "إجماع",
    "rajih": "عشرون مثقالاً (85 غراماً تقريباً)",
    "ijmaa": True
}

db.add_masala(masala_salah)
db.add_masala(masala_zakat)

print("\n" + "="*50)
print("   نتائج عمليات قاعدة البيانات")
print("="*50)

# بحث
print("\n🔍 البحث عن كلمة 'سفر':")
results = db.search_by_keyword("سفر")
for r in results:
    print(f"   • {r['title']} [{r['category']}]")

# مقارنة
print("\n⚖️  مقارنة المذاهب في مسألة الجمع:")
comp = db.compare_madhabs("M001")
print(f"   المسألة: {comp['title']}")
print(f"   نوع الخلاف: {comp['نوع الخلاف']}")
for m, d in comp["madhabs"].items():
    names = {"hanafi":"الحنفي","maliki":"المالكي","shafii":"الشافعي","hanbali":"الحنبلي"}
    print(f"   [{names[m]}] {d['الحكم']}")
print(f"   الراجح: {comp['خلاصة']}")

# إحصاءات
print("\n📊 إحصاءات قاعدة البيانات:")
stats = db.stats()
for k, v in stats.items():
    print(f"   {k}: {v}")

