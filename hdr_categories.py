"""Offline scene categories for HDR names, shared by scans and live categorization."""
import re
import unicodedata

LABELS = {
    'HDRStudio': '摄影棚',
    'HDRSky': '天空',
    'HDRInterior': '室内',
    'HDRStreet': '街道与城市',
    'HDRForest': '森林与公园',
    'HDRCoast': '海边与水域',
    'HDRMountain': '山地与岩石',
    'HDRField': '草地与田野',
    'HDRIndustrial': '工业场景',
    'HDRDesert': '沙漠',
    'HDRSnow': '雪地',
    'HDROther': '其他环境',
}

# Ordered rules: strong context wins; time/weather only classifies otherwise
# unidentified names. Boundaries keep "park" out of "parking" and "road" out
# of "roadmap". Separators and case are normalized before matching.
_RULES = [
    ('HDRStudio', r'studios?|photostudio|softbox|light tent|cyclorama|摄影棚|影棚|柔光箱'),
    ('HDRSky', r'puresky|pure sky|sky dome|skydome|纯天空'),
    ('HDRInterior', r'interiors?|indoors?|室内'),
    ('HDRIndustrial', r'industrial|hopper|waterworks|carpentry|autoshop|auto service|machine|missile|factory|factories|warehouses?|workshops?|hangars?|construction|loading dock|shipyards?|quarry|power plant|refinery|steelworks|工厂|工业|厂房|仓库|车间|矿场|工地'),
    ('HDRInterior', r'museums?|ballrooms?|shops?|stores?|malls?|theat(?:er|re)s?|suites?|pubs?|vaults?|manors?|dungeons?|rooms?|lounges?|halls?|attics?|cellars?|basements?|kitchens?|apartments?|offices?|restaurants?|cafes?|canteens?|garages?|chapels?|church|churches|cathedrals?|mosques?|temples?|libraries|library|cinemas?|galleries|gallery|corridors?|lobbies|lobby|staircases?|schools?|classrooms?|gym|supermarkets?|bakeries|bakery|bunkers?|tunnels?|houses?|cabins?|bathrooms?|bedrooms?|酒吧|客厅|卧室|厨房|房间|餐厅|办公室|教堂|走廊|室内大厅|地下室|车库'),
    ('HDRCoast', r'beaches|beach|coasts?|coastal|seaside|oceans?|sea|harbou?r|docks?|piers?|rivers?|riverside|lakes?|lakeside|waterfalls?|falls|ponds?|creeks?|brooks?|fountains?|moats?|shipwrecks?|canals?|reservoirs?|streams?|pools?|海边|海滩|海岸|湖泊|湖边|河流|河边|瀑布|码头|水域'),
    ('HDRForest', r'forests?|woodlands?|woods|jungles?|rainforest|arboretum|parks?|gardens?|groves?|orchards?|botanical|greenhouses?|森林|树林|公园|花园|竹林|果园'),
    ('HDRMountain', r'mountains?|hillsides?|hilltops?|hills?|canyons?|cliffs?|ridges?|valleys?|rocks?|rocky|caves?|alps|alpine|山地|山脉|山区|高山|峡谷|悬崖|岩石|山谷|洞穴'),
    ('HDRStreet', r'piazzas?|plazas?|balconies|balcony|pathways?|walkways?|stadiums?|towers?|castles?|airfields?|terminals?|streets?|roads?|alleys?|urban|city|cities|towns?|squares?|crossings?|intersections?|parking|courtyards?|sidewalks?|pavements?|bridges?|viaducts?|overpass|underpass|rooftops?|stations?|railway|railroad|街道|街景|城市|道路|广场|停车场|桥梁|天桥|屋顶|车站'),
    ('HDRField', r'golf|fields?|meadows?|grass|grassy|grasslands?|pastures?|farms?|farmland|rural|countryside|prairies|prairie|lawns?|wheat|hay|agricultural|草地|草原|田野|牧场|农场|农田|乡村'),
    ('HDRDesert', r'deserts?|dunes?|sandy|sand|荒漠|沙漠|沙丘'),
    ('HDRSnow', r'snow|snowy|winter|ice|icy|frozen|glaciers?|雪地|雪景|冬季|冰川|冰雪'),
    ('HDRSky', r'sky|clear|afternoon|storm|stormy|sunrise|sunset|dawn|dusk|clouds?|cloudy|overcast|noon|midday|night|stars?|starlit|sunny|misty|foggy|evening|morning|twilight|天空|日出|日落|黄昏|黎明|阴天|多云|晴空'),
]
RULES = [(category, re.compile(r'(?<![a-z])(?:'+pattern+r')(?![a-z])')) for category, pattern in _RULES]


def classify_hdr(name):
    name = unicodedata.normalize('NFKC', str(name or '')).casefold()
    name = re.sub(r'[_\W]+', ' ', name)
    for category, pattern in RULES:
        if pattern.search(name):
            return category
    return 'HDROther'
