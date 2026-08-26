import json

entries = [
("tenth of a shilling, a penny in old nigerian currency","anini","n.m. (pl. aninai)",21),
("button","anini","n.m. (pl. aninai)",21),
("military officer's stars or ribbons indicating rank","anini","n.m. (pl. aninai)",21),
("determination, zeal, fervour","àniyà","n.f.",21),
("goal","àniyà","n.f.",21),
("evil intention (usu. in curse)","àniyà","n.f.",21),
("take notice, realize, pay attention","ankarà","v.i.",21),
("handcuffs","ankwà","n.f.",21),
("prophet","annabi","n.m. (pl. annabawa)",21),
("the prophet muhammad","Annàbi","n.m. (proper name usage)",21),
("mischief-maker","annàmimi","n.m. (f. annàmimiya, pl. annàmimai)",21),
("joyous feeling, pleasure, merriment","annàshuwa","n.f.",21),
("epidemic, plague","annoba","n.f.",21),
("brightness, light","annuri","n.m.",21),
("cheerfulness","annuri","n.m.",21),
("used to introduce questions of surprise or doubt","anya","(interrog. particle)",21),
("damn it!","af","excl.",21),
("borrow sth. which itself will be returned","ara","v.t. (i/e) (vn. aro)",21),
("lend sth. to s.o.","arà","v.t. (with i.o.)",21),
("thunder, clap of thunder","aradù","n.f.",21),
("fine manufactured thread","arafiyà","n.f.",21),
("cheapness, easiness","arahà","n.f.",21),
("meeting s.o. coincidentally","arangamà","n.f.",21),
("clashing together (e.g. of armies)","arangamà","n.f.",21),
("used in kayan ~ breakable goods (glass, porcelain)","aras","id.",21),
("verbal coincidence, saying what s.o. else has said","arashi","n.m.",21),
("compensation for wounding s.o.","arashi","n.m.",21),
("four thousand","arbà","n.f. and adj.",21),
("used in yi ~ meet face to face unexpectedly","arbà","n.f.",21),
("forty","arba'in","n.f. and adj.",21),
("forty day period after woman gives birth","arba'in","n.f. and adj.",21),
("four hundred","arbaminyà","n.f. and adj.",21),
("north, northern","àrewa","n.f.",21),
("north of","àrewacin","prep.",21),
("arrears, back-payment","arjiyà","n.f.",21),
("sth. very satisfying","armashi","n.m.",21),
("pagan, heathen","arnè","n.m. (f. arniya, pl. arna)",21),
("loan","aro","n.m.",21),
("long, long ago","aru-aru","adv.",21),
("wealth, riches, prosperity","arziki","n.m. (pl. arzukà)",21),
("make s.o. wealthy, rich","arzuta","v.t.",21),
("be wealthy, rich","arzutà","v.i.",21),
("saturday","Asabar","n.f.",21),
("mat made of reeds","asabari","n.m. (pl. asàbàrai)",21),
("origins, stock, pedigree","asali","n.m. (pl. àsàlai)",21),
("cause, reasons","asali","n.m. (pl. àsàlai)",21),
("principles, foundation","asali","n.m. (pl. àsàlai)",21),
("chewing stick","asawaki","n.m.",21),
("cleaning one's teeth","asawaki","n.m.",21),
("sound used in driving away fowl","as-as","id.",21),
("aspirin","asfirin","n.m.",21),
("expression of regret","ash","excl.",21),
("special optional evening prayers after lisha during month of ramadan","asham","n.m.",21),
("match(es)","ashana","n.f.",21),
("abusive, obscene language","ashâr","n.f. (pl. asharè-asharè)",21),
("foul-mouthed, morally degraded person","asharafi","n.m. (f. asharafiya, pl. asharafai)",21),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 21: {len(entries)} entries (ashe continues on page 22)\n")

print("wrote", len(entries))
