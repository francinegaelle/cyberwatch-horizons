import os, json, re, hashlib, smtplib, ssl, html
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests, feedparser

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONFIG = json.loads((ROOT/"config/watch_config.json").read_text(encoding="utf-8"))
SOURCES = json.loads((ROOT/"config/sources.json").read_text(encoding="utf-8"))
DATA = DOCS/"data.json"
STATE = DOCS/"state.json"
HISTORY = DOCS/"kpi_history.json"

def load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default
def save(path, obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def now(): return datetime.now(timezone.utc)
def iso(dt):
    if not dt: dt=now()
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
def uid(*parts): return hashlib.sha256("|".join(map(str,parts)).encode()).hexdigest()[:28]
def clean(s): return re.sub(r"\s+"," ", re.sub(r"<[^>]+>"," ", html.unescape(s or ""))).strip()
def parse_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z","+00:00"))
    except: return now()
def source_quality(src):
    return round(.30*src["author_expertise"]+.40*src["institution_reputation"]+.30*src["editorial_rigor"],1)

HORIZONS=CONFIG["horizons"]

def objective_match(text):
    t=text.lower()
    scores={}
    for h,c in HORIZONS.items():
        scores[h]=sum(1 for kw in c["keywords"] if kw.lower() in t)
    best=max(scores,key=scores.get)
    return best,scores[best],scores

def category(text):
    t=text.lower()
    rules=[
      ("IAM / Zero Trust",r"\b(iam|identity|zero trust|mfa|sso|oauth|oidc|entra|passkey|fido|privileged access)\b"),
      ("IA / cybersécurité",r"\b(artificial intelligence|generative ai|genai|llm|large language model|machine learning|adversarial|agentic ai|ai security)\b"),
      ("Pannes / Cloud / SaaS",r"\b(outage|degraded|service disruption|unavailable|incident|cloud|saas)\b"),
      ("Cyberattaque",r"\b(ransomware|phishing|malware|ddos|breach|compromis|compromise|cyber attack)\b"),
      ("Vulnérabilité / correctif",r"\b(cve-\d|vulnerab|patch|security update|exploit|zero[- ]day|kev)\b"),
      ("DevOps / Supply chain",r"\b(devops|supply chain|github|gitlab|ci/cd|package|dependency)\b"),
      ("Réglementation / normes",r"\b(regulation|directive|nis2|dora|iso 27001|standard|compliance)\b"),
    ]
    for n,p in rules:
        if re.search(p,t): return n
    return "Nouveauté IT / technologie"

def severity(title,desc,source):
    t=f"{title} {desc}".lower()
    if source=="CISA KEV" or re.search(r"\b(actively exploited|known exploited|zero[- ]day|critical outage|major outage|ransomware attack)\b",t):
        return "P1"
    if re.search(r"\b(critical vulnerability|cvss 9|cvss 10|exploit public|security incident|data breach|service disruption|outage)\b",t):
        return "P2"
    if re.search(r"\b(cve-|vulnerab|patch|advisory|security update|degraded|malware|phishing)\b",t):
        return "P3"
    return "P4"

def make_event(src,title,url,published,desc="",raw_id=None):
    full=f"{title} {desc}"
    h,score,scores=objective_match(full)
    cat=category(full)
    pri=severity(title,desc,src["name"])
    # World-wide operational incidents stay H1 unless they clearly belong to H2/H3.
    if score==0 or cat in ("Pannes / Cloud / SaaS","Cyberattaque","Vulnérabilité / correctif"):
        h="H1"
    relevance = min(100, 45 + score*15 + (20 if pri in ("P1","P2") else 0))
    weak = (h in ("H2","H3") and pri in ("P3","P4"))
    actionable = pri in ("P1","P2","P3") and cat in ("Pannes / Cloud / SaaS","Cyberattaque","Vulnérabilité / correctif","IAM / Zero Trust")
    return {
      "id":raw_id or uid(src["id"],title,url),
      "title":clean(title),"description":clean(desc)[:1800],
      "source":src["name"],"source_id":src["id"],"source_url":src["url"],"url":url,
      "language":src["language"],"region":src["region"],"primary_source":src["primary"],
      "source_quality":source_quality(src),
      "published":iso(published),"detected":iso(now()),
      "priority":pri,"horizon":h,"category":cat,
      "relevance_score":relevance,"weak_signal":weak,"actionable":actionable,
      "objective_scores":scores
    }

def feed_date(e):
    for k in ("published_parsed","updated_parsed"):
        p=e.get(k)
        if p:
            return datetime(*p[:6],tzinfo=timezone.utc)
    return now()

def fetch_feed(src,events):
    d=feedparser.parse(src["url"])
    if getattr(d,"bozo",False) and not d.entries: raise RuntimeError(str(getattr(d,"bozo_exception","feed error")))
    cutoff=now()-timedelta(days=10)
    for e in d.entries[:120]:
        dt=feed_date(e)
        if dt<cutoff: continue
        events.append(make_event(src,e.get("title","Untitled"),e.get("link",src["url"]),dt,e.get("summary","")))

def fetch_cisa(src,events):
    r=requests.get(src["url"],timeout=30,headers={"User-Agent":"CyberWatchHorizons/2.0"})
    r.raise_for_status(); j=r.json(); cutoff=now()-timedelta(days=60)
    for v in j.get("vulnerabilities",[]):
        dt=parse_dt(v.get("dateAdded",""))
        if dt<cutoff: continue
        ev=make_event(src,f'{v.get("cveID","CVE")} — {v.get("vulnerabilityName","Known exploited vulnerability")}',
                      "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",dt,
                      v.get("shortDescription",""),"kev-"+v.get("cveID",""))
        ev["priority"]="P1"; ev["horizon"]="H1"; ev["category"]="Vulnérabilité / correctif"; ev["actionable"]=True; ev["relevance_score"]=100
        events.append(ev)

def fetch_nvd(src,events):
    end=now(); start=end-timedelta(hours=24)
    params={"pubStartDate":start.strftime("%Y-%m-%dT%H:%M:%S.000"),"pubEndDate":end.strftime("%Y-%m-%dT%H:%M:%S.000"),"resultsPerPage":100}
    headers={"User-Agent":"CyberWatchHorizons/2.0"}
    if os.getenv("NVD_API_KEY"): headers["apiKey"]=os.getenv("NVD_API_KEY")
    r=requests.get(src["url"],params=params,headers=headers,timeout=40); r.raise_for_status()
    for x in r.json().get("vulnerabilities",[]):
        c=x.get("cve",{}); cid=c.get("id")
        if not cid: continue
        desc=next((d.get("value","") for d in c.get("descriptions",[]) if d.get("lang")=="en"),cid)
        pub=parse_dt(c.get("published",""))
        sev=""
        for k in ("cvssMetricV40","cvssMetricV31","cvssMetricV30"):
            if c.get("metrics",{}).get(k):
                dat=c["metrics"][k][0].get("cvssData",{})
                sev=f'CVSS {dat.get("baseScore","")} {dat.get("baseSeverity","")}'
                break
        events.append(make_event(src,f"{cid} — {desc[:260]}",f"https://nvd.nist.gov/vuln/detail/{cid}",pub,sev+" "+desc,"nvd-"+cid))

def extract_cve(text):
    return set(re.findall(r"CVE-\d{4}-\d{4,7}",text.upper()))
def add_cross_check(events):
    by_cve={}
    for e in events:
        cvs=extract_cve(e["title"]+" "+e["description"])
        e["cves"]=sorted(cvs)
        for c in cvs: by_cve.setdefault(c,set()).add(e["source"])
    for e in events:
        srcs=set()
        for c in e["cves"]: srcs |= by_cve.get(c,set())
        e["cross_check_count"]=len(srcs) if srcs else 1
        e["cross_checked"]=e["cross_check_count"]>=2

def metrics(items):
    out={}
    for h in ("H1","H2","H3"):
        arr=[x for x in items if x["horizon"]==h]
        if not arr:
            out[h]={"count":0}; continue
        relevant=[x for x in arr if x["relevance_score"]>=60]
        sq=sum(x["source_quality"] for x in arr)/len(arr)
        cross=[x for x in arr if x["priority"] in ("P1","P2")]
        cr=(100*sum(1 for x in cross if x["cross_checked"])/len(cross)) if cross else 100
        action=100*sum(1 for x in arr if x["actionable"])/len(arr)
        orig=100*sum(1 for x in arr if x["primary_source"])/len(arr)
        weak=sum(1 for x in arr if x["weak_signal"])
        ttri=[]
        for x in arr:
            try: ttri.append(max(0,(parse_dt(x["detected"])-parse_dt(x["published"])).total_seconds()/60))
            except: pass
        out[h]={
          "count":len(arr),
          "relevance_rate":round(100*len(relevant)/len(arr),1),
          "source_quality_score":round(sq,1),
          "cross_check_rate":round(cr,1),
          "actionable_rate":round(action,1),
          "original_language_rate":round(orig,1),
          "weak_signals_month":weak,
          "time_to_receive_minutes":round(sum(ttri)/len(ttri),1) if ttri else None,
          "hypotheses_quarter":0,
          "scenarios_quarter":0
        }
    return out

def kpi_status(h,m):
    targets=HORIZONS[h]["kpi_targets"]; rows=[]
    labels={
      "relevance_rate":"Pertinence de la veille","source_quality_score":"Qualité des sources",
      "cross_check_rate":"Taux de recoupement","time_to_receive_minutes":"Time to Receive Information",
      "actionable_rate":"Informations actionnables","original_language_rate":"Sources en langue originale",
      "weak_signals_month":"Signaux faibles détectés","hypotheses_quarter":"Hypothèses transformées",
      "scenarios_quarter":"Scénarios H3 mis à jour"
    }
    lower_better={"time_to_receive_minutes"}
    for k,target in targets.items():
        val=m.get(k)
        ok=False if val is None else (val<=target if k in lower_better else val>=target)
        rows.append({"key":k,"name":labels[k],"value":val,"target":target,"status":"OK" if ok else "ALERTE","action":HORIZONS[h]["sla_action"]})
    return rows

def send_mail(subject,body):
    host=os.getenv("SMTP_HOST"); port=int(os.getenv("SMTP_PORT","587")); user=os.getenv("SMTP_USER"); pw=os.getenv("SMTP_PASSWORD"); recipient=os.getenv("ALERT_EMAIL")
    if not all([host,user,pw,recipient]): return False
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=user; msg["To"]=recipient; msg.set_content(body)
    ctx=ssl.create_default_context()
    with smtplib.SMTP(host,port,timeout=30) as s:
        s.starttls(context=ctx); s.login(user,pw); s.send_message(msg)
    return True

def immediate_alerts(new):
    imp=[e for e in new if e["priority"] in CONFIG["notifications"]["email"]["immediate_priorities"]]
    if not imp: return
    lines=["Nouvelles alertes CyberWatch :",""]
    for e in imp[:40]:
        lines += [f'{e["priority"]} | {e["horizon"]} | {e["category"]}',e["title"],f'Source: {e["source"]}',f'Publié: {e["published"]}',f'Détecté: {e["detected"]}',f'Qualité source: {e["source_quality"]}/100',f'Recoupement: {e["cross_check_count"]} source(s)',f'Lien: {e["url"]}',""]
    send_mail(f'[CyberWatch] {len(imp)} nouvelle(s) alerte(s) P1/P2',"\n".join(lines))

def digest(items,horizon,subject):
    arr=[e for e in items if e["horizon"]==horizon][:60]
    if not arr:return
    lines=[subject,""]
    for e in arr[:30]:
        lines += [f'{e["priority"]} | {e["category"]} | {e["published"][:10]}',e["title"],f'{e["source"]} — {e["url"]}',""]
    send_mail(subject,"\n".join(lines))

def main():
    old=load(DATA,{"items":[]}); state=load(STATE,{"seen":[]}); seen=set(state.get("seen",[]))
    collected=[]; errors=[]
    for src in SOURCES:
        try:
            if src["id"]=="cisa-kev": fetch_cisa(src,collected)
            elif src["id"]=="nvd": fetch_nvd(src,collected)
            else: fetch_feed(src,collected)
        except Exception as e: errors.append(f'{src["name"]}: {e!r}')
    uniq={e["id"]:e for e in collected}; collected=list(uniq.values())
    add_cross_check(collected)
    new=[e for e in collected if e["id"] not in seen]
    for e in new: seen.add(e["id"])
    merged={e["id"]:e for e in old.get("items",[])}
    for e in collected: merged[e["id"]]=e
    items=list(merged.values()); items.sort(key=lambda x:x["published"],reverse=True); items=items[:2000]
    add_cross_check(items)
    met=metrics(items); kpis={h:kpi_status(h,met[h]) for h in ("H1","H2","H3")}
    data={"generated_at":iso(now()),"errors":errors,"config":CONFIG,"metrics":met,"kpis":kpis,"items":items}
    save(DATA,data); save(STATE,{"seen":list(seen)[-10000:]})
    hist=load(HISTORY,[])
    day=now().strftime("%Y-%m-%d")
    snapshot={"date":day,"metrics":met}
    hist=[x for x in hist if x.get("date")!=day]+[snapshot]
    save(HISTORY,hist[-365:])
    immediate_alerts(new)
    # scheduled digests use environment flags from dedicated workflows
    if os.getenv("SEND_H2_DIGEST")=="1": digest(items,"H2","[CyberWatch H2] Synthèse hebdomadaire IAM / Zero Trust")
    if os.getenv("SEND_H3_DIGEST")=="1": digest(items,"H3","[CyberWatch H3] Revue mensuelle IA en cybersécurité")
    print(f"{len(new)} new; {len(items)} stored; errors={len(errors)}")
if __name__=="__main__": main()
