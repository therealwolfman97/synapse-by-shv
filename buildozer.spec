[app]

title = Synapse by SHV
package.name = synapsebyshv
package.domain = org.sachith

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True

# Uncomment and set these if you have them
# icon.filename = assets/icon.png
# presplash.filename = assets/presplash.png

[buildozer]

log_level = 2
warn_on_root = 1
