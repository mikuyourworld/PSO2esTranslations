#!/usr/bin/env python3
# coding=utf8
import codecs
import json
import os
import regex
import shutil
import argparse

json_loc = os.path.join("..", "json")

parser = argparse.ArgumentParser(
    description = "Translates ticket item descriptions.")

#Switch for description on untranslated names
parser.add_argument("-a", dest = "all", action = "store_true",
                    help = ("Translate descriptions even for items "
                            "with no translated names."))

# Switch for language.
LANGS = {-1: "JP",
         0: "EN",
         1: "KO",
         2: "RU",
         3: "CN"}
# Add more later.
parser.add_argument("-l", type = int, dest = "lang", action = "store",
                    choices = [0, 1, 2, 3], default = 0, metavar = "N",
                    help = ("Set a language to translate into. "
                            "Available options are 0 (EN), 1 (KO), 2 (RU) and 3 (CN). "
                            "Defaults to EN."))

# Switch for retranslating all descriptions.
parser.add_argument("-r", dest = "redo", action = "store_true",
                    help = ("Force all ticket descriptions to be processed, "
                            "even if already translated."))

args = parser.parse_args()
TRANS_ALL, LANG, REDO_ALL = args.all, args.lang, args.redo

# Full width character transtable
chartable = [
    "".maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ　＝－＋／．＆（）：！",
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz =-+/.&():!"),

    "".maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ　＝－＋／．＆（）：！",
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz =-+/.&():!"),

    "".maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ　＝－＋／．＆（）：！",
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz =-+/.&():!"),

    "".maketrans("",
    "")]


# Translate layered wear

layered_wear_types = {"In": ["innerwear", "이너웨어", "внутреннюю одежду (In)", "內衣"],
                      "Ba": ["basewear", "베이스웨어", "верхнюю одежду (Ba)", "底衣"],
                      "Se": ["setwear", "세트 웨어", "комплектную одежду (Se)", "套服"],
                      "Fu": ["full setwear", "풀세트 웨어", "полн.компл.одежду (Fu)", "全身服裝"],
                      "Ou": ["outerwear", "아우터 웨어", "внешнюю одежду (Ou)", "外套"]}

# Old layered wear format. Must include itype and iname variables.
# JP text: 
    # 使用すると、新しい{itype}の\n
    # {iname}が選択可能。
layer_desc_formats = [("Unlocks the new {itype}\n"
                       "\"{iname}\"."),
                      ("사용하면 새로운 {itype}인\n"
                       "\"{iname}\"\n"
                       "의 사용이 가능해진다."),
                      ("Разблокирует новую\n"
                       "{itype}\n"
                       "\"{iname}\"."),
                      ("使用後，可選用新的{itype}\n"
                       "{iname}。")]

# JP text unavailable.
layer_sex_locks = {"n": ["", "", "", ""],
                   "m": ["\nOnly usable on male characters.",
                         " 남성만 가능.",
                         "\nТолько для мужских персонажей.",
                         "\n僅限男性使用。"],
                   "f": ["\nOnly usable on female characters.",
                         " 여성만 가능.",
                         "\nТолько для женских персонажей.",
                         "\n僅限女性使用。"]}

# New cosmetics format. Must include itype variable.
# JP text: 
    # 使用すると新しい{itype}が\n
    # 選択可能になる。
ndesc_n_formats = ["Unlocks {a}new {itype} for use.",
                 "사용하면 새로운 {itype}\n선택이 가능해집니다.",
                 "Разблок {itype}.",
                 "使用後可選用新的{itype}。"]

# JP text: 
    # 使用すると新しい{itype}が\n
    # 全キャラクターで選択可能になる。
ndesc_allcharacters_formats = ["A {itype} that unlocks for all\ncharacters on your account.",
                 "사용하면 새로운 {itype} 아이템을\n모든 캐릭터에 선택할 수 있게 됩니다.",
                 "",
                 "使用後所有角色均可選用新的{itype}。"]

# JP text: 
    # 使用すると新しい{itype}パターンが\n
    # 選択可能になる。
ndesc_pattern_formats = ["Unlocks {a}new {itype} for use.",
                 "사용하면 새로운 {itype}\n선택이 가능해집니다.",
                 "Разблок {itype}.",
                 "使用後可選用新的{itype}種類。"]

# JP text: 対応：
ntype_statements = ["Type: ",
                    "대응: ",
                    "Тип: ",
                    "適用於："]

# JP text:
    # ヒト型
    # キャスト
    # ヒト型/キャスト
    # タイプ1
    # タイプ2<c>
# No longer used.
ntype_locks = {"a": ["All", "KO_All", "Все", "CN_All"],
                "a1": ["Human/Cast Type 1", "인간형/캐스트타입1", "Человек/CAST (тип1)", "人類/機器人 類型1"],
                "a2": ["Human/Cast Type 2", "인간형/캐스트타입2", "Человек/CAST (тип2)", "人類/機器人 類型2"],
                "h1": ["Human Type 1", "인간형 타입1", "Человек (тип1)", "人類 類型1"],
                "h2": ["Human Type 2", "인간형 타입2", "Человек (тип2)", "人類 類型2"],
                "c1": ["Cast Type 1", "캐스트 타입1", "CAST (тип1)", "機器人 類型1"],
                "c2": ["Cast Type 2", "캐스트 타입2", "CAST (тип2)", "機器人 類型2"]}

# JP text:
    # ※着用時はインナーが非表示になります。
# No longer used.
layer_hide_inners = ["※Hides innerwear when worn.",
                     "※착용 시 이너웨어는 표시하지 않음.",
                     "※При экипировке скрывает In.",
                     "※穿著時不會顯示內衣。"]

# JP text:
    # ※一部[In]カラー同期
# No longer used.
layer_sync_inners = ["※Synchronizes with [In] color.",
                     "※일부 [In]컬러 동기화",
                     "※Цвета некоторых [In] синхр-ся.",
                     "※與一部分[In]同步顏色"]

# JP text: 
    # ※アクセサリー表示非対応
layer_hide_accessories = ["※Hides accessories when worn.",
                          "※악세서리 표시 불가",
                          "※Скрывает аксессуары.",
                          "※不適用於飾品的顯示"]

# JP text: 
    # ※カラー変更非対応
ncosmetic_color_locks = ["※Color cannot be changed",
                        "※컬러 변경 불가",
                        "",
                        "※不適用於顏色的變更"]

# JP text: 
    # ※『PSO2』ブロック非対応
ngs_only = ["※Not available in [PSO2] Blocks.",
             "※『PSO2』블록 비대응",
             "※Нельзя использовать в блоке PSO2",
             "※不適用於『PSO2』"]

# JP text: 
    # ※『PSO2』ではLv.100以上の\n
    # 　マグにのみ使用可能
mag_device_lv100 = [("※Must be used in PSO2 on a Mag\n"
                            "which has reached Lv.100 or above."),
                            ("※『PSO2』에선 Lv.100이상의\n"
                            "마그에서만 사용 가능"),
                            (""),
                            ("※在『PSO2』中僅可對\n"
                            "　Lv.100或以上的瑪古使用")]

# JP text: 
    # ※『NGS』でのみ使用可能
mag_device_ngs = ["※Only usable in NGS.",
                        "※『NGS』에서만 사용 가능",
                        "",
                        "※僅可在『NGS』中使用"]

def translate_layer_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]
    
    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Some items are locked to one sex or the other.
    sex = "n"
    if "女性のみ使用可能。" in item["jp_explain"]:
        sex = "f"
    elif "男性のみ使用可能。" in item["jp_explain"]:
        sex = "m"
    
    # Some items hide your innerwear (these are mostly swimsuits).
    hideinner = False
    if "着用時はインナーが非表示になります。" in item["jp_explain"]:
        hideinner = True
    
    # Translate the description.
    item["tr_explain"] = (layer_desc_formats[LANG] + "{sexlock}{hidepanties}").format(
        itype = layered_wear_types[item_name[-3:-1]][LANG] if item_name.endswith("]")
                # Exception for defaults since they don't have [In], [Ba] etc
                else layered_wear_types[file_name.split("_")[0][0:2]][LANG],
        iname = item_name,
        sexlock = layer_sex_locks[sex][LANG] if sex != "n" else "",
        hidepanties = "\n<yellow>" + layer_hide_inners[LANG] + "<c>" if hideinner == True else "")

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

