مشروع تحويل برنامج شغل العربية PRO v6 إلى APK
==============================================

المحتويات:
- main.py                 : ملف البرنامج الأصلي بعد إعادة تسميته للاسم المطلوب من Kivy/Buildozer
- buildozer.spec          : إعدادات بناء APK
- requirements.txt        : مكتبات التشغيل
- build_apk_ubuntu.sh     : سكريبت بناء سريع على Ubuntu/WSL
- .github/workflows       : بناء تلقائي عبر GitHub Actions

مهم:
لا أستطيع إخراج APK فعلي من داخل بيئة ChatGPT الحالية لأن أدوات Buildozer و Android SDK غير مثبتة هنا.
لكن هذا المجلد جاهز للبناء مباشرة على Linux/Ubuntu أو GitHub Actions.

طريقة البناء على Ubuntu أو WSL:
1) افتح Terminal داخل هذا المجلد.
2) نفذ الأوامر التالية:

sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev
./build_apk_ubuntu.sh

بعد انتهاء البناء ستجد ملف APK داخل مجلد:
bin/

طريقة البناء بدون جهاز قوي باستخدام GitHub Actions:
1) أنشئ Repository جديد على GitHub.
2) ارفع ملفات هذا المجلد كما هي.
3) افتح تبويب Actions.
4) شغل Workflow باسم Build Android APK.
5) بعد الانتهاء، حمّل Artifact باسم car-work-manager-pro-apk.

ملاحظات تثبيت على الهاتف:
- ملف debug APK قابل للتثبيت، لكن الهاتف قد يطلب تفعيل Install unknown apps.
- إذا ظهر تحذير Play Protect فهذا طبيعي مع تطبيق Debug غير منشور على Google Play.
- قاعدة البيانات يتم حفظها داخل بيانات التطبيق على Android.
- الواجهة مضبوطة Landscape لأن البرنامج فيه Sidebar وجدول واسع.
