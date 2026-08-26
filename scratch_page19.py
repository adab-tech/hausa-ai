import json

entries = [
("gunpowder","albarushi","n.m.",19),
("onion(s)","albasà","n.f.",19),
("regular weekly or monthly salary, wages","albashi","n.m.",19),
("good news","albishir","n.m.",19),
("mule","alfadari","n.m. (f. alfadara, pl. alfadarai)",19),
("pride, boastfulness","alfahari","n.m.",19),
("favour, generosity, kindness, leniency","alfarma","n.f.",19),
("nobility, high rank or birth","alfarma","n.f.",19),
("obscene or abusive language","alfasha","n.f.",19),
("dawn, half-light at dawn","alfijir","n.m.",19),
("high-pitched musical instrument, played by blowing on a double-reed mouthpiece","algaità","n.f. (pl. algaitu)",19),
("sackcloth","algàrarà","n.f.",19),
("maroon (colour)","algàshi","n. and adj. (f. algàsa, pl. algàsai)",19),
("form of fraud in selling","algùs","n.m.",19),
("one who has made the pilgrimage to mecca","alhaji","n.m. (f. alhajiya, pl. alhazai)",19),
("guilt, sin, offence","alhaki","n.m.",19),
("obviously, as a matter of fact, certainly","alhali","conj.",19),
("praise be to god!, god be praised!","alhamdù lillahi","excl.",19),
("thursday","Alhamis","n.f.",19),
("kindness, generosity, gift, good deed","alheri","n.m.",19),
("material wealth","alheri","n.m.",19),
("meditation about something sad","alhini","n.m.",19),
("senegal hoopoe (bird)","alhudahudà","n.m.",19),
("one thousand (esp. used in dates)","alif","n.f.",19),
("algebra","aljabarà","n.f.",19),
("genie, jinn, good or bad spirit","aljan, aljàni","n.m. (f. aljàna, pl. aljànu)",19),
("paradise, heavenly kingdom","aljannà","n.f.",19),
("pocket","aljihu","n.m. (pl. aljihunà)",19),
("value, worth, quality","alkadàri","n.m.",19),
("game of somersaulting in water","alkafùra","n.f.",19),
("sweet fried delicacy made from wheat flour","alkaki","n.m.",19),
("wheat","alkàmà","n.f.",19),
("unwalled town or urban area","alkaryà","n.f. (pl. alkaryu)",19),
("promise","alkawàri","n.m. (pl. alkawurà)",19),
("reliability","alkawàri","n.m. (pl. alkawurà)",19),
("burnous, usu. worn by emirs, chiefs, and sometimes malams","alkyabbà","n.f. (pl. alkyabbu)",19),
("pen","alƙalami","n.m. (pl. alƙalumà)",19),
("numerical figure","alƙalami","n.m. (pl. alƙalumà)",19),
("muslim judge, judge","alƙali","n.m. (pl. alƙalai)",19),
("the koran","Alƙur'ani","n.m.",19),
("fetish, deity","allà","n.m. (pl. alloli)",19),
("eagerness","allà-allà","n.f.",19),
("god","Allàh","n.m.",19),
("expression of denial, negation, complete refusal","allambaram, allambûr","excl.",19),
("chalk","àlli","n.m.",19),
("fine powder ground from animal bone used by women in spinning thread","àlli","n.m.",19),
("wooden writing board used for practising arabic script","àllo","n.m. (pl. allunà)",19),
("blackboard, slate","àllo","n.m. (pl. allunà)",19),
("needle","allurà","n.f. (pl. allùrai)",19),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 19: {len(entries)} entries (allura sense 2 continues on page 20)\n")

print("wrote", len(entries))