def get_type_restrictions(item):
    types = "a"

    if "：ヒト型" in item["jp_explain"] and "/キャスト" not in item["jp_explain"]:
        types = "h"
    elif "：キャスト" in item["jp_explain"]:
        types = "c"
        
    if "タイプ1<c>" in item["jp_explain"]:
        types += "1"
    elif "タイプ2<c>" in item["jp_explain"]:
        types += "2"
    
    return types

def translate_nlayer_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]

    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Some basewears partially synchronise their colour with your innerwear
    syncinner = False
    if "一部[In]カラー同期" in item["jp_explain"]:
        syncinner = True
        
    # Some items are locked to one race and/or type.
    types = get_type_restrictions(item)

    # Some items hide your innerwear (these are mostly swimsuits).
    hideinner = False
    if "着用時はインナーが非表示になります。" in item["jp_explain"]:
        hideinner = True

    # Some setwears are incompatible with accessories
    hideaccess = False
    if "アクセサリー表示非対応" in item["jp_explain"]:
        hideaccess = True

    # Some ngs items cannot be recolored.
    ncolorlocked = False
    if "カラー変更非対応" in item["jp_explain"]:
        ncolorlocked = True

    # Translate the description.
    item["tr_explain"] = (ndesc_n_formats[LANG] + "{syncpanties}" + "{typelock}" + "{hidepanties}" + "{noaccessories}" + "{ncolorlock}").format(
        itype = layered_wear_types[item_name[-3:-1]][LANG] if item_name.endswith("]")
                # Exception for default layered wear since it doesn't have [In], [Ba] etc
                else layered_wear_types[file_name.split("_")[0][0:2]][LANG],
        # Ugly hack
        a = "a ",
        syncpanties = "\n<yellow>" + layer_sync_inners[LANG] + "<c>" if syncinner == True else "",
        typelock = "" if types == "a" else "\n<yellow>※{0}{1}<c>".format(ntype_statements[LANG], ntype_locks[types][LANG]),
        hidepanties = "\n<yellow>" + layer_hide_inners[LANG] + "<c>" if hideinner == True else "",
        noaccessories = "\n<yellow>" + layer_hide_accessories[LANG] + "<c>" if hideaccess == True else "",
        ncolorlock = "\n<yellow>" + ncosmetic_color_locks[LANG] + "<c>" if ncolorlocked == True else "")

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

layered_file_names = ["Basewear_Female",
                      "Basewear_Male",
                      "Innerwear_Female",
                      "Innerwear_Male",
                      "NGS_Outer_Female",
                      "NGS_Outer_Male"]

for name in layered_file_names:
    items_file_name = "Item_" + name + ".txt"
    
    try:
        items_file = codecs.open(os.path.join(json_loc, items_file_name),
                                 mode = 'r', encoding = 'utf-8')
    except FileNotFoundError:
        print("\t{0} not found.".format(items_file_name))
        continue
    
    items = json.load(items_file)
    print("{0} loaded.".format(items_file_name) + " {")
    
    items_file.close()

    newtranslations = False
    
    for item in items:
        problem = translate_nlayer_desc(item, name) if "選択可能になる。" in item["jp_explain"] else translate_layer_desc(item, name)

        if problem == 0:
            print("\tTranslated description for {0}".format(item["tr_text"] or item["jp_text"]))
            newtranslations = True

    if newtranslations == False:
        print("\tNo new translations.")
    
    print("}")
    
    items_file = codecs.open(os.path.join(json_loc, items_file_name),
                             mode = 'w', encoding = 'utf-8')
    json.dump(items, items_file, ensure_ascii=False, indent="\t", sort_keys=False)
    items_file.write("\n")
    items_file.close()

# Translate other cosmetics

cosmetic_file_names = [
    "NGS_Ear",
    "NGS_Horn",
    "NGS_Motion",
    "NGS_Mouth",
    "NGS_Stamps",
    "Stack_Accessory",
    "Stack_BodyPaint",
    "Stack_Eye",
    "Stack_EyeBrow",
    "Stack_EyeLash",
    "Stack_FacePaint",
    "Stack_Hairstyle",
    "Stack_Sticker"
    ]

cosmetic_types = {
    "NGS_Ear": ["ear shape", "귀", "", "耳朵"],
    "NGS_Horn": ["horn type", "뿔", "", "角"],
    "NGS_Motion": ["motion", "모션", "", "行動方式"],
    "NGS_Mouth": ["teeth and tongue\nset", "치아/혀", "", "牙齒、舌頭"],
    "NGS_Stamps": ["stamp", "스탬프", "", "表情圖"],
    "Stack_Accessory": ["accessory", "악세서리", "аксессуар", "飾品"],
    "Stack_BodyPaint": ["body paint", "바디 페인트", "рис. тела", "身體彩繪"],
    "Stack_Eye": ["eye pattern", "눈동자", "глаза", "瞳孔"],
    "Stack_EyeBrow": ["eyebrow type", "눈썹", "брови", "眉毛"],
    "Stack_EyeLash": ["eyelash type", "속눈썹", "ресницы", "睫毛"],
    "Stack_FacePaint": ["makeup", "메이크업", "макияж", "妝容"],
    "Stack_Hairstyle": ["hairstyle", "헤어스타일", "причёску", "髪型"],
    "Stack_Sticker": ["sticker", "스티커", "стикер", "貼紙"]
    }

# JP text: 
    # 使用すると、新しい{itype}の\n
    # {iname}が選択可能。
