"""
====================================================
  نظام القواعد الفقهية — Rules Engine
  يطبّق القواعد الأصولية على المسائل
====================================================
"""

# ===== القواعد الفقهية الكبرى =====
FIQH_RULES = [
    {
        "id": "R01",
        "qaida": "الأمور بمقاصدها",
        "trigger_keywords": ["نية","قصد","هدف","غرض"],
        "application": "يُحكم بناءً على النية والقصد من الفعل",
        "examples": ["النية في العبادات", "قصد الاحتيال في العقود"]
    },
    {
        "id": "R02",
        "qaida": "الضرورات تبيح المحظورات",
        "trigger_keywords": ["اضطرار","ضرورة","خوف","مرض","شدة","حاجة ماسة"],
        "application": "يُباح المحرم عند الضرورة بقدرها",
        "examples": ["أكل الميتة عند الجوع الشديد", "التداوي بالمحرم"]
    },
    {
        "id": "R03",
        "qaida": "الأصل في الأشياء الإباحة",
        "trigger_keywords": ["حكم","مباح","جائز","أصل","جديد","مستحدث"],
        "application": "ما لا دليل على تحريمه فهو مباح",
        "examples": ["المعاملات الجديدة", "الأطعمة المستحدثة"]
    },
    {
        "id": "R04",
        "qaida": "المشقة تجلب التيسير",
        "trigger_keywords": ["مشقة","صعوبة","عسر","سفر","مرض","كبر"],
        "application": "يُخفف الحكم عند المشقة كالقصر في السفر",
        "examples": ["الجمع والقصر في السفر", "إفطار المريض"]
    },
    {
        "id": "R05",
        "qaida": "لا ضرر ولا ضرار",
        "trigger_keywords": ["ضرر","أذى","ضرار","إفساد","إتلاف"],
        "application": "يُمنع كل ما فيه ضرر على النفس أو الغير",
        "examples": ["منع الغش في التجارة", "منع البيع الذي يضر المشتري"]
    },
]


class RulesEngine:
    """يطبّق القواعد الفقهية على السؤال ويضيف تحليلاً أصولياً"""

    def find_applicable_rules(self, keywords: list) -> list:
        """يجد القواعد المنطبقة على الكلمات المفتاحية"""
        applicable = []
        for rule in FIQH_RULES:
            for kw in keywords:
                if any(kw in t or t in kw
                       for t in rule["trigger_keywords"]):
                    applicable.append(rule)
                    break
        return applicable

    def adjust_confidence(self, base_conf: float,
                          rules: list, ijmaa: bool) -> float:
        """يعدّل درجة الثقة بناءً على القواعد والإجماع"""
        if ijmaa:
            return min(base_conf * 1.15, 0.99)
        if rules:
            return min(base_conf * (1 + 0.05 * len(rules)), 0.95)
        return base_conf

    def get_takyeef(self, category: str, khilaf_type: str) -> str:
        """التكييف الفقهي: تصنيف نوع المسألة"""
        takyeef_map = {
            ("عبادات",        "إجماع"):       "مسألة قطعية متفق عليها",
            ("عبادات",        "خلاف حقيقي"):  "مسألة ظنية فيها خلاف معتبر",
            ("معاملات",       "خلاف نسبي"):   "مسألة اجتهادية في المعاملات",
            ("قضايا معاصرة", "خلاف نسبي"):   "نازلة معاصرة تحتاج اجتهاداً جماعياً",
        }
        return takyeef_map.get((category, khilaf_type),
               "مسألة فقهية تحتاج مزيداً من البحث")


# ==========================================
# اختبار نظام القواعد
# ==========================================

if __name__ == "__main__":
    engine = RulesEngine()

    print("═" * 52)
    print("  اختبار نظام القواعد الفقهية")
    print("═" * 52)

    test_cases = [
        (["مرض","سفر","مشقة"],   "عبادات",       "خلاف حقيقي", False),
        (["ضرورة","اضطرار"],     "معاملات",      "خلاف نسبي",  False),
        (["زكاة","ذهب","نصاب"],  "عبادات",       "إجماع",      True),
        (["بنك","فائدة","ربا"],  "قضايا معاصرة","خلاف نسبي",  False),
    ]

    for keywords, cat, khilaf, ijmaa in test_cases:
        rules = engine.find_applicable_rules(keywords)
        conf  = engine.adjust_confidence(0.65, rules, ijmaa)
        taky  = engine.get_takyeef(cat, khilaf)

        print(f"\n🔑 الكلمات: {' · '.join(keywords)}")
        print(f"   التكييف : {taky}")
        print(f"   الثقة   : {conf*100:.0f}%")
        if rules:
            print(f"   القواعد المنطبقة:")
            for r in rules:
                print(f"     • {r['qaida']} ← {r['application']}")
