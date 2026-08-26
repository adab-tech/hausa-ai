import json

entries = [
("banana(s)","ayàbà","n.f.",23),
("iron for pressing","ayàn","n.m.",23),
("pressing, ironing","ayàn","n.m.",23),
("caravan","ayàri","n.m. (pl. ayàrori)",23),
("how terrible!, i'm so sorry! (used for serious misfortune such as bad accident or death)","ayyà","excl.",23),
("what a shame!, how terrible! (used after hearing of sth. bad but not really serious)","ayyà","excl.",23),
("the sound of guda","ayyurùrûi","id.",23),
("put or place sth. on top of sth.","azà","v.t.",23),
("impose (e.g. task or tax)","azà","v.t.",23),
("think","azà","v.i.",23),
("great pain, anguish, torture","azabà","n.f. (pl. azàbu, azabobi)",23),
("second prayer of the day; time of day from about 2 p.m. to 4 p.m.","azahar","n.f.",23),
("used in tun fil ~ since time immemorial","azal","adv.",23),
("predestined misfortune","azàliyà","n.f.",23),
("intention, purpose, zeal","azamà","n.f.",23),
("sense, meaning","azanci","n.m.",23),
("common sense, intelligence, wit","azanci","n.m.",23),
("section of split tree (usu. deleb palm) used for roofing","azara","n.f. (pl. azàru)",23),
("the fast of ramadan","azumi","n.m.",23),
("fasting","azumi","n.m.",23),
("silver","azurfa","n.f.",23),
("oppressor, bully, cheat","azzalumi","n.m. (f. azzaluma, pl. azzalùmai)",23),
("penis","azzakàri","n.m.",23),
("there isn't any, there aren't any","bâ","(alt. form of babù when obj. expressed)",23),
("without","bâ","(alt. form of babù when obj. expressed)",23),
("less (in telling time)","bâ","(alt. form of babù when obj. expressed)",23),
("not (general negative marker)","ba","(neg. particle, tone varies acc. to use)",23),
("give, offer","ba","v.t. (becomes bâ before noun obj.)",23),
("cause emotion in s.o.","ba","v.t. (becomes bâ before noun obj.)",23),
("mockery, joke","ba'à","n.f.",23),
("soldier","ba'askarè","n.m. (pl. askarawa)",23),
("father","bàba","n.m.",23),
("respectful term of address for an old man","bàba","n.m.",23),
("eunuch","bàba","n.m. (pl. bàbanni)",23),
("paternal aunt, mother","babà","n.f.",23),
("indigo","baba","n.m.",23),
("professional beggar who attaches himself to praise-singers and musicians","bàbambadè","n.m. (f. bàbambadiya, pl. bambadawa)",23),
("good-quality knife or sword made in borno","bàbarbarà","n.f.",23),
("big","bàbba","n. and adj. (pl. mânya)",23),
("important, great","bàbba","n. and adj. (pl. mânya)",23),
("elder, senior","bàbba","n. and adj. (pl. mânya)",23),
("grill, toast, singe","babbaka","v.t. (vn.f. bàbbaka)",23),
("block up space with one's body","babbakè","v.t.",23),
("stage of learning arabic consonants without vowels","babbaku","n.m.",23),
("large locust","babè","n.m.",23),
("chapter","babi","n.m.",23),
("category","babi","n.m.",23),
("there isn't any, there aren't any (neg. form corresponding to àkwai)","babù","(neg. particle)",23),
("motorcycle","bàbur","n.m. (pl. babùrà)",23),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 23: {len(entries)} entries\n")

print("wrote", len(entries))
