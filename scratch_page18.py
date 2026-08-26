import json

entries = [
("they, one, it","àkà","impers. pro. (rel. past tense subj.)",18),
("continually, regularly, repeatedly","à kâi à kâi","adv.",18),
("fingernail, claw, talon","àkaifa","n.f. (pl. àkaifu)",18),
("lead-rope of camel","àkàlà","n.f. (pl. àkàlai)",18),
("they, one, it","àkàn","impers. pro. (hab. tense subj.)",18),
("accountant","àkantà","n.m. (pl. akantoci)",18),
("opposite or reverse of sth.","àkàsi","n.m.",18),
("shiny black horse","àkàwàl, àkàwàli","n.m. (f. akàwàla, pl. àkàwàlai)",18),
("smooth black-skinned person","àkàwàl, àkàwàli","n.m. (f. akàwàla, pl. àkàwàlai)",18),
("clerk","àkàwù","n.m. (pl. akawunà, àkàwù-àkàwù)",18),
("they, one, it","àkè","impers. pro. (rel. cont. tense subj.)",18),
("grey-coloured baft (cloth)","àkoko","n.m.",18),
("parrot","àkù","n.m. or f.",18),
("warning that if the addressee repeats the stated action, they alone will be to blame","àkul","(idiom)",18),
("stop that!","àkul","excl.",18),
("don't... (followed by rel. past tense verb)","àkul","excl.",18),
("coop for keeping fowl","àkurki","n.m. (pl. àkùrkai)",18),
("black wooden bowl for food","àkùshi","n.m. (pl. akùsà)",18),
("goat","àkùyà","n.f. (pl. awaki, àwàkai)",18),
("there is, there are","àkwai","(existential particle)",18),
("box, crate, trunk","àkwàtì","n.m. (pl. akwatunà)",18),
("at least","àƙallà","adv.",18),
("leather wallet or purse","àlàbè","n.m. (pl. àlàbai)",18),
("yam or cassava flour","àlàbo","n.m.",18),
("custom, habit, tradition","al'adà","n.f. (pl. al'àdu)",18),
("menstruation","al'adà","n.f. (pl. al'àdu)",18),
("pig, boar","àlàdè","n.m. (pl. àlàdai, àlàdu)",18),
("surprise, wonder, miracle","al'ajàbi","n.m. (pl. al'ajubà)",18),
("continually pestering or bothering s.o.","alaƙaƙài","n.m.",18),
("food made of beans mashed with palm oil and spices and wrapped in leaves or tinned","àlàlà","n.m.",18),
("sign, symbol","alamà","n.f. (pl. alamomi, àlàmu)",18),
("indication, trace, piece of evidence","alamà","n.f. (pl. alamomi, àlàmu)",18),
("road sign","alamà","n.f. (pl. alamomi, àlàmu)",18),
("matter, business, affair","al'amari","n.m. (pl. al'amurà)",18),
("mark or indicate sth.","alamta","v.t.",18),
("be marked or indicated","alamtà","v.i.",18),
("the heavens (spiritual)","Al'arshi","n.m.",18),
("luxury item","alatù","n.m.",18),
("private parts of body, esp. male","al'aurà","n.f.",18),
("any sweet made from sugar, honey, and/or fruit","alawà","n.f.",18),
("white calico cloth, shirting material","alawayyò","n.m.",18),
("monetary allowance","alawùs","n.m.",18),
("allowance of space, room to move","alawùs","n.m.",18),
("allowance of time","alawùs","n.m.",18),
("oil from palm kernel","alayyadi","n.m.",18),
("spinach","alayyaho","n.m.",18),
("leprosy","albaràs","n.f.",18),
("blessing, prosperity, grace, gift from god","albarkà","n.f.",18),
("no! (in bargaining, used by seller to reject an offer)","albarkà","excl.",18),
("good fortune or benefit enjoyed through s.o. else's grace or influence","albarkàci","n.m.",18),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 18: {len(entries)} entries\n")

print("wrote", len(entries))
