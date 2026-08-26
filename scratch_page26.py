import json

entries = [
("patch of material","banki","n.m. (pl. bankè-bankè)",26),
("taking one's leave of s.o., saying good-bye","ban kwana","n.m.",26),
("twist outwards, warp or bend sth.","bankàra","v.t.",26),
("acne in adolescents","bàn-ni-dà-mugù","n.m.",26),
("loincloth","bànte","n.m. (pl. bantunà)",26),
("useless, foolish person or thing","banza","n.f.",26),
("in vain","banza","adv. (with à)",26),
("cheaply, easily, free","banza","adv. (with à)",26),
("last year","bàra","n.f. and adv.",26),
("aiming at sth., attempting to catch sth.","bàra","n.f.",26),
("servant","barà","n.m. (f. baranyà, pl. barori)",26),
("begging for alms","barà","n.f.",26),
("eggs left unhatched","bàrà-gurbì","n.m.",26),
("sth. or s.o. left after others have gone","bàrà-gurbì","n.m.",26),
("at variance, in disharmony","baram-baràm","adv.",26),
("buying goods speculatively for resale at a large profit","baràndà","n.m.",26),
("any strong alcoholic beverage","bàràsa","n.f.",26),
("sprinkle, scatter","barbàda","v.t.",26),
("a biting fly","bârbajè","n.m.",26),
("mating by animals","barbara","n.f.",26),
("sleep","barci","n.m.",26),
("solidification of liquids","barci","n.m.",26),
("a traditional title held by a mounted warrior","bardè","n.m. (pl. baràde)",26),
("brave person","bardè","n.m. (pl. baràde)",26),
("outsider, stranger, one not related by blood","bàre","n.m. or f.",26),
("gazelle","bàrewa","n.f. (pl. bàreyi)",26),
("stable","bârga","n.f.",26),
("blanket","bàrgo","n.m. (pl. bargunà)",26),
("leave, leave off","bari","v.t. (becomes bar before obj.)",26),
("let, allow","bari","v.t. (becomes bar before obj.)",26),
("barracks, camp, rest house","barjiki","n.f.",26),
("township, urban area, city","barjiki","n.f.",26),
("corkscrew","barimà","n.f. (pl. barimu)",26),
("thread of screw","barimà","n.f. (pl. barimu)",26),
("general greeting (to which reply is ~ kadai)","barkà","excl.",26),
("in disorder, mess","barkàtai","adv.",26),
("pepper","bàrkòno","n.m.",26),
("joking","barkwanci","n.m.",26),
("used in yakin ~ any destructive war, esp. civil war","basasà","n.f.",26),
("debt, buying sth. on credit","bashi","n.m. (pl. basussukà)",26),
("bad smell of rotting meat or fish","bashi","n.m.",26),
("large needle for sewing leather and stiff materials","bàsilla","n.f. (pl. bàsillu)",26),
("insight, quick understanding, intelligence","basirà","n.f.",26),
("bicycle","basukùr","n.m. (pl. basukurori)",26),
("piles, haemorrhoids","basùr","n.m.",26),
("bundle of grass prepared for thatching","bata","n.m.",26),
("coming to blows, physical struggle","bà-ta-kashì","n.m.",26),
("battalion","bataliyà","n.f. (pl. bataliyoyi)",26),
("battery","batir","n.m. (pl. baturà)",26),
("indecent talk","batsa","n.f.",26),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 26: {len(entries)} entries\n")

print("wrote", len(entries))
