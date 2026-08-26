import json

entries = [
("afterwards, later","bisani","adv. (with dàgà)",29),
("good news","bisharà","n.f.",29),
("tree","bishiyà","n.f. (pl. bishiyoyi)",29),
("used when inviting s.o. to begin a meal, come into a room, sit down, etc.","bismilla","excl.",29),
("said by s.o. about to begin eating, start work, etc.","bismillahi","excl.",29),
("biscuit","biskît","n.m.",29),
("used in bakin ~ police beat","bît","n.m.",29),
("reading again through a text","bità","n.f.",29),
("veterinary","bitinarè","n.m.",29),
("teach or study by reading","biyà","v.t.",29),
("go via, pass by, call at","biyà","v.i.",29),
("pay","biya","v.t.",29),
("fulfil","biya","v.t.",29),
("five","biyar","n.f. and adj.",29),
("obedience","biyayyà","n.f.",29),
("two","biyu","n.f. and adj.",29),
("double","biyu","n.f. and adj.",29),
("double loss","biyu biyu","n.m.",29),
("a biting fly","bobuwa","n.f.",29),
("body of a lorry","bodi","n.m.",29),
("native doctor, wizard","boka","n.m. (f. bokanyà, pl. bokàye)",29),
("bucket","bokiti","n.m. (pl. bòkitai)",29),
("western education","bokò","n.m.",29),
("hausa written in roman script","bokò","n.m.",29),
("mock arrangement (e.g. army manoeuvres)","bokò","n.m.",29),
("adulteration, fraud, trick","bokò","n.m.",29),
("buckle","bokùl","n.m. (pl. bokuloli)",29),
("refuse pit","bolà","n.f. (pl. bololi)",29),
("bomb","bôm","n.m.",29),
("a less-favoured wife","borà","n.f.",29),
("rebelliousness, disobedience","bôrè","n.m.",29),
("the cult of spirit possession","bori","n.m.",29),
("a follower of the cult (dan bori)","bori","n.m.",29),
("used in 'ya'yan ~ ball bearings","boris","n.m.",29),
("intentionally spinning car or motorcycle around in soft sand","boris","n.m.",29),
("blister","bororò","n.m.",29),
("bus","bôs","n.f. (pl. bôs-bôs)",29),
("house-boy, steward","boyi","n.m. (pl. boyi-boyi)",29),
("mouth disease with rotting of teeth, usu. in children","bubù","n.m.",29),
("dry, windy, harmattan haze","budà","n.f.",29),
("a large, edible toad","bùduddùgi","n.m. (pl. bùdùddùgai)",29),
("unmarried girl of marriageable age","budurwa","n.f. (pl. budurwoyi)",29),
("girl-friend (of a boy)","budurwa","n.f. (pl. budurwoyi)",29),
("open slightly","buɗà","v.t.",29),
("disclose","buɗà","v.t.",29),
("taking the first meal of the day during ramadan","buɗà-bàki","n.m.",29),
("open","buɗè","v.t.",29),
("new opportunities (in trade), progress (in education)","buɗi","n.m.",29),
("opening a water inlet in an irrigated plot","buɗi","n.m.",29),
("beat, strike, hit, thrash","bùga","v.t. (i/e) (vn. bugù)",29),
("beat, strike sth. (e.g. fire a gun, pump up a tyre, publish a book, set off an explosive, send a telegram or make a call)","bugà","v.t.",29),
("be thoroughly beaten","bugu","v.i.",29),
("be drunk","bugu","v.i.",29),
("moreover, in addition","bugù dà kari","conj.",29),
("traditional-style trousers with very wide crotch","bujè","n.m.",29),
("sack, bag","bùhu","n.m. (pl. buhunhunà)",29),
("compass for drawing, drafting","bùkari","n.m.",29),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 29: {len(entries)} entries (bukata continues on page 30)\n")

print("wrote", len(entries))
