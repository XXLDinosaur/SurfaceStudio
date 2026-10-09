"""Enable the copied add-on using the user's existing Blender preferences.
Run with normal --background (never --factory-startup).
"""
from pathlib import Path
import json
import addon_utils
import bpy

root=Path(__file__).resolve().parent
before=set(bpy.context.preferences.addons.keys())
module=addon_utils.enable('surface_studio_bridge',default_set=True,persistent=True)
if module is None or not hasattr(bpy.types,'SURFACESTUDIO_PT_library'):
    raise RuntimeError('Surface Studio add-on did not register; preferences were not saved')
addon=bpy.context.preferences.addons.get('surface_studio_bridge')
addon.preferences.executable_path=str(root/'Surface Studio.exe')
after=set(bpy.context.preferences.addons.keys())
if not before.issubset(after):
    raise RuntimeError('Existing add-on preferences changed; preferences were not saved')
bpy.ops.wm.save_userpref()
report={'version':bpy.app.version_string,'enabled':True,'existingAddonsPreserved':len(before),'exe':str(root/'Surface Studio.exe')}
(root/'data'/'blender-install-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SURFACE_ADDON_INSTALLED '+json.dumps(report,ensure_ascii=False),flush=True)
