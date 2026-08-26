import json, io

entries = [
("large lidded basket made of grass","àdùdù","n.m. (pl. àdùdai)",17),
("desert date tree or its fruit","àduwà","n.f. (pl. àduwoyi)",17),
("indicates surprise or sudden recollection","af","excl.",17),
("throw (grain, groundnuts, etc.) into mouth without touching it","àfà","v.t. (vn. àfì)",17),
("small handful of sth. (e.g. groundnuts or tobacco) thrown into the mouth","àfì","n.m.",17),
("appeal (legal)","àfil","n.m.",17),
("type of cheap cotton thread","àfitatu","n.m.",17),
("april","Afrilù","n.m.",17),
("be eager, anxious","àfù","v.i.",17),
("possessing a lot of sth.","àga","n.f.",17),
("becoming well known","àga","n.f.",17),
("plantain(s)","àgadè","n.m.",17),
("help, assistance, rescue, relief","agàji","n.m.",17),
("smallpox","àgana","n.f.",17),
("tendon in back part of ankle","àgara","n.f.",17),
("help, assist, come to rescue of s.o.","àgazà","v.t. (jj/je) (vn. agàji)",17),
("clock, watch","àgogo","n.m. (pl. àgògai, agogunà)",17),
("step-child (child of man's wife by her former husband)","àgòlà","n.m. (f. agoliya, pl. àgòlai)",17),
("melon seeds used for making soup","àgushi","n.m.",17),
("august","Agustà","n.m.",17),
("duck","àgwàgwa","n.f. (pl. àgwàgi)",17),
("type of large riga with round neck and slit-like embroidery design","agwaja","n.f.",17),
("expression of pleasant joking between women, usu. followed by ayyururui","àhâyye","excl.",17),
("used in cittar ~ ginger root","àhò","n.m.",17),
("one and a half pence in old nigerian currency","ahù","n.m.",17),
("leniency, pardon, mercy","àhuwà","n.f.",17),
("greeting used by women on entering s.o. else's house or coming upon a group of people","àhuwo","excl.",17),
("oh yes!, aha!, of course!, oh, i see!","âi","excl.",17),
("well yes, but..., mind you... (used during long discussions)","ai","excl.",17),
("blame s.o.","aibàta","v.t.",17),
("fault, blemish","aibù, aibi","n.m. (pl. aibobi)",17),
("iodine","àidîn","n.m.",17),
("send s.o. (on errand)","àika","v.t. (i/e) (vn. aikì)",17),
("send sth.","aikà","v.t. (usu. with dà)",17),
("work sth. out completely","aikàce","v.t.",17),
("do, perform, act","aikàta","v.t.",17),
("small job given out to s.o. for wages (usu. farm work by men or grinding of corn by women)","àikàtau","n.m.",17),
("errand","àike","n.m. (pl. àikè-àikè)",17),
("work, job, duty","aikì","n.m. (pl. ayyukà, àikàce-àikàce)",17),
("activity, act","aikì","n.m. (pl. ayyukà, àikàce-àikàce)",17),
("essence, reality","ainihi","n.m.",17),
("very, very much, truly","ainùn","adv.",17),
("fixed period of time, deadline, time limit","ajàli","n.m.",17),
("appointed end of one's life, fate, cause of death","ajàli","n.m.",17),
("hausa written in arabic script","ajàmì","n.m.",17),
("agenda","ajandà","n.f. (pl. ajàndu)",17),
("class or form (in school)","ajì","n.m. (pl. azuzuwà, ajujuwà)",17),
("class, category, group","ajì","n.m. (pl. azuzuwà, ajujuwà)",17),
("anything stored or deposited for safekeeping","ajìyà","n.f. (pl. àjìyè-àjìyè)",17),
("a traditional title","ajìyà","n.m.",17),
("put down or away","ajìye","v.t.",17),
("store, save, put in safe-keeping, deposit","ajìye","v.t.",17),
("man with his human weakness","ajìzi","n.m. (f. ajìza, pl. àjìzai)",17),
]

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\ha_en_pairs_chunk2.jsonl", "a", encoding="utf-8") as f:
    for en, ha, ctx, pg in entries:
        obj = {"source_en": en, "target_ha": ha, "context": ctx, "provenance": "newman_1977", "page": pg}
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

with open(r"C:\Users\Adamu\Desktop\Hausa AI\data\processed\newman_1977\progress_chunk2.txt", "a", encoding="utf-8") as f:
    f.write(f"page 17: {len(entries)} entries\n")

print("wrote", len(entries))
