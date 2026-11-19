"""Offline Chinese category labels derived from asset names; no file mutations."""
import re
from hdr_categories import classify_hdr

RULES = [
    ('DrainCover','井盖',r'drain.?cover|manhole|井盖'),
    ('Drain','排水口',r'drain|排水口'),
    ('PoleBase','杆座',r'pole.?base|杆座'),
    ('Crack','裂缝',r'cracks?|裂缝|裂纹'),
    ('Pothole','坑洞',r'pothole|坑洞'),
    ('Stain','污渍',r'stains?|污渍|油污'),
    ('Rust','锈迹',r'rust|锈'),
    ('Graffiti','涂鸦',r'graffiti|涂鸦'),
    ('Scratch','划痕',r'scratches|scratch|划痕'),
    ('Water','水纹',r'water|waves?|ripples?|水纹|水波'),
    ('Snow','冰雪',r'snow|snowmobile|glacier|ice|冰雪|积雪|冰面'),
    ('Foam','泡沫',r'foam|泡沫'),
    ('Plastic','塑料',r'plastic|polystyrene|polypropylene|polyvinylpyrrolidone|pvc|garbage bag|塑料'),
    ('Rubber','橡胶',r'rubber|橡胶'),
    ('Glass','玻璃',r'glass|玻璃'),
    ('Artwork','装饰画',r'paintings?|panting|装饰画'),
    ('Food','食物',r'food|noodles?|pizza|bacon|banana|chickpeas?|beans?|peanuts?|biscuits?|bread|crispbread|meat|steak|seeds?|corn|cake|chocolate|cheese|oatmeal|pomegranate|rice|食物'),
    ('Animal','动物表面',r'animal|creature|feathers?|wings?|skin|flesh|pelt|butterflies|动物|羽毛'),
    ('Marble','大理石',r'marble|大理石'),
    ('Climber','藤蔓',r'vines?|climber|藤蔓'),
    ('Tree','树皮',r'bark|tree|树皮'),
    ('Leaf','落叶',r'leaves|leaf|落叶|叶片'),
    ('Grass','草地',r'grass|grassy|turf|weed|草'),
    ('Gravel','碎石',r'gravel|gravelly|pebbles?|grit|碎石|砾石'),
    ('Tiles','瓷砖',r'tiles?|mosaic|瓷砖'),
    ('Concrete','混凝土',r'concrete|cement|混凝土|水泥'),
    ('Asphalt','沥青',r'asphalt|沥青'),
    ('Brick','砖墙',r'bricks?|砖墙'),
    ('Wood','木材',r'wood|wooden|timber|veneer|parquets?|planks?|plywood|chipboard|mdf|floorboards?|木'),
    ('Metal','金属',r'metal|steel|iron|copper|金属|钢|铁|铜'),
    ('Rock','岩石',r'rocks?|rocky|cliff|岩石'),
    ('Stone','石材',r'stones?|cobblestones?|flagstones?|granite|slate|terrazzo|石材'),
    ('Fabric','织物',r'fabric|cloth|leather|cotton|denim|tarp|rope|tatami|straw blind|织物|布料|皮革'),
    ('Soil','土壤',r'soil|mud|dirt|mulch|土壤|泥'),
    ('Sand','沙地',r'sand|sandy|沙'),
    ('Moss','苔藓',r'moss|mossy|lichen|lichened|苔藓'),
    ('Paper','纸张',r'paper|cardboard|wallpaper|纸'),
    ('Cork','软木',r'cork|软木'),
    ('Debris','碎屑',r'debris|rubble|scrap|ash pile|coal ash|powdered ash|碎屑'),
    ('Ground','地表',r'ground|forest floor|forest path|lakebed|riverbed|terrain|地表'),
    ('Wall','墙面',r'wall|墙'),
    ('Road','道路',r'road|道路'),
    ('Plaster','灰泥',r'plaster|stucco|drywall|灰泥'),
    ('Plants','植物',r'plants?|seaweed|植物'),
]
LABELS={key:label for key,label,_ in RULES}

def asset_group(asset):
    if asset.get('kind')=='hdr':return 'hdr'
    if asset.get('kind')=='decal':return 'decal'
    if asset.get('kind')=='normal' or asset.get('normalOnly'):return 'normal'
    if asset.get('kind')=='image':return 'texture'
    return 'material'

def automatic_category(asset):
    if asset.get('kind')=='hdr':return classify_hdr(asset.get('name',''))
    # Native exports deliberately enter Uncategorized until the user sorts them.
    if asset.get('kind')=='blend':return asset['category']
    def match(text):
        for key,_,pattern in RULES:
            # English word boundaries prevent e.g. "sand" matching "sandal".
            for term in pattern.split('|'):
                if re.search(r'(?<![a-z])(?:'+term+r')(?![a-z])' if term.isascii() else term,text):return key
    name=str(asset.get('name','')).lower()
    category=match(name)
    if category:return category
    if asset_group(asset)=='texture':return 'Other'
    # Prefer structured package metadata over generic descriptive tags; use
    # folder names for older technical exports with missing display names.
    for value in asset.get('categories',[]):
        category=match(value.lower()) if isinstance(value,str) else None
        if category:return category
    for values in ([str(asset.get('folder','')).replace('_',' ')], asset.get('tags',[])):
        category=match(' '.join(v for v in values if isinstance(v,str)).lower())
        if category:return category
    fallback=asset.get('category','Uncategorized')
    return 'Uncategorized' if fallback in {'Decal','NormalOnly','Other','Misc'} else fallback
