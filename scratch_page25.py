import json

entries = [
("letter of any alphabet","baƙi","n.m.",25),
("consonant in arabic script","baƙi","n.m. (pl. babbaƙu)",25),
("guest, stranger, visitor","baƙo","n.m. (f. baƙuwa, pl. baƙi)",25),
("foreign element","baƙo","n.m. (f. baƙuwa, pl. baƙi)",25),
("measles","baƙon dauro","n.m.",25),
("be a guest or visitor of","baƙuntà","v.t. (ci/ce)",25),
("reach puberty","balagà","v.i.",25),
("eloquent use of language","balagà","n.f.",25),
("rhetoric (subject for study)","balagà","n.f.",25),
("calamity, great misfortune","bala'i","n.m.",25),
("balance (in accounting)","balàs","n.m.",25),
("flickering or fluttering","bal-bal","id.",25),
("make a bright fire","balbàla","v.t.",25),
("cattle egret","bâlbelà","n.f. (pl. bàlbèlu)",25),
("adult","balìgi","n.m. (f. balìga, pl. bàlìgai)",25),
("how much less (after neg. sentence)","bàlle","(particle)",25),
("how much more (after affirmative sentence)","bàlle","(particle)",25),
("different, distinct","bambam","adv.",25),
("difference, distinctness","bambanci","n.m.",25),
("raising the voice in anger","bàmbani","n.m.",25),
("differentiate, separate, distinguish","bambànta","v.t.",25),
("differ, be different","bàmbantà","v.i.",25),
("how strange, abnormal!","bàmbaràkwai","excl.",25),
("palm wine","bâmmi","n.m.",25),
("i did not","bàn","(contr. of neg. marker bà and pro. in)",25),
("form of ²ba used in compounds (e.g. showing respect, annoyance, saying goodbye, calming down, frightening)","ban","(verbal prefix)",25),
("this year","bana","n.f. and adv.",25),
("age (esp. of cattle)","bana","n.f. and adv.",25),
("christian","bànasarè","n.m. (f. bànasariya, pl. nàsarà, nàsàru)",25),
("bayonet","banati","n.m.",25),
("drying meat or fish over fire","banda","n.f.",25),
("apart from, excluding, besides","bandà","prep.",25),
("without","bandà","prep.",25),
("bandage","bandejì","n.m.",25),
("bolt of cloth","bandir","n.m.",25),
("latrine","bân daki","n.m.",25),
("small bowl-shaped drum which is beaten with the fingers (usu. played for traditional rulers)","bànga","n.f. (pl. bangunà)",25),
("crowding around s.o.","bàngà-bangà","n.m.",25),
("push rudely and forcefully aside","bangàje","v.t.",25),
("wall (of hut or room)","bango","n.m. (pl. bangwàye)",25),
("cover of book","bango","n.m. (pl. bangwàye)",25),
("collide","bànka","v.t. (i/e)",25),
("drink much of","bànka","v.t. (i/e)",25),
("patch clothing","bànka","v.t. (i/e)",25),
("set big fire to","bankà","v.t. (with i.o.)",25),
("lift up edge of mat, cloth, etc.","bankàda","v.t.",25),
("reveal","bankàda","v.t.",25),
("push aside","bankàde","v.t.",25),
("knock down or aside with great force","bankè","v.t.",25),
("bank, coffers","banki","n.m. (pl. bankunà)",25),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 25: {len(entries)} entries\n")

print("wrote", len(entries))