# {sexlock} unavailable.
cosmetic_desc_use_new_formats = [("Unlocks the {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "for use in the Beauty Salon."),
                         ("사용하면 새로운 {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "의 사용이 가능해진다."),
                         ("Разблок-т {itype} {sexlock}\n"
                          "\"{iname}\"\n"
                          "для использования в салоне."),
                         ("使用後，可選用新的{sexlock}{itype}\n"
                          "{iname}。")]

# JP text: 
    # チケットを使用すると、{itype}\n
    # {iname}が選択可能。
# {sexlock} unavailable.
cosmetic_desc_ticket_formats = [("Unlocks the {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "for use in the Beauty Salon."),
                         ("사용하면 새로운 {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "의 사용이 가능해진다."),
                         ("Разблок-т {itype} {sexlock}\n"
                          "\"{iname}\"\n"
                          "для использования в салоне."),
                         ("使用票券後，可選用{sexlock}{itype}\n"
                          "{iname}。")]

# JP text: 
    # チケットを使用すると、新しい{itype}の\n
    # {iname}が選択可能。
# {sexlock} unavailable.
cosmetic_desc_ticket_new_formats = [("Unlocks the {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "for use in the Beauty Salon."),
                         ("사용하면 새로운 {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "의 사용이 가능해진다."),
                         ("Разблок-т {itype} {sexlock}\n"
                          "\"{iname}\"\n"
                          "для использования в салоне."),
                         ("使用票券後，可選用新的{sexlock}{itype}\n"
                          "{iname}。")]

# JP text: 
    # 特定ステッカーの装着許可チケット。\n
    # 使用すると、新しい{itype}の\n
    # {iname}が選択可能。
# {sexlock} unavailable.
cosmetic_desc_sticker_use_new_formats = [("Unlocks the {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "for use in the Beauty Salon."),
                         ("사용하면 새로운 {sexlock}{itype}\n"
                          "\"{iname}\"\n"
                          "의 사용이 가능해진다."),
                         ("Разблок-т {itype} {sexlock}\n"
                          "\"{iname}\"\n"
                          "для использования в салоне."),
                         ("特定貼紙的著裝許可票券。\n"
                          "使用後，可選用新的{sexlock}{itype}\n"
                          "{iname}。")]

# JP text unavailable.
cosmetic_sex_locks = {"m": ["male-only ", "남성 전용 ", "только для М", "男性專用"],
                      "f": ["female-only ", "여성 전용 ", "только для Ж", "女性專用"]}

# JP text: 
    # ※サイズ調整はできません。
cosmetic_size_locks = ["※Size cannot be adjusted.",
                       "※사이즈 조정은 할 수 없습니다.",
                       "※Нельзя отрегулировать размер.",
                       "※無法調整尺寸。"]

# JP text: 
    # ※カラーは変更できません
cosmetic_color_locks = ["※Color cannot be changed",
                        "※색상은 변경할 수 없습니다",
                        "※Цвет нельзщя изменить.",
                        "※無法變更顏色"]

# JP text: 
    # 特定ステッカーの非表示許可チケット。\n
    # 使用すると、ステッカーの\n非表示が選択可能。
no_sticker_desc = [("Unlocks the ability to not display a\n"
                    "sticker in the Beauty Salon."),
                   ("특정 스티커 숨김 허가 티켓.\n"
                    "사용하면 스티커의\n"
                    "숨김이 선택 가능해집니다."),
                   ("Разблокирует возможность\n"
                    "не отображать стикер в салоне."),
                   ("特定貼紙的不顯示許可票券。\n"
                    "使用後可以選擇不顯示貼紙。")]

# New cosmetic tickets use the formats we defined earlier for new layer wear

def translate_cosmetic_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]

    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Exception for "no sticker" sticker
    elif item["jp_text"] == "ステッカーなし":
        item["tr_explain"] = no_sticker_desc[LANG]
        return 0
    
    # Some stickers have different names in-game from their tickets.
    # The in-game name is in the tickets' descriptions.
    # Extract it here.
    if file_name == "Stack_Sticker":
        description_name = regex.search(
            r'(?<=ステッカーの\n)(.+[ＡＢＣ]?)(?=が選択可能。)',
            item["jp_explain"]).group(0)

        if (description_name != item["jp_text"]):
            item_name = item_name.replace(" Sticker", "")
            item_name = item_name.replace("ステッカー", "")

    # Sort the description format
    desc_sort = "use_new"
    if item["jp_explain"].startswith("チケットを使用すると、新しい"):
        desc_sort = "ticket_new"
    elif item["jp_explain"].startswith("チケットを使用すると、"):
        desc_sort = "ticket"
    elif item["jp_explain"].startswith("特定ステッカーの装着許可チケット。"):
        desc_sort = "sticker_use_new"
    
    # Some items are locked to one sex or the other.
    sex = "n"
    if "女性のみ使用可能。" in item["jp_explain"]:
        sex = "f"
    elif "男性のみ使用可能。" in item["jp_explain"]:
        sex = "m"
    
    # Some items cannot be resized.
    sizelocked = False
    
    if "サイズ調整はできません。" in item["jp_explain"]:
        sizelocked = True

    # Some items cannot be recolored.
    colorlocked = False
    
    if "カラーは変更できません" in item["jp_explain"]:
        colorlocked = True

    # Some ngs items cannot be recolored.
    ncolorlocked = False
    
    if "カラー変更非対応" in item["jp_explain"]:
        ncolorlocked = True
    
    # Combine the variable name.
    desc_format_name = "cosmetic_desc_" + desc_sort + "_formats"

    # Translate the description.
    item["tr_explain"] = (eval(desc_format_name)[LANG] + "{sizelock}" + "{colorlock}" + "{ncolorlock}").format(
        sexlock = cosmetic_sex_locks[sex][LANG] if sex != "n" else "",
        itype = item_type,
        iname = item_name,
        sizelock = "\n<yellow>" + cosmetic_size_locks[LANG] + "<c>" if sizelocked == True else "",
        colorlock = "\n<yellow>" + cosmetic_color_locks[LANG] + "<c>" if colorlocked == True else "",
        ncolorlock = "\n<yellow>" + ncosmetic_color_locks[LANG] + "<c>" if ncolorlocked == True else "")
    
    # Hello Kitty item copyright notice
    if item["jp_text"] == "ハローキティチェーン":
        item["tr_explain"] += "\nc'76,'15 SANRIO APPR.NO.S564996"

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

def translate_ncosmetic_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]

    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2
    
    # Sort the description format
    desc_sort = "n"
    if "全キャラクターで選択可能になる。" in item["jp_explain"]:
        desc_sort = "allcharacters"
    elif "パターンが\n選択可能になる。" in item["jp_explain"]:
        desc_sort = "pattern"

    # Some items are locked to one race and/or type.
    types = get_type_restrictions(item)

    # Some items hide your innerwear (these are mostly swimsuits).
    hideinner = False
    if "着用時はインナーが非表示になります。" in item["jp_explain"]:
        hideinner = True
    
    # Some items are not supported in the PSO2 blocks.
    ngsonly = False
    if "『PSO2』ブロック非対応" in item["jp_explain"]:
        ngsonly = True
    
    # Combine the variable name.
    ndesc_format_name = "ndesc_" + desc_sort + "_formats"

    # Translate the description.
    item["tr_explain"] = (eval(ndesc_format_name)[LANG] + "{typelock}" + "{ngsonly}").format(
        itype = item_type,
        a = "a ",
        typelock = "" if types == "a" else "\n<yellow>※{0}{1}<c>".format(ntype_statements[LANG], ntype_locks[types][LANG]),
        hidepanties = "\n<yellow>" + layer_hide_inners[LANG] + "<c>" if hideinner == True else "",
        ngsonly = "\n<yellow>" + ngs_only[LANG] + "<c>"  if ngsonly == True else "")

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

for file_name in cosmetic_file_names:
    items_file_name = "Item_" + file_name + ".txt"
    item_type = cosmetic_types[file_name][LANG]
    
    try:
        items_file = codecs.open(os.path.join(json_loc, items_file_name),
                                 mode = 'r', encoding = 'utf-8')
    except FileNotFoundError:
        print("\t{0} not found.".format(items_file_name))
        continue
    
    items = json.load(items_file)
    print("{0} loaded.".format(items_file_name) + " {")
    
    items_file.close()

    newtranslations = False
    
    for item in items:
        problem = translate_ncosmetic_desc(item, file_name) if "選択可能になる。" in item["jp_explain"] else translate_cosmetic_desc(item, file_name)

        if problem == 0:
            print("\tTranslated description for {0}".format(item["tr_text"] or item["jp_text"]))
            newtranslations = True

    if newtranslations == False:
        print("\tNo new translations.")
    
    print("}")

    items_file = codecs.open(os.path.join(json_loc, items_file_name),
                             mode = 'w', encoding = 'utf-8')
    json.dump(items, items_file, ensure_ascii=False, indent="\t", sort_keys=False)
    items_file.write("\n")
    items_file.close()

# Translate LAs
try:
    items_file = codecs.open(os.path.join(json_loc, "Item_Stack_LobbyAction.txt"),
                             mode = 'r', encoding = 'utf-8')
except FileNotFoundError:
    print("\tItem_Stack_LobbyAction.txt not found.")

items = json.load(items_file)
print("Item_Stack_LobbyAction.txt loaded. {")

items_file.close()

# JP text: 
    # ロビアク『{iname}』\n
    # を全キャラクターで使用可能になる。
la_formats = [("Unlocks the new Lobby Action\n"
               "\"{iname}\"."),
              ("『{iname}』 로비 액션을\n"
               "모든 캐릭터에 등록한다."),
              ("Разблокирует новый лобби-экшн:\n"
               "\"{iname}\"."),
              ("所有角色均可選用大廳動作\n"
               "『{iname}』。")]

# JP text: 
    # 使用すると新しいロビーアクションが\n
    # 全キャラクターで選択可能になる。
nla_formats = [("Unlocks a new Lobby Action for use by\n"
                "all characters on your account."),
               ("사용하면 새로운 로비 액션이\n"
                "모든 캐릭터에서 사용 가능해진다."),
               ("Разблокирует новый лобби-экшн\n"
                "для всех персонажей вашего акка."),
               ("使用後所有角色均可選用新的大廳動作。")]

la_extras = {
            # JP text: 
                # ※対応機能：ボタン派生/一部表示適用外\n
                # 対応服指可動/『PSO2』ブロック非対応
            "*actnopreviewfingersngs": [
                ("※Extra actions (cannot preview).\n"
                 "Finger motion by outfit. Not in [PSO2]."),
                ("※지원 기능: 버튼 파생/일부 표시 적용 제외\n"
                 "대응 복장 손가락 움직임/『PSO2』 블록 미지원"),
                ("\n"
                 ""),
                ("※適用功能：按鍵衍生/不適用一部分顯示\n"
                 "適用服裝可動手指/不適用於『PSO2』")
                ],
            
            # JP text: 
                # ※対応機能：ボタン派生／\n
                # 対応服指可動／『PSO2』ブロック非対応
            "*actfingersngs": [
                ("Has button actions/Finger motion\n"
                 "outfit-limited/Can't use in [PSO2].<c>"),
                ("대응 기능: 버튼 파생/대응 복장\n"
                 "손가락 가동/『PSO2』 블록 비지원<c>"),
                ("Есть действия/Движен. пальцев\n"
                 "огранич./Недоступно в [PSO2].<c>"),
                ("※適用功能：按鍵衍生/\n"
                 "適用服裝可動手指/不適用於『PSO2』")
                ],

            # JP text: 
                # ※対応機能：ボタン派生／ランダム／\n
                # 対応服指可動
            "*actrandomfingers": [
                ("※Has button actions/randomness.\n"
                 "Finger motion limited based on outfit."),
                ("지원 기능: 버튼 파생/랜덤\n"
                 "대응복 손가락 가동"),
                ("Есть кнопка действия/рандом.\n"
                 "Одежда влияет на движ-е пальцев"),
                ("※適用功能：按鍵衍生/隨機動作/\n"
                 "適用服裝可動手指")
                ],

            # JP text: 
                # ※対応機能：ボタン派生／\n
                # 対応服指可動
            "*actfingers": [
                ("※Use action buttons for extra actions.\n"
                 "Finger motion limited based on outfit."),
                ("지원 기능: 버튼 파생\n"
                 "대응복 손가락 가동"),
                ("Доступно доп действие.\n"
                 "Одежда влияет на движ-е пальцев"),
                ("※適用功能：按鍵衍生/\n"
                 "適用服裝可動手指")
                ],

            # JP text: 
                # ※対応機能：対応服指可動／\n
                # 武器装備反映／『PSO2』ブロック非対応
            "*fingersweaponsngs": [
                ("※Finger motion outfit limited. Shows\n"
                 "equipment. Cannot perform in [PSO2]."),
                ("※지원 기능: 대응복 손가락 가동/\n"
                 "무기 장비 반영/『PSO2』블록 비대응"),
                ("※Движ. завис-т от одежды| Отображ.\n"
                 "экип. оружие| Только для NGS."),
                ("※適用功能：適用服裝可動手指/\n"
                 "顯示裝備武器/不適用於『PSO2』")
                ],

            # JP text: 
                # ※対応機能：対応服指可動／\n
                # 『PSO2』ブロック非対応
            "*fingersngs": [
                ("※Finger motion limited based on outfit.\n"
                 "Cannot perform in [PSO2] Blocks."),
                ("※지원 기능: 대응복 손가락 가동<c>\n"
                 "『PSO2』블록 비대응"),
                ("※Одежда влияет на движ-е пальцев\n"
                 "Нельзя использовать в блоке PSO2"),
                ("※適用功能：適用服裝可動手指/\n"
                 "不適用於『PSO2』")
                ],

            # JP text: 
                # ※対応機能：対応服指可動
            "*fingers": [
                ("※Finger motion limited based on outfit."),
                ("※지원 기능: 대응복 손가락 가동"),
                ("※Одежда влияет на движ-е пальцев"),
                ("※適用功能：適用服裝可動手指")
                ],
            
            # JP text: 
                # 対応機能：ボタン派生\n
                # <yellow>対象服のみ指も可動<c>
            # Only on a dummy LA but the script crashes when run with -a if not included
            "actfingers": [
                ("※Use action buttons for extra actions.\n"
                 "Finger motion limited based on outfit."),
                ("지원 기능: 버튼 파생\n"
                 "대응복 손가락 가동"),
                ("Доступно доп действие.\n"
                 "Одежда влияет на движ-е пальцев"),
                ("適用功能：按鍵衍生/\n"
                 "<yellow>適用服裝可動手指<c>")
                ],

            # JP text: 
                # 対応機能：ボタン派生／武器装備反映\n
                # <yellow>一部武器反映不可<c>
            "actweapons": [
                ("Shows equipment, has extra actions.\n"
                 "<yellow>Doesn't show some weapons.<c>"),
                ("지원 기능: 버튼 파생/무기 장비 반영\n"
                 "<yellow>일부 무기 반영 불가<c>"),
                ("Отображ. оружие; доп действие.\n"
                 "<yellow>Не показывает некоторое оружие.<c>"),
                ("適用功能：按鍵衍生/顯示裝備武器\n"
                 "<yellow>無法顯示一部分武器<c>")
                ],
                     
            # JP text: 
                # 対応機能：ボタン派生／ランダム
            "actrandom": [
                ("Has button actions/randomness."),
                ("지원 기능: 버튼 파생/랜덤"),
                ("Есть кнопка действия/рандом."),
                ("適用功能：按鍵衍生/隨機動作")
                ],
                     
            # JP text: 
                # 対応機能：ボタン派生
            "act": [
                ("Use action buttons for extra actions."),
                ("지원 기능: 버튼 파생"),
                ("Доступно доп действие."),
                ("適用功能：按鍵衍生")
                ],
                     
            # JP text: 
                # 対応機能：武器装備反映\n
                # <yellow>一部武器反映不可<c>
            "weapons": [
                ("Shows equipped weapons.\n"
                 "<yellow>Doesn't show some weapons.<c>"),
                ("지원 기능: 무기 장비 반영\n"
                 "<yellow>일부 무기 반영 불가<c>"),
                ("Показывает экип-е оружие.\n"
                 "<yellow>Не показывает некоторое оружие.<c>"),
                ("適用功能：顯示裝備武器\n"
                 "<yellow>無法顯示一部分武器<c>")
                ],

            # JP text: 
                # 対応機能：リアクション
            "react": [
                ("Reaction has extra actions."),
                ("지원 기능: 리액션"),
                ("Есть доп действие реакцией."),
                ("適用功能：反應動作")
                ]
            }

extras_names = {
    "ボタン派生/一部表示適用外\n対応服指可動/『PSO2』ブロック非対応<c>": "*actnopreviewfingersngs",
    "ボタン派生／\n対応服指可動／『PSO2』ブロック非対応<c>": "*actfingersngs",
    "ボタン派生／対応服指可動／\n『PSO2』ブロック非対応<c>": "*actfingersngs",
    "ボタン派生／ランダム／\n対応服指可動<c>": "*actrandomfingers",
    "ボタン派生／\n対応服指可動<c>": "*actfingers",
    "対応服指可動／\n武器装備反映／『PSO2』ブロック非対応<c>": "*fingersweaponsngs",
    "対応服指可動／\n『PSO2』ブロック非対応<c>": "*fingersngs",
    "対応服指可動<c>": "*fingers",
    "ボタン派生\n<yellow>対象服のみ指も可動<c>": "actfingers",
    "ボタン派生／武器装備反映\n<yellow>一部武器反映不可<c>": "actweapons",
    "ボタン派生／ランダム": "actrandom",
    "ボタン派生": "act",
    "武器装備反映\n<yellow>一部武器反映不可<c>": "weapons",
    "リアクション":"react"
    }

# JP text: 
    # 使用すると新しい手のポーズが\n全キャラクターで選択可能になる。\n
    # <yellow>※一部ロビーアクション非対応／\n
    # 『PSO2』ブロック非対応<c>
ha_formats = [("When used, allows you to select a\n"
               "new hand pose for all characters.\n"
               "<yellow>※Does not support all Lobby Actions.\n"
               "※Cannot perform in [PSO2] Blocks.<c>"),
              ("사용하면 새로운 손가락 포즈가\n"
               "모든 캐릭터로 선택할 수 있게 된다.\n"
               "<yellow>※일부 로비 액션 미지원/\n"
               "『PSO2』블록 비대응<c>"),
              ("Даёт возможность использовать\n"
               "версию с двигающимися пальцами.\n"
               "<yellow>※Поддерж-т не все лобби-экшены.\n"
               "※Нельзя использовать в блоке PSO2<c>"),
              ("使用後所有角色均可選用新的手部姿勢\n"
               "<yellow>※不適用於一部分大廳動作/\n"
               "不適用於『PSO2』<c>")]

def translate_la_desc(item):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]

    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Figure out what extra stuff to put at the end of the description
    extras = "n"
    # Split off the bit that changes and use it as the key to a dictionary of codenames    
    if "対応機能：" in item["jp_explain"]:
        extras_jp = item["jp_explain"].split("対応機能：")[1]
        extras = extras_names[extras_jp]
    elif "※『PSO2』ブロック非対応" in item["jp_explain"]:
        extras = "ngs_only"

    # Translate old LAs
    if "ロビアク『" in item["jp_explain"]:
        # Split LA name from number.
        splits = regex.split("[\"「」]", item_name)
        
        item["tr_explain"] = (la_formats[LANG] + "{extrastuff}").format(
            # Remember Photon Chairs have no number
            iname = splits[1] if len(splits) > 1 else splits[0],
            extrastuff = "" if extras == "n" else "\n" + la_extras[extras][LANG])
    
    # Translate hand poses    
    elif "使用すると新しい手のポーズが" in item["jp_explain"]:
        item["tr_explain"] = ha_formats[LANG]

    # Translate new LAs
    else:
        item["tr_explain"] = (nla_formats[LANG] + "{extrastuff}").format(
            extrastuff = ("" if extras == "n"
                          else "\n" + "<yellow>" + ngs_only[LANG] + "<c>" if extras == "ngs_only"
                          else "\n" + "<yellow>" + la_extras[extras][LANG] + "<c>"
                          )
                      )

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0    

for item in items:
    if translate_la_desc(item) == 0:
        print("\tTranslated description for {0}".format(item["tr_text"] or item["jp_text"]))
        newtranslations = True

if newtranslations == False:
    print("\tNo new translations.")

print("}")       

items_file = codecs.open(os.path.join(json_loc, "Item_Stack_LobbyAction.txt"),
                         mode = 'w', encoding = 'utf-8')
json.dump(items, items_file, ensure_ascii=False, indent="\t", sort_keys=False)
items_file.write("\n")
items_file.close()

# Translate voices

try:
    items_file = codecs.open(os.path.join(json_loc, "Item_Stack_Voice.txt"),
                             mode = 'r', encoding = 'utf-8')
except FileNotFoundError:
    print("\tItem_Stack_Voice.txt not found.")

items = json.load(items_file)
print("Item_Stack_Voice.txt loaded. {")
    
items_file.close()

cv_names = {
    "ゆかな": ["Yukana Nogami", "", "Ногами Юкана", ""],
    "チョー": ["Cho", "쵸", "Чо", ""],
    "ポポナ": ["Popona", "", "Попона", ""],
    "下野 紘": ["Hiro Shimono", "시모노 히로", "Хиро Симоно", ""],
    "中原 麻衣": ["Mai Nakahara", "나카하라 마이", "Маи Накахара", ""],
    "中尾 隆聖": ["Ryusei Nakao", "나카오 류세이", "Рюсэй Накао", ""],
    "中村 悠一": ["Yuichi Nakamura", "유이치 나카무라", "Юичи Накамура", ""],
    "中田 譲治": ["Joji Nakata", "나카타 조지", "Дзёдзи Наката", ""],
    "中西 茂樹": ["Shigeki Nakanishi", "", "Сигэки Наканиши", ""],
    "久野 美咲": ["Misaki Kuno", "", "Мисаки Куно", ""],
    "井上 和彦": ["Kazuhiko Inoue", "", "Казухико Иноэ", ""],
    "井上 喜久子": ["Kikuko Inoue", "", "Кикуко Иноуэ", ""],
    "井上 麻里奈": ["Marina Inoue", "", "Марина Иноуэ", ""],
    "井口 裕香": ["Yuka Iguchi", "", "Юка Игути", ""],
    "今井 麻美": ["Asami Imai", "", "Асами Имаи", ""],
    "伊瀬 茉莉也": ["Mariya Ise", "", "Мария Исэ", ""],
    "伊藤 静": ["Shizuka Ito", "", "Сидзука Ито", ""],
    "会 一太郎": ["Ichitaro Ai", "", "Ичитаро Ай", ""],
    "住友 優子": ["Yuko Sumitomo", "", "Юко Сумитомо", ""],
    "佐倉 綾音": ["Ayane Sakura", "", "Аянэ Сакура", ""],
    "佐武 宇綺": ["Uki Satake", "", "Уки Сатакэ", ""],
    "佐藤 利奈": ["Rina Sato", "", "Рина Сато", ""],
    "佐藤 友啓": ["Tomohiro Sato", "", "Томохиро Сато", ""],
    "佐藤 聡美": ["Satomi Sato", "", "Сатоми Сато", ""],
    "佳村 はるか": ["Haruka Yoshimura", "", "Харука Ёсимура", ""],
    "保志 総一朗": ["Soichiro Hoshi", "", "Соичиро Хоши", ""],
    "光吉 猛修": ["Takenobu Mitsuyoshi", "", "Такэнобу Мицуёши", ""],
    "内田 真礼": ["Maaya Uchida", "", "Маая Утида", ""],
    "千本木 彩花": ["Sayaka Senbongi", "", "Саяка Сэмбонги", ""],
    "古賀 葵": ["Aoi Koga", "", "Аой Кога", ""],
    "吉野 裕行": ["Hiroyuki Yoshino", "", "Хироюки Ёшино", ""],
    "名塚 佳織": ["Kaori Nazuka", "", "Каори Надзука", ""],
    "喜多村 英梨": ["Eri Kitamura", "", "Эри Китамура", ""],
    "坂本 真綾": ["Maaya Sakamoto", "", "Маая Сакамото", ""],
    "堀川 りょう": ["Ryo Horikawa", "", "Рё Хорикава", ""],
    "堀江 由衣": ["Yui Horie", "", "Юи Хориэ", ""],
    "増田 俊樹": ["Toshiki Masuda", "", "Тошики Масуда", ""],
    "天野 名雪": ["Nayuki Amano", "", "Наюки Амано", ""],
    "子安 武人": ["Takehito Koyasu", "", "Такэхито Коясу", ""],
    "安元 洋貴": ["Hiroki Yasumoto", "", "Хироки Ясумото", ""],
    "安済 知佳": ["Chika Anzai", "", "Чика Андзаи", ""],
    "寺島 拓篤": ["Takuma Terashima", "", "Такума Тэрашима", ""],
    "小倉 唯": ["Yui Ogura", "", "Юй Огура", ""],
    "小原 莉子": ["Riko Kohara", "", "Рико Кохара", ""],
    "小山 茉美": ["Mami Koyama", "", "Мами Кояма", ""],
    "小松 未可子": ["Mikako Komatsu", "", "Микако Комацу", ""],
    "小林 ゆう": ["Yu Kobayashi", "", "Ю Кобаяши", ""],
    "小清水 亜美": ["Ami Koshimizu", "", "Ами Косимидзу", ""],
    "小西 克幸": ["Katsuyuki Konishi", "", "Кацуюки Кониши", ""],
    "小野 大輔": ["Daisuke Ono", "", "Дайсукэ Оно", ""],
    "小野坂 昌也": ["Masaya Onosaka", "", "Масая Оносака", ""],
    "山岡 ゆり": ["Yuri Yamaoka", "", "Юри Ямаока", ""],
    "岡本 信彦": ["Nobuhiko Okamoto", "", "Нобухико Окамото", ""],
    "岩下 読男": ["Moai Iwashita", "", "Моаи Ивасита", ""],
    "島本 須美": ["Sumi Shimamoto", "", "Суми Симамото", ""],
    "島﨑 信長": ["Nobunaga Shimazaki", "", "Нобунага Симадзаки", ""],
    "川村 万梨阿": ["Maria Kawamura", "", "Мария Кавамура", ""],
    "川澄 綾子": ["Ayako Kawasumi", "", "Аяко Кавасуми", ""],
    "市来 光弘": ["Mitsuhiro Ichiki", "", "Мицухиро Ичики", ""],
    "引坂 理絵": ["Rie Hikisaka", "", "Рие Хирисака", ""],
    "悠木 碧": ["Aoi Yuki", "", "Аои Юки", ""],
    "戸松 遥": ["Haruka Tomatsu", "토마츠 하루카", "Харука Томацу", ""],
    "斉藤 壮馬": ["Soma Saito", "", "Сома Сайто", ""],
    "斉藤 朱夏": ["Shuka Saito", "", "Шюка Саито", ""],
    "斎藤 千和": ["Chiwa Saito", "사이토 치와", "Тива Сайто", ""],
    "新田 恵海": ["Emi Nitta", "", "Эми Нитта", ""],
    "日笠 陽子": ["Yoko Hikasa", "", "Ёко Хикаса", ""],
    "早見 沙織": ["Saori Hayami", "", "Саори Хаями", ""],
    "木村 珠莉": ["Juri Kimura", "", "Дзюри Кимура", ""],
    "木村 良平": ["Ryohei Kimura", "", "Рёхэй Кимура", ""],
    "本渡 楓": ["Kaede Hondo", "", "Каэдэ Хондо", ""],
    "杉田 智和": ["Tomokazu Sugita", "", "Томокадзу Сугита", ""],
    "村川 梨衣": ["Rie Murakawa", "", "Риэ Муракава", ""],
    "東山 奈央 ": ["Nao Toyama", "토야마 나오", "Нао Тояма", ""],
    "松岡 禎丞": ["Yoshitsugu Matsuoka", "마츠오카 요시츠구", "Ёсицугу Мацуока", ""],
    "柿原 徹也": ["Tetsuya Kakihara", "카키하라 테츠야", "Тэцуя Какихара", ""],
    "桃井 はるこ": ["Haruko Momoi", "", "Харуко Момои", ""],
    "桑島 法子": ["Houko Kuwashima", "", "Хоко Кувасима", ""],
    "梶 裕貴": ["Yuki Kaji", "", "Юки Кадзи", ""],
    "森久保 祥太郎": ["Showtaro Morikubo", "", "Сётаро Морикубо", ""],
    "植田 佳奈": ["Kana Ueda", "", "Кана Уэда", ""],
    "榊原 良子": ["Yoshiko Sakakibara", "", "Ёсико Сакакибара", ""],
    "榎本 温子": ["Atsuko Enomoto", "", "Ацуко Эномото", ""],
    "横山 智佐": ["Chisa Yokoyama", "", "Тиса Ёкояма", ""],
    "橘田 いずみ": ["Izumi Kitta", "", "Идзуми Китта", ""],
    "櫻井 孝宏": ["Takahiro Sakurai", "", "Такахиро Сакураи", ""],
    "水樹 奈々": ["Nana Mizuki", "", "Нана Мидзуки", ""],
    "水橋 かおり": ["Kaori Mizuhashi", "", "Каори Мидзухаси", ""],
    "江口 拓也": ["Takuya Eguchi", "", "Такуя Эгучи", ""],
    "沢城 みゆき": ["Miyuki Sawashiro", "", "Миюки Саваширо", ""],
    "沼倉 愛美": ["Manami Numakura", "", "Манами Нумакура", ""],
    "洲崎 綾": ["Aya Suzaki", "", "Ая Судзаки", ""],
    "清水 彩香": ["Ayaka Shimizu", "", "Аяка Симидзу", ""],
    "渡辺 久美子": ["Kumiko Watanabe", "", "Кумико Ватанабэ", ""],
    "潘 めぐみ": ["Megumi Han", "", "Мэгуми Хан", ""],
    "瀬戸 麻沙美": ["Asami Seto", "", "Асами Сэто", ""],
    "玄田 哲章": ["Tessho Genda", "", "Тэссё Гэнда", ""],
    "生天目 仁美": ["Hitomi Nabatame", "", "Хитоми Набатамэ", ""],
    "田中 理恵": ["Rie Tanaka", "", "Риэ Танака", ""],
    "田村 ゆかり": ["Yukari Tamura", "", "Юкари Тамура", ""],
    "田辺 留依": ["Rui Tanabe", "타나베 루이", "Руи Танабэ", ""],
    "甲斐田 裕子": ["Yuko Kaida", "", "Юко Каида", ""],
    "白石 涼子": ["Ryoko Shiraishi", "", "Рёко Сираиси", ""],
    "白鳥 哲": ["Tetsu Shiratori", "", "Тэцу Сиратори", ""],
    "皆口 裕子": ["Yuko Minaguchi", "미나구치 유코", "Юко Минагучи", ""],
    "矢島 晶子": ["Akiko Yajima", "", "Юко Минагучи", ""],
    "石田 彰": ["Akira Ishida", "", "Акира Исида", ""],
    "神原 大地": ["Daichi Kanbara", "", "Даичи Камбара", ""],
    "神谷 浩史": ["Hiroshi Kamiya", "", "Хироши Камия", ""],
    "福山 潤": ["Jun Fukuyama", "", "Дзюн Фукуяма", ""],
    "秋元 羊介": ["Yosuke Akimoto", "", "Ёсукэ Акимото", ""],
    "秦 佐和子": ["Sawako Hata", "", "Савако Хата", ""],
    "種田 梨沙": ["Risa Taneda", "타네다 리사", "Риса Танеда", ""],
    "立木 文彦": ["Fumihiko Tachiki", "타치키 후미히코", "Фумихико Тачики", ""],
    "立花 理香": ["Rika Tachibana", "", "Рика Тачибана", ""],
    "竹達 彩奈": ["Ayana Taketatsu", "", "Аяна Такэтацу", ""],
    "細谷 佳正": ["Yoshimasa Hosoya", "", "Ёшимаса Хосоя", ""],
    "紲星 あかり": ["Kizuna Akari", "", "Кизуна Акари", ""],
    "結月 ゆかり": ["Yuzuki Yukari", "", "Юзуки Акари", ""],
    "緑川 光": ["Hikaru Midorikawa", "", "Хикару Мидорикава", ""],
    "緒方 恵美": ["Megumi Ogata", "", "Мэгуми Огата", ""],
    "能登 麻美子": ["Mamiko Noto", "", "Мамико Ното", ""],
    "花江 夏樹": ["Natsuki Hanae", "", "Нацуки Ханаэ", ""],
    "花澤 香菜": ["Kana Hanazawa", "", "Кана Ханадзава", ""],
    "若本 規夫": ["Norio Wakamoto", "", "Норио Вакамото", ""],
    "茅野 愛衣": ["Ai Kayano", "", "Аи Каяно", ""],
    "草尾 毅": ["Takeshi Kusao", "", "Такэши Кусао", ""],
    "菊地 美香": ["Mika Kikuchi", "", "Мика Кикучи", ""],
    "蒼井 翔太": ["Shouta Aoi", "", "Сёта Аои", ""],
    "藤本 結衣": ["Yui Fujimoto", "", "Юи Фудзимото", ""],
    "藤田 曜子": ["Yoko Fujita", "", "Ёко Фудзита", ""],
    "藤田 茜": ["Akane Fujita", "", "Аканэ Фудзита", ""],
    "諏訪 彩花": ["Ayaka Suwa", "", "Аяка Сува", ""],
    "諏訪部 順一": ["Junichi Suwabe", "", "Дзюнъичи Сувабэ", ""],
    "豊口 めぐみ": ["Megumi Toyoguchi", "", "Мэгуми Тоёгучи", ""],
    "豊崎 愛生": ["Aki Toyosaki", "", "Аки Тоёсаки", ""],
    "近藤 佳奈子": ["Kanako Kondo", "", "Канако Кондо", ""],
    "速水 奨": ["Sho Hayami", "", "Сё Хаями", ""],
    "那須 晃行": ["Akiyuki Nasu", "", "Акаюки Насу", ""],
    "金元 寿子": ["Hisako Kanemoto", "", "Хисако Канэмото", ""],
    "金田 アキ": ["Aki Kanada", "", "Аки Канада", ""],
    "釘宮 理恵": ["Rie Kugimiya", "", "Риэ Кугимия", ""],
    "鈴村 健一": ["Kenichi Suzumura", "스즈무라 켄이치", "Кэнъити Судзумура", ""],
    "銀河 万丈": ["Banjo Ginga", "", "Бандзё Гинга", ""],
    "長谷川 唯": ["Yui Hasegawa", "", "Юи Хасэгава", ""],
    "門脇 舞以": ["Mai Kadowaki", "", "Маи Кадоваки", ""],
    "関 智一": ["Tomokazu Seki", "", "Томокадзу Сэки", ""],
    "阿澄 佳奈": ["Kana Asumi", "", "Кана Асуми", ""],
    "陶山 章央": ["Akio Suyama", "", "Акио Суяма", ""],
    "雨宮 天": ["Sora Amamiya", "", "Сора Амамия", ""],
    "飛田 展男": ["Nobuo Tobita", "", "Нобуо Тобита", ""],
    "飯田 友子": ["Yuko Iida", "이이다 유우코", "Юко Иида", ""],
    "高木 友梨香": ["Yurika Takagi", "", "Юрика Такаги", ""],
    "高橋 未奈美": ["Minami Takahashi", "", "Минами Такахаши", ""],
    "高橋 李依": ["Rie Takahashi", "", "Риэ Такахаши", ""],
    "高野 麻里佳": ["Marika Kono", "", "Марика Коно", ""],
    "黒沢 ともよ": ["Tomoyo Kurosawa", "", "Томоё Куросава", ""],
    "こおろぎさとみ": ["Satomi Korogi", "코오로기 사토미", "Сатоми Короги", ""],
    "三宅 健太": ["Kenta Miyake", "", "Кэнта Миякэ", ""],
    "諸星 すみれ": ["Sumire Morohoshi", "", "Сумирэ Морохоси", ""],
    "宮本 侑芽": ["Yume Miyamoto", "", "Юмэ Миямото", ""],
    "川島 得愛": ["Tokuyoshi Kawashima", "", "Токуёси Кавасима", ""],
    "田所 あずさ": ["Azusa Tadokoro", "", "Адзуса Тадокоро", ""],
    "森田 順平": ["Junpei Morita", "", "Дзюмпэи Морита", ""],
    "上田 麗奈": ["Reina Ueda", "", "Уэда Рэйна", ""],
    "入野 自由": ["Miyu Irino", "", "Ирино Мию", ""],
    "梅原 裕一郎": ["Yuichiro Umehara", "", "Умэхара Юитиро", ""],
    "逢坂 良太": ["Ryota Osaka", "", "Осака Рёта", ""],
    "小原 好美": ["Konomi Kohara", "", "", ""],
    "白上 フブキ": ["Shirakami Fubuki", "", "", ""],
    "影山 シエン": ["Kageyama Shien", "", "", ""],
    "一 伊那尓栖": ["Ninomae Ina'nis", "", "", ""],
    "日野 聡": ["Satoshi Hino", "", "", ""],
    "原 由実": ["Yumi Hara", "", "", ""],
    "闇ノ シュウ": ["Shu Yamino", "", "", ""],
    "星川 サラ": ["Hoshikawa Sara", "", "", ""],
    "葉加瀬 冬雪": ["Hakase Fuyuki", "", "", ""],
    "甲斐田 晴": ["Haru Kaida", "", "", ""],
    "津田 健次郎": ["Kenjiro Tsuda", "", "", ""],
    "鬼頭 明里": ["Akari Kito", "", "", ""],
    "Ｍ・Ａ・Ｏ": ["M・A・O", "M・A・O", "M・A・O", "M・A・O", ""],
    "？？？": ["???", "???", "???", "???"],
    "": ["Unknown", "알 수 없는", "Неизвестно", ""]
    }

# What to fall back to if a name hasn't been translated into your language.
# -1: Prefer falling back to JP over any other language
name_fallbacks = {0: -1,
                  1: -1,
                  2: 0,
                  3: -1}

# JP text: 
    # 使用すると、新しいボイスが選択可能。
voice_desc_formats = ["Allows a new voice to be selected.",
                      "사용하면 새로운 보이스 사용 가능.",
                      "Позволяет выбрать новый голос.",
                      "使用後，可選用新的語音。"]

def translate_voice(item):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]

    # No JP description so skip this one
    if item["jp_explain"] == "":
            return -1
    
    # Description already present, leave it alone
    if (item["tr_explain"] != "" and REDO_ALL == False
          # Catch old format descriptions that keep creeping in somehow.
          and "Salon" not in item["tr_explain"]): 
        return -2

    # Strings for race/sex combo restrictions
    # JP text unavailable.
    restrictions = {
    "hm": ["\nNon-Cast male characters only.",
           "\n인간 남성만 사용 가능.",
           "\nТолько для М не CAST'ов.",
           "\n僅限非機器人男性使用。"],
    "hf": ["\nNon-Cast female characters only.",
           "\n인간 여성만 사용 가능.",
           "\nТолько для Ж не CAST'ов.",
           "\n僅限非機器人女性使用。"],
    "cm": ["\nMale Casts only.",
           "\n캐스트 남성만 사용 가능.",
           "\nТолько для М CAST'ов.",
           "\n僅限男性機器人使用。"],
    "cf": ["\nFemale Casts only.",
           "\n캐스트 여성만 사용 가능.",
           "\nТолько для Ж CAST'ов.",
           "\n僅限女性機器人使用。"],
    "am": ["\nMale characters only (all races).",
           "\n남성만 사용 가능.",
           "\nТолько М персонажей (все расы).",
           "\n僅限男性使用。"],
    "af": ["\nFemale characters only (all races).",
           "\n여성만 사용 가능.",
           "\nТолько Ж персонажей (все расы).",
           "\n僅限女性使用。"],
    "an": ["\nUsable by all characters.",
           "\n모두 사용 가능.",
           "\nДоступно всем персонажам.",
           ""]}
    
    # Detect ticket's race/sex restriction.
    # Default to no restriction.
    racensex= "an"
    
    if "人間男性のみ使用可能。" in item["jp_explain"]:
        racensex= "hm"
    elif "人間女性のみ使用可能。" in item["jp_explain"]:
        racensex= "hf"
    elif "キャスト男性のみ使用可能。" in item["jp_explain"]:
        racensex= "cm"
    elif "キャスト女性のみ使用可能。" in item["jp_explain"]:
        racensex= "cf"
    elif "男性のみ使用可能。" in item["jp_explain"]:
        racensex= "am"
    elif "女性のみ使用可能。" in item["jp_explain"]:
        racensex= "af"
    
    # Find out if we know the voice actor's name
    jp_cv_name = item["jp_explain"].split("ＣＶ")[1]
    cv_name = ""

    # We do, so try to translate it
    if jp_cv_name in cv_names: 
        curr_lang = LANG
        
        while cv_name == "":
            # We've fallen back to JP. Nowhere else to fall back to so break
            if curr_lang == -1:
                cv_name = jp_cv_name
                break
            else:
                cv_name = cv_names[jp_cv_name][curr_lang]
                if cv_name == "":
                    print("\tWARNING: No translation for {jp} in {currlang}, falling back to {nextlang}".format(
                        jp = jp_cv_name,
                        currlang = LANGS[curr_lang],
                        nextlang = LANGS[name_fallbacks[curr_lang]]))
                curr_lang = name_fallbacks[curr_lang]
        
    else:
        # We don't, so report it.
        print("Voice ticket {0} has a new voice actor: {1}"
              .format(item_name, jp_cv_name))
        cv_name = jp_cv_name
    
    # Translate the description
    item["tr_explain"] = voice_desc_formats[LANG] + "{restriction}\nCV: {actorname}".format(
        restriction = restrictions[racensex][LANG],
        actorname = cv_name)

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
        
    return 0

for item in items:
    
    if translate_voice(item) == 0:
        print("\tTranslated description for {0}".format(item["tr_text"] or item["jp_text"]))
        newtranslations = True

if newtranslations == False:
    print("\tNo new translations.")

print("}")       

items_file = codecs.open(os.path.join(json_loc, "Item_Stack_Voice.txt"),
                         mode = 'w', encoding = 'utf-8')
json.dump(items, items_file, ensure_ascii=False, indent="\t", sort_keys=False)
items_file.write("\n")
items_file.close()

# JP text: 
    # マグの見た目を変更するデバイス。
magd_evol_formats = ["A device that changes a Mag's form.",
                            "마그의 외형을 변경하는 디바이스.",
                            "",
                            "變更瑪古外觀的裝置。"]

# JP text: 
    # マグのレベルや支援機能をリセットし\n
    # マグを初期の状態に戻すデバイス。
magd_reset_formats = [("Resets a Mag's appearance, stats,\n"
                                "and support functions back to its \n"
                                "default state."),
                                ("마그의 레벨과 지원 기능을 재설정 하고\n"
                                "마그를 초기 상태로 되롤릴 수 있는 장치"),
                                (""),
                                ("重置瑪古的等級與支援功能\n"
                                "並使瑪古變回初始狀態的裝置。")]

# Translate the files that can be sorted by description or item name.
def translate_cosmeticsorted_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]
    
    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Sort the description format
    desc_sort = "use_new"
    if item["jp_explain"].startswith("チケットを使用すると、新しい"):
        desc_sort = "ticket_new"

    # Some Mag devices can only be used for mags that are lv.100 or above in PSO2.
    magdlv100 = False
    if "『PSO2』ではLv.100以上の" in item["jp_explain"]:
        magdlv100 = True

    # Some Mag devices can only be used in NGS.
    magdngs = False
    if "『NGS』でのみ使用可能" in item["jp_explain"]:
        magdngs = True

    # Sort the type.
    item_type = "n"
    if "新しい頭部" in item["jp_explain"]:
        item_type = "Head"
    elif "パートナーカード（ＰＣ）" in item["jp_explain"]:
        item_type = "Personalcard"
    elif "マグの見た目を変更するデバイス" in item["jp_explain"]:
        item_type = "MagDeviceEvol"
    elif "マグのレベルや支援機能をリセットし" in item["jp_explain"]:
        item_type = "MagDeviceReset"
    
    # Combine the variable name.
    desc_format_name = "cosmetic_desc_" + desc_sort + "_formats"

    # Translate the description.
    if item_type == "Personalcard":
        # Need to expand if needed
        return -1
    elif item_type.startswith("MagDevice"):
        item["tr_explain"] = ("{magd_format}" + "{magd_lv100limit}" + "{magd_ngslimit}").format(
        magd_format = (magd_evol_formats[LANG] if item_type == "MagDeviceEvol" else magd_reset_formats[LANG]),
        magd_lv100limit = "\n<yellow>" + mag_device_lv100[LANG] + "<c>" if magdlv100 == True else "",
        magd_ngslimit = "\n<yellow>" + mag_device_ngs[LANG] + "<c>" if magdngs == True else "")
    else: 
        item["tr_explain"] = (eval(desc_format_name)[LANG]).format(
            itype = cosmeticsorted_types[item_type][LANG],
            iname = item_name,
            sexlock = "")

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

def translate_ncosmeticsorted_desc(item, file_name):
    item_name = ""

    # Decide what name we're working with
    if TRANS_ALL:
        item_name = item["tr_text"] or item["jp_text"]
    else:
        if item["tr_text"] == "":
            # No translated name so skip this one
            return -1
        else:
            item_name = item["tr_text"]
    
    # Description already present, leave it alone
    if item["tr_explain"] != "" and REDO_ALL == False:
        return -2

    # Sort the type.
    item_type = "n"
    if "新しい顔バリエーション" in item["jp_explain"]:
        item_type = "Facetype"
    elif "新しいヘッドパーツ" in item["jp_explain"]:
        item_type = "Headparts"
    elif "・ボディ" in item["jp_text"]:
        item_type = "Bodyparts"
    elif "・アーム" in item["jp_text"]:
        item_type = "Armparts"
    elif "・レッグ" in item["jp_text"]:
        item_type = "Legparts"
    elif "パートナーカード（ＰＣ）" in item["jp_explain"]:
        item_type = "Personalcard"
    
    # Translate the description.
    if item_type == "Personalcard":
        # Need to expand if needed
        return -1
    else: 
        item["tr_explain"] = (ndesc_n_formats[LANG]).format(
            itype = cosmeticsorted_types[item_type][LANG],
            # Ugly hack
            a = "" if item_type.endswith("s") else "a ",
            iname = item_name)

    item["tr_explain"] = item["tr_explain"].translate(chartable[LANG])
    
    return 0

cosmeticsorted_file_names = [
    "FacePattern",
    "NGS_Parts_Female",
    "NGS_Parts_Male",
    "Stack_DeviceHT",
    "Stack_Headparts"
    ]

cosmeticsorted_types = {
    "Head": ["head", "헤드 파츠", "", "頭部"],
    "Facetype": ["face type", "얼굴 바리에이션", "", "面部類型"],
    "Headparts": ["head parts", "헤드 파츠", "", "頭部部件"],
    "Bodyparts": ["body parts", "바디 파츠", "", "身體部件"],
    "Armparts": ["arm parts", "암 파츠", "", "手臂部件"],
    "Legparts": ["leg parts", "레그 파츠", "", "腿部部件"]
    }

for file_name in cosmeticsorted_file_names:
    items_file_name = "Item_" + file_name + ".txt"
    
    try:
        items_file = codecs.open(os.path.join(json_loc, items_file_name),
                                 mode = 'r', encoding = 'utf-8')
    except FileNotFoundError:
        print("\t{0} not found.".format(items_file_name))
        continue
    
    items = json.load(items_file)
    print("{0} loaded.".format(items_file_name) + " {")
    
    items_file.close()

    newtranslations = False
    
    for item in items:
        problem = translate_ncosmeticsorted_desc(item, file_name) if "選択可能になる。" in item["jp_explain"] or item["jp_explain"] == "" else translate_cosmeticsorted_desc(item, file_name)

        if problem == 0:
            print("\tTranslated description for {0}".format(item["tr_text"] or item["jp_text"]))
            newtranslations = True

    if newtranslations == False:
        print("\tNo new translations.")
    
    print("}")

    items_file = codecs.open(os.path.join(json_loc, items_file_name),
                             mode = 'w', encoding = 'utf-8')
    json.dump(items, items_file, ensure_ascii=False, indent="\t", sort_keys=False)
    items_file.write("\n")
    items_file.close()

print ("Ticket translation complete.")
