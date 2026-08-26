import json

entries = [
("water trickling down wall from leaky roof","bi-bango","n.m.",28),
("cover with smoke, dust, etc.","bice","v.t.",28),
("go out, be extinguished (of fire, lamp)","bice","v.i.",28),
("thatching needle","bidà","n.m.",28),
("subdue, force under control","bi dà","v.t.",28),
("lead","bi dà","v.t.",28),
("one after the other, in order, in sequence","bî dà bî","adv.",28),
("roan horse","bidi","n.m.",28),
("orange-coloured bambara groundnuts","bidi","n.m.",28),
("innovation in religious practices, heresy","bidi'à","n.f. (pl. bidi'o'i)",28),
("merrymaking, drumming","bidi'à","n.f. (pl. bidi'o'i)",28),
("look for, search","bida","v.t. (i/e)",28),
("thud","bif","id.",28),
("place","bigirè","n.m. (pl. bigirai)",28),
("large bull","bijimi","n.m. (pl. bijimai)",28),
("stalwart fellow","bijimi","n.m. (pl. bijimai)",28),
("revolt, desert","bijire","v.t. (with i.o.)",28),
("baboon","bika","n.m.",28),
("celebration, festival, feast, ceremony","biki","n.m. (pl. bukukuwà)",28),
("bay horse","bikili","n.m.",28),
("attempt to reconcile runaway wife, enemy, etc.","bikò","n.m.",28),
("hot baths taken by women lasting up to forty days after delivery of child","biki","n.m.",28),
("bill, invoice","bîl","n.m.",28),
("without limit, numerous, many","bila haddin","adv.",28),
("long, aimless, and fruitless search","bilimbituwa","n.f.",28),
("thinking constantly and anxiously about sth.","bimbini","n.m.",28),
("investigate, inquire into","bincika","v.t. (vn. bincike)",28),
("investigation","bincike","n.m. (pl. bincikè-bincikè)",28),
("research","bincike","n.m. (pl. bincikè-bincikè)",28),
("gun, firearm","bindigà","n.f. (pl. bindigogi)",28),
("repeatedly, often","bini-bini","adv.",28),
("fulani-style hand-woven shirt, open at the sides","binjima","n.f.",28),
("sowing of seeds in anticipation of the rains","binne","n.m.",28),
("bury","binnè","v.t.",28),
("fill in a hole","binnè","v.t.",28),
("summit, top","birbishi","n.m.",28),
("brigadier","birgediyà","n.m.",28),
("rolling on the ground (animal or child)","birgima","n.f.",28),
("monkey","biri","n.m. (pl. birai)",28),
("ignoring a person, turning a deaf ear","biris","id.",28),
("abundantly","birjik","id.",28),
("brake(s)","birki","n.m.",28),
("overturn, turn inside out","birkice","v.t.",28),
("become confused, upset, disorganized","birkice","v.i.",28),
("roll sth. around in liquid or powder to coat it","birkidà","v.t.",28),
("roll about on the ground (animal)","birkidà","v.i.",28),
("bricklayer","birkilà","n.m. (pl. birkiloli)",28),
("walled town, city","birni","n.m. (pl. birane)",28),
("ball-point pen, biro","biro","n.m.",28),
("on top, above, on","bisa","prep.",28),
("concerning, with reference to","bisa","prep.",28),
("in accordance with","bisa","prep.",28),
("used in forming fractions","bisa","prep.",28),
("pack animal","bisa","n.f. (pl. bisàshe)",28),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 28: {len(entries)} entries\n")

print("wrote", len(entries))
