# cubest

[English](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [हिन्दी](README.hi.md) · **العربية** · [বাংলা](README.bn.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [日本語](README.ja.md) · [ਪੰਜਾਬੀ](README.pa.md)

> **رموز أقل بمعدل 7–22× لكل فحص مستودع لوكلاء الذكاء الاصطناعي.**
> مُجمِّع OLAP بتمرير واحد يطوي أي تدفق نصي — كود، سجلات، CSV، JSONL،
> XML، HTML، مصنوعات SDD — إلى مكعّب متعدد الأبعاد مضغوط. مصمَّم من أجل
> **Claude Code وCursor وCodex وAider وWindsurf وCline وContinue.dev**
> وأي وكيل ذكاء اصطناعي يدفع لكل رمز إدخال.

<p align="left">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg">
  <img src="https://img.shields.io/badge/deps-stdlib%20only-green.svg">
  <img src="https://img.shields.io/badge/tests-57%20passing-brightgreen.svg">
</p>

## 🧠 لماذا يهم هذا وكيل الذكاء الاصطناعي

مُقاس على 7 سيناريوهات حقيقية (انظر [`examples/`](examples/)):

| # | السيناريو                                    | Naive tokens | Cubest tokens | النسبة    |
|---|----------------------------------------------|:------------:|:-------------:|:---------:|
| 1 | تحقيق nginx 5xx (سجل من 5000 سطر)            | 3,590        | 158           | **22.7×** |
| 2 | تهيئة مستودع جديد (40 ملفًا)                 | 1,256        | 175           | 7.2×      |
| 3 | خريطة تأثير MR من `git diff`                 | 280          | 16            | **17.5×** |
| 4 | تجميع CSV صغير (300 صف)                      | 280          | 368           | 0.8× ❌   |
| 5 | تدقيق SEO لعشر صفحات HTML                    | 382          | 49            | 7.8×      |
| 6 | تدقيق استخدام القرص (300 ملف)                | 338          | 68            | 5.0×      |
| 7 | تجميع فئات RSS (3×30 عنصرًا)                 | 1,692        | 265           | 6.4×      |
|   | **الوسيط (median)**                          |              |               | **7.2×**  |

يتفوّق cubest على **التدفقات الكبيرة والبيانات الهرمية**. في الجداول
الصغيرة جدًا (CSV من 300 صف) يكون خط أنابيب `awk` البسيط مضغوطًا بالفعل
وقد يخسر cubest. أما في السيناريوهات الأساسية — السجلات وأشجار الكود
وزحف sitemap — فإن الرموز التي تسقط في سياق الوكيل تقلّ بمعدل 5–25×.

## 🚀 التثبيت

```bash
# تنزيل بسيط (بلا اعتماديات لملفات JSON)
curl -O https://raw.githubusercontent.com/BaryshevS/cubest/main/cubest.py
python3 cubest.py --profile file_tree .

# عبر pip (سيُنشر على PyPI قريبًا)
pip install cubest
cubest --profile file_tree .

# عبر مغلِّف npm
npx cubest --profile file_tree .
```

## ⚡ بداية سريعة

```bash
# خريطة مستودع غير مألوف (30 سطرًا بدلًا من 3000)
cubest --profile file_tree .

# سجل nginx.gz — أعلى عناوين URL × الحالة × زمن الاستجابة p95
cubest --profile nginx_access /var/log/nginx/access.log.gz

# عدّ سطور الكود لكل لغة
cubest --profile loc_counter .

# CSV → OLAP → لوحة ECharts تفاعلية (ملف HTML وحيد)
cubest -p '{
  "dimensions": ["campaign", "device"],
  "measures": [{"name":"impressions","type":"sum","field":"impressions"}],
  "extract": [{"type":"preset","preset":"csv"}],
  "output": {"format":"echarts","chart_type":"sankey"}
}' report.csv > dashboard.html
```

## 📊 صيغ الإخراج

13 صيغة: `tree`، `flat`، `compact`، `csv`، `md_table`، `yaml`، `json`،
`xml`، `dot`، `mermaid`، `plantuml`، `drawio`، `echarts`.

31 ملفًّا تعريفيًّا مدمجًا — للكود والسجلات وCSV وSEO وK8s وOpenAPI وSDD.
القائمة الكاملة في [README الإنجليزي](README.md#-what-you-get).

## 📜 الترخيص

Apache License 2.0 — انظر [LICENSE](LICENSE) و[NOTICE](NOTICE).

**اشتراط النَّسب (Apache 2.0 §4d):** إذا أعدت توزيع cubest، يجب
إدراج ملف NOTICE مع الحفاظ على رابط المصدر الأصلي:

> https://github.com/BaryshevS/cubest

## 💖 الدعم

إذا كان cubest يوفّر عليك رموزًا في تدفقات عمل الوكلاء اليومية أو يُقصّر
حادثة تشغيلية، ففكّر في رعاية المشروع — يذهب التمويل مباشرة إلى بنود
خارطة الطريق (t-digest، بث CSV، مقاطع للوكلاء) والبنية التحتية:

- **GitHub Sponsors** → https://github.com/sponsors/BaryshevS
- **Open Collective** → https://opencollective.com/baryshevsv

حتى 3 دولارات شهريًا تُبقي المشروع حيًّا. يحصل الرعاة على أولوية في فرز
issues ويُذكرون في ملاحظات الإصدار.

## ⭐ ضع نجمة على المستودع

إذا وفّر عليك cubest جزءًا من ميزانية الذكاء الاصطناعي أو قصّر حادثة SRE
بساعة — النجمة تساعد الآخرين على العثور عليه. هذا كل الطلب.

<a href="https://github.com/BaryshevS/cubest/stargazers">
  <img src="https://img.shields.io/github/stars/BaryshevS/cubest?style=social" alt="Star">
</a>
