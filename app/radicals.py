"""Significados en español de los radicales Kangxi (los 214 tradicionales).

Es una referencia fija y bien conocida (no depende de la IA ni de ningún
archivo externo): se usa solo para mostrar al estudiante qué significa un
radical cuando aparece en "radicals" de un carácter guardado, como ayuda de
memorización. Puede no cubrir alguna variante rara; si un radical no está
aquí, la app simplemente lo muestra sin significado.
"""

RADICAL_MEANINGS: dict[str, str] = {
    "一": "uno, línea horizontal", "丨": "línea vertical", "丶": "punto", "丿": "trazo hacia la izquierda",
    "乙": "segundo (ciclo), doblez", "亅": "gancho",
    "二": "dos", "亠": "tapa", "人": "persona", "亻": "persona (variante)", "儿": "piernas, hijo",
    "入": "entrar", "八": "ocho, dividir", "冂": "límite, frontera", "冖": "cubierta, tapa",
    "冫": "hielo", "几": "mesa baja, taburete", "凵": "recipiente abierto", "刀": "cuchillo",
    "刂": "cuchillo (variante)", "力": "fuerza, poder", "勹": "envolver", "匕": "cuchara, daga",
    "匚": "caja, contenedor", "匸": "ocultar", "十": "diez", "卜": "adivinación",
    "卩": "sello, persona arrodillada", "厂": "acantilado, fábrica", "厶": "privado, personal",
    "又": "mano derecha, de nuevo",
    "口": "boca", "囗": "cercado, recinto", "土": "tierra", "士": "erudito, caballero",
    "夂": "ir despacio", "夊": "caminar arrastrando", "夕": "atardecer, noche", "大": "grande",
    "女": "mujer", "子": "niño, hijo", "宀": "techo, tejado", "寸": "pulgada, mano",
    "小": "pequeño", "尢": "cojo", "尸": "cadáver, cuerpo", "屮": "brote",
    "山": "montaña", "川": "río", "工": "trabajo", "己": "uno mismo",
    "巾": "tela, toalla", "干": "escudo, seco", "幺": "pequeño, joven", "广": "techo, refugio amplio",
    "廴": "caminar largo", "廾": "dos manos juntas", "弋": "flecha con cuerda", "弓": "arco",
    "彐": "hocico de cerdo", "彡": "pelo, plumas, adorno", "彳": "paso corto, caminar",
    "心": "corazón, mente", "忄": "corazón (variante)", "戈": "lanza, arma", "户": "puerta, hogar",
    "手": "mano", "扌": "mano (variante)", "支": "rama, sostener", "攴": "golpear ligero",
    "攵": "golpear ligero (variante)", "文": "escritura, cultura", "斗": "medida de grano, pelea",
    "斤": "hacha", "方": "cuadrado, dirección", "无": "no, sin", "日": "sol, día",
    "曰": "decir", "月": "luna, carne", "木": "árbol, madera", "欠": "carecer, bostezar",
    "止": "detener, pie", "歹": "muerte, mal", "殳": "arma, lanza corta", "毋": "no",
    "比": "comparar", "毛": "pelo, vello", "氏": "clan, apellido", "气": "vapor, aire",
    "水": "agua", "氵": "agua (variante)", "火": "fuego", "灬": "fuego (variante)",
    "爪": "garra", "爫": "garra (variante)", "父": "padre", "爻": "trigramas, cruce",
    "爿": "madera partida, cama", "片": "rebanada, trozo plano", "牙": "diente, colmillo",
    "牛": "buey, vaca", "牜": "buey (variante)", "犬": "perro", "犭": "perro (variante)",
    "玄": "profundo, misterioso", "玉": "jade", "王": "jade/rey (variante)", "瓜": "melón",
    "瓦": "teja, cerámica", "甘": "dulce", "生": "nacer, vida", "用": "usar",
    "田": "campo de cultivo", "疋": "pieza de tela, pie", "疒": "enfermedad", "癶": "pasos, caminar",
    "白": "blanco", "皮": "piel", "皿": "recipiente, plato", "目": "ojo",
    "矛": "lanza", "矢": "flecha", "石": "piedra", "示": "espíritu, mostrar",
    "礻": "espíritu (variante)", "禸": "huella de animal", "禾": "grano, cereal", "穴": "cueva, agujero",
    "立": "estar de pie", "竹": "bambú", "⺮": "bambú (variante)", "米": "arroz",
    "糸": "seda, hilo", "纟": "seda (variante)", "缶": "vasija de barro", "网": "red",
    "罒": "red (variante)", "羊": "oveja", "羽": "pluma", "老": "viejo",
    "耂": "viejo (variante)", "而": "y, pero", "耒": "arado", "耳": "oreja",
    "聿": "pincel", "肉": "carne", "臣": "ministro, funcionario", "自": "uno mismo, nariz",
    "至": "llegar", "臼": "mortero", "舌": "lengua", "舛": "oponerse, error",
    "舟": "barco", "艮": "detenerse, terco", "色": "color", "艸": "hierba",
    "艹": "hierba (variante)", "虍": "tigre", "虫": "insecto, bicho", "血": "sangre",
    "行": "caminar, ir", "衣": "ropa", "衤": "ropa (variante)", "襾": "cubrir",
    "见": "ver", "角": "cuerno, ángulo", "言": "palabra, hablar", "讠": "palabra (variante)",
    "谷": "valle", "豆": "frijol, haba", "豕": "cerdo", "豸": "fiera, reptil",
    "贝": "concha, dinero", "赤": "rojo", "走": "caminar, correr", "足": "pie",
    "⻊": "pie (variante)", "身": "cuerpo", "车": "carro, vehículo", "辛": "picante, sufrimiento",
    "辰": "momento, hora temprana", "辵": "caminar, avanzar", "辶": "caminar (variante)",
    "邑": "ciudad, poblado", "酉": "vino, alcohol", "釆": "distinguir, separar", "里": "pueblo, medida de distancia",
    "金": "metal, oro", "钅": "metal (variante)", "长": "largo", "门": "puerta",
    "阜": "colina, montículo", "阝": "colina/ciudad (variante)", "隶": "esclavo, siervo", "隹": "pájaro de cola corta",
    "雨": "lluvia", "青": "azul, verde", "非": "no, incorrecto", "面": "cara, rostro",
    "革": "cuero, piel curtida", "韦": "cuero curtido", "韭": "cebollino", "音": "sonido",
    "页": "página, cabeza", "风": "viento", "飞": "volar", "食": "comida, comer",
    "饣": "comida (variante)", "首": "cabeza, primero", "香": "fragante", "马": "caballo",
    "骨": "hueso", "高": "alto", "髟": "cabello (largo)", "鬥": "pelear",
    "鬯": "vino ritual", "鬲": "caldero", "鬼": "fantasma", "鱼": "pez",
    "鸟": "pájaro", "卤": "sal, salmuera", "鹿": "ciervo", "麦": "trigo",
    "麻": "cáñamo", "黄": "amarillo", "黍": "mijo", "黑": "negro",
    "黹": "bordado", "黾": "rana, sapo", "鼎": "trípode, caldero", "鼓": "tambor",
    "鼠": "rata, ratón", "鼻": "nariz", "齐": "parejo, igual", "齿": "diente",
    "龙": "dragón", "龟": "tortuga", "龠": "flauta",
}


def radical_meaning(radical: str) -> str:
    return RADICAL_MEANINGS.get(radical, "")
