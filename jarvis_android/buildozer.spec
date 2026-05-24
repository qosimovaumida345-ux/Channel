[app]
title = Jarvis AI
package.name = jarvisai
package.domain = org.sdzabu

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, SYSTEM_ALERT_WINDOW
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.accept_sdk_license = True
android.arch = arm64-v8a

# Use develop branch of p4a for Python 3.14 support
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
