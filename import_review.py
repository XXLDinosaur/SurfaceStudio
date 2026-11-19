"""Built-in, offline import checks. Never modify source textures."""
import re

POLICY_VERSION = 2
BOTANICAL = {'plant', 'plants', 'tree', 'trees', 'leaf', 'leaves', 'grass',
             'bush', 'bushes', 'flower', 'flowers', 'edible', 'moss', 'climber',
             'shrub', 'herb', 'fern', 'vine', 'weed', 'seaweed', 'lichen',
             'foliage', 'branch', 'branches', 'stem', 'stems', 'weeds', 'ferns',
             'shrubs', 'vines', 'twig', 'twigs', 'bark'}

def plant_atlas(meta, folder_name):
    categories = set(re.findall(r'[a-z]+', ' '.join(
        c for c in meta.get('categories', []) if isinstance(c, str)).lower()))
    identity = [str(meta.get('name', '')), folder_name]
    if categories & {'debris', 'ocean', 'scatter', 'nature'}:
        identity.extend(t for t in meta.get('tags', []) if isinstance(t, str))
    words = categories | set(re.findall(r'[a-z]+', ' '.join(identity).lower()))
    return bool('atlas' in categories and words & BOTANICAL)

def new_report():
    return dict(policyVersion=POLICY_VERSION, checkedFolders=0,
                includedPlantAtlases=0, excludedPlantAtlases=0,
                colorPreviews=0, excludedExamples=[])

def needs_review(index):
    report = index.get('importReview')
    return not isinstance(report, dict) or report.get('policyVersion') != POLICY_VERSION

def summary(report, items):
    classified = sum(a['category'] not in {'Uncategorized', 'Other'} for a in items)
    return {**(report or {}), 'classified': classified,
            'unclassified': len(items)-classified,
            'manualAssignments': sum(a['manualCategory'] for a in items)}
