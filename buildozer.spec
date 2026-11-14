# =============================================================================
# Buildozer Specification File for Google Play Store (.aab Release)
# Save this file strictly as: buildozer.spec (in the same folder as main.py)
# Docs: https://kivy.org/doc/stable/guide/packaging-android.html
# PyPI: https://pypi.org/project/buildozer/
# Target API Policy: https://support.google.com/googleplay/android-developer/answer/11926878?hl=en
# =============================================================================

[app]

title = Magic Kaleido-Pop Studio
package.name = kaleidopop
package.domain = org.abdullahstudios
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# Core Python + Kivy dependencies
requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 1
android.presplash_color = #0D0D1A

# =============================================================================
# Android & Google Play Store Specific Settings
# =============================================================================

# Target Android API (35/36 supported by Android SDK)
android.api = 35
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

# Release & Debug output formats
android.release_artifact = aab
android.debug_artifact = apk

# Zero permissions required (Families Policy compliant)
android.permissions =
android.allow_backup = True

# Use master branch of python-for-android for latest API 35/36 and Gradle support
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
