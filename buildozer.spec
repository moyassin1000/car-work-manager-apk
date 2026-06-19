[app]

# اسم التطبيق الظاهر على الهاتف
title = Car Work Manager PRO

# اسم الحزمة - بدون مسافات
package.name = carworkmanagerpro
package.domain = org.aeo

# ملف البداية يجب أن يكون main.py
source.dir = .
source.include_exts = py,png,kv,json,ttf,db,csv
icon.filename = %(source.dir)s/icon.png
source.exclude_dirs = tests,bin,build,.git,.github,__pycache__

version = 0.6

# تثبيت KivyMD 1.2.0 لأن الكود يستخدم واجهات الأزرار القديمة MDRaisedButton/MDFlatButton
requirements = python3,kivy==2.3.0,kivymd==1.2.0,arabic-reshaper,python-bidi

# واجهة البرنامج مصممة بعرض كبير وبقائمة جانبية، لذلك Landscape أفضل للموبايل/التابلت
orientation = landscape
fullscreen = 0

# لا يحتاج صلاحيات خارجية لأن قاعدة البيانات داخل مجلد بيانات التطبيق
# android.permissions =

# إعدادات أندرويد
android.api = 35
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.build_tools_version = 35.0.0
android.archs = arm64-v8a, armeabi-v7a

# نسخة Debug تنتج APK جاهز للتثبيت بعد السماح بالتثبيت من مصادر غير معروفة
# للأجهزة الحديثة يكفي arm64-v8a، لكن تركت armeabi-v7a لدعم أوسع

[buildozer]
log_level = 2
warn_on_root = 1
