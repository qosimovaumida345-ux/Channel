[app]
title = Jarvis AI
package.name = jarvisai
package.domain = org.sdzabu

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy

orientation = portrait

osx.python_version = 3
osx.kivy_version = 1.9.1

fullscreen = 0
android.permissions = INTERNET, SYSTEM_ALERT_WINDOW

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1
