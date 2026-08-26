import json

entries = [
("alt. form of bayar dà","ba dà","v.t.",24),
("change (clothes, direction, etc.)","baddàla","v.t.",24),
("water-lily","badò","n.m.",24),
("leather worker","bàdukù","n.m. (pl. dukàwa)",24),
("sprinkle powdered substance","badà","v.t.",24),
("next year","bàdi","n.f. and adv.",24),
("powdered mixture of spice and groundnut cake sprinkled on tsire and kilishi","bàdi","n.m.",24),
("courtier","bàfadà","n.m. (pl. fàdàwa)",24),
("paternal uncle","baffà","n.m. (pl. bàffànni)",24),
("large acacia tree","bàgàruwa","n.f.",24),
("unsophisticated person, simpleton, rustic","bàgidajè","n.m. (f. bàgidajjiya, pl. gidàdàwa)",24),
("gwari man","bàgwari","n.m. (f. bàgwariya, pl. gwàràwa)",24),
("person who cannot speak hausa well","bàgwari","n.m. (f. bàgwariya, pl. gwàràwa)",24),
("left-handed person","bàhagò","n.m. (f. bàhagùwa, pl. bàhàgwai)",24),
("difficult person or thing","bàhagò","n.m. (f. bàhagùwa, pl. bàhàgwai)",24),
("investigation, inquiry","bàhàsi","n.m.",24),
("latrine","bâ-hayà","n.m.",24),
("miser","bàhili","n.m. (f. bàhiliya, pl. bàhilai)",24),
("bathtub, large round basin","bahò","n.m.",24),
("he did not","bài","(contr. of neg. marker bà and pro. yà)",24),
("alt. form of ²ba before noun obj.","bai","v.t. (with wà)",24),
("inside-out","bàibâi","adv.",24),
("thatch a house","baibàye","v.t. (vn.f. bàibayà)",24),
("level, smooth","bâi daya","adv.",24),
("similar, same","bâi daya","adv.",24),
("betrothal","baiko","n.m.",24),
("line of verse, stanza","baiti","n.m. (pl. baitoci)",24),
("treasury","bàitùlmali","n.m.",24),
("gift, esp. from god","baiwa","n.f.",24),
("generosity","baiwa","n.f.",24),
("betrothal","baiwa","n.f.",24),
("cloth on which card players play","bajau","n.m.",24),
("reddened (used of mouth stained with kolanut)","bajau","adv.",24),
("make level, flatten","bajè","v.t.",24),
("spread out","bajè","v.t.",24),
("smeared all over (usu. with filth)","bajè-bajè","id.",24),
("possessing outstanding, impressive qualities (e.g. bravery or strength)","bajintà","n.f.",24),
("badge","bajò","n.m.",24),
("bow","baka","n.m. (pl. bakunkunà)",24),
("catch of lock","baka","n.m. (pl. bakunkunà)",24),
("hacksaw","baka","n.m. (pl. bakunkunà)",24),
("in the mouth","bakà","adv.",24),
("winnow grain with circular tray","bakàce","v.t. (vn. bàkàce)",24),
("pretending to be asleep","bakan","n.m.",24),
("mouth","bàki","n.m. (pl. bakunà)",24),
("mouth of vessel, opening, entrance","bàki","n.m. (pl. bakunà)",24),
("speaking, speech","bàki","n.m. (pl. bakunà)",24),
("edge","bàki","n.m. (pl. bakunà)",24),
("limit","bàki","n.m. (pl. bakunà)",24),
("in exchange for, as equivalent to","bàkin","prep.",24),
("on the verge of","bàkin","prep.",24),
("seven","bakwài","n.f. and adj.",24),
("black, dark","baƙi","n. and adj. (f. baƙa, pl. baƙàƙe)",24),
("sth. bad, negative (in compounds)","baƙi","n. and adj. (f. baƙa, pl. baƙàƙe)",24),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 24: {len(entries)} entries (2nd baƙi 'letter' entry continues on page 25)\n")

print("wrote", len(entries))
