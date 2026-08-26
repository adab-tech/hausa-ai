import json

entries = [
("gambian oribi (gazelle)","batsiyà","n.f. (pl. batsiyoyi)",27),
("small leather or metal container for tobacco, snuff, etc.","battà","n.f. (pl. battoci)",27),
("speech, conversation","batu","n.m. (pl. batutuwà)",27),
("matter, affair","batu","n.m. (pl. batutuwà)",27),
("motion, proposal","batu","n.m. (pl. batutuwà)",27),
("european","baturè","n.m. (f. baturìya, pl. turàwa)",27),
("senior government official","baturè","n.m. (f. baturìya, pl. turàwa)",27),
("voucher","baucà","n.f. (pl. baucoci)",27),
("swerve, dodge aside","baudè","v.i.",27),
("go astray (in morals)","baudè","v.i.",27),
("evasiveness, being a dodger","baudiya","n.f.",27),
("worship","bauta","v.t. (with i.o.)",27),
("serve faithfully, work hard for","bauta","v.t. (with i.o.)",27),
("slavery, servitude","bauta","n.f.",27),
("worship","bauta","n.f.",27),
("enslave","bautar","v.t. (dà)",27),
("slave","bawà","n.m. (f. baiwa, pl. bayi)",27),
("urine","bawàli","n.m.",27),
("valve","bawùl","n.m.",27),
("back","baya","n.m.",27),
("behind, backwards","bayà","adv.",27),
("anaemia","bayâmma","n.f.",27),
("after","bayan","prep.",27),
("behind","bayan","prep.",27),
("explanation","bàyani","n.m. (pl. bàyànai)",27),
("give","bayar","v.t. (dà) (= ba dà before d.o.)",27),
("betray s.o.","bayar","v.t. (dà) (= ba dà before d.o.)",27),
("giving things to one another, relieving one another in a task","bàyayyà","n.f.",27),
("copulation by horses","bàye","n.m.",27),
("explain","bayyàna","v.t.",27),
("reveal, expose","bayyàna","v.t.",27),
("be revealed, appear","bàyyanà","v.i.",27),
("fringed leather apron or loincloth worn during dancing","bàza","n.f.",27),
("spread (out) sth.","bazà","v.t.",27),
("bolt, run away","bazamà","v.i.",27),
("hot season just before the rains","bazara","n.f.",27),
("flapping or flowing of ragged clothes or of a gown in the wind","bazar-bazar","id.",27),
("surprise","bà zàta","n.f.",27),
("person who is no longer married but still marriageable","bàzawàri","n.m. (f. bàzawàra, pl. zawarawa)",27),
("become or pretend to be deaf and dumb","bebànce","v.i.",27),
("deaf mute","bebe","n.m. (f. bebiya, pl. bebàye)",27),
("flower bed","bedi","n.m.",27),
("longing, yearning","bège","n.m.",27),
("bugle","begìlà","n.m. (pl. begìloli)",27),
("porcupine","beguwa","n.f.",27),
("belt","bêl","n.m.",27),
("uvula","bèli, bèlu","n.m.",27),
("bail","beli","n.m.",27),
("bench","benci","n.m. (pl. bencunà)",27),
("upstairs, upper storey","bene","n.m. (pl. benàye)",27),
("girl whose breasts are not yet formed and who is not marriageable","berà","n.f. (pl. berori)",27),
("a coarse salt","bezà","n.f.",27),
("follow, come next after","bi","v.t.",27),
("obey","bi","v.t.",27),
("travel by way of","bi","v.t.",27),
("be owed something","bi","v.t.",27),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 27: {len(entries)} entries\n")

print("wrote", len(entries))
