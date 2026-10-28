"""Offline Chinese category labels derived from asset names; no file mutations."""
import re

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
    ('Marble','大理石',r'marble|大理石'),
    ('Climber','藤蔓',r'vines?|climber|藤蔓'),
    ('Tree','树皮',r'bark|tree|树皮'),
    ('Leaf','落叶',r'leaves|leaf|落叶|叶片'),
    ('Grass','草地',r'grass|weed|草'),
    ('Tiles','瓷砖',r'tiles?|瓷砖'),
    ('Concrete','混凝土',r'concrete|cement|混凝土|水泥'),
    ('Asphalt','沥青',r'asphalt|沥青'),
    ('Brick','砖墙',r'brick|砖墙'),
    ('Wood','木材',r'wood|timber|木'),
    ('Metal','金属',r'metal|steel|iron|copper|金属|钢|铁|铜'),
    ('Rock','岩石',r'rocks?|岩石'),
    ('Stone','石材',r'stone|石材'),
    ('Fabric','织物',r'fabric|cloth|leather|织物|布料|皮革'),
    ('Soil','土壤',r'soil|mud|土壤|泥'),
    ('Sand','沙地',r'sand|沙'),
    ('Moss','苔藓',r'moss|苔藓'),
    ('Paper','纸张',r'paper|纸'),
    ('Wall','墙面',r'wall|墙'),
    ('Road','道路',r'road|道路'),
    ('Plaster','灰泥',r'plaster|灰泥'),
    ('Plants','植物',r'plants?|植物'),
]
LABELS={key:label for key,label,_ in RULES}

def asset_group(asset):
    if asset.get('kind')=='decal':return 'decal'
    if asset.get('kind')=='normal' or asset.get('normalOnly'):return 'normal'
    return 'material'

def automatic_category(asset):
    # Native exports deliberately enter Uncategorized until the user sorts them.
    if asset.get('kind')=='blend':return asset['category']
    name=str(asset.get('name','')).lower()
    for key,_,pattern in RULES:
        # English word boundaries prevent e.g. "sand" matching "sandal".
        for term in pattern.split('|'):
            if re.search(r'(?<![a-z])(?:'+term+r')(?![a-z])' if term.isascii() else term,name):return key
    fallback=asset.get('category','Uncategorized')
    return 'Uncategorized' if fallback in {'Decal','NormalOnly','Other','Misc'} else fallback
