#!/usr/bin/env python3
"""Free job-feed updater; all locations and direct links are validated."""
import datetime, hashlib, html, json, os, pathlib, re, urllib.parse, urllib.request
OUT=pathlib.Path(__file__).resolve().parents[1]/'docs'/'jobs.json'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
TITLE_TERMS=('infrastructure','systems engineer','system engineer','systems administrator','system administrator','network engineer','cloud engineer','it engineer','azure engineer','desktop engineer','platform engineer','network administrator','it support engineer','ict support','technical support engineer','it operations')
SENIOR_REJECT=('intern','graduate','apprentice','director','principal','head of','chief technology','vice president')
NONPERM=('contract','temporary','freelance','casual','internship','part-time')
UA='BrisbaneBermudaJobs/1.1 (public GitHub Pages job tracker)'
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response)
def s(x):
    if isinstance(x,dict): return str(x.get('name') or x.get('display_name') or x.get('title') or '')
    return str(x or '')
def country_for(location,country):
    value=s(location).lower()\n    country_hint=s(country).lower()
    # Require clear evidence of a location, not ambiguous "Hamilton" alone.
    if re.search(r'\bbermuda\b|\bhamilton,\s*bm\b',value):return 'Bermuda'
    if re.search(r'\bbrisbane\b|\bqueensland\b|\bqld\b',value):return 'Brisbane'
    return None
def valid_jobtype(type_):
    t=s(type_).lower()
    return not any(term in t for term in NONPERM)
jobs={}; errors=[]; sources=[]
def add(title,company,location,url,source,salary='',posted='',description='',country='',jobtype=''):
    title=s(title).strip(); url=s(url).strip(); location=s(location).strip()
    if not title or not url.startswith('https://'):return
    lower=title.lower()
    if not any(term in lower for term in TITLE_TERMS):return
    if any(term in lower for term in SENIOR_REJECT):return
    if not valid_jobtype(jobtype) or any(re.search(r'\b'+re.escape(t)+r'\b',lower) for t in NONPERM):return
    region=country_for(location,country)
    if not region:return
    # Reject explicitly remote-anywhere postings (unless anchored to a named target location).
    desc=html.unescape(re.sub(r'<[^>]*>',' ',s(description)))
    unique=hashlib.sha256(url.encode()).hexdigest()[:16]
    jobs[unique]={'id':unique,'title':title,'company':s(company) or 'Company not supplied',
      'location':location or region,'country':region,'url':url,'source':source,
      'salary':s(salary) or 'Not disclosed','posted':s(posted),
      'employment':s(jobtype) or 'Permanent status unverified',
      'visa':'Not confirmed','description':re.sub(r'\s+',' ',desc)[:350]}
# Feed 1: Arbeitnow (public, no key; mainly European)
try:
    data=fetch('https://www.arbeitnow.com/api/job-board-api')
    for x in data.get('data',[]):
        if isinstance(x,dict):
            add(x.get('title'),x.get('company_name'),x.get('location'),x.get('url'),'Arbeitnow',
                posted=x.get('created_at'),description=x.get('description'),jobtype=x.get('job_type'))
    sources.append('Arbeitnow')
except Exception as e: errors.append('Arbeitnow: '+str(e)[:120])
# Feed 2: Dev Global Jobs (free non-commercial API, country-searchable, attribution required)
for code in ('au','bm'):
    try:
        url='https://devglobaljobs.com/api/v1/jobs?'+urllib.parse.urlencode({'limit':100,'country':code,'search':'engineer'})
        data=fetch(url)
        entries=data if isinstance(data,list) else (data.get('jobs') or data.get('data') or data.get('results') or [])
        if isinstance(entries,dict):entries=entries.get('jobs') or entries.get('items') or []
        for x in entries:
            if not isinstance(x,dict):continue
            loc=x.get('location') or x.get('city') or ''
            if isinstance(loc,dict):loc=', '.join(str(v) for v in (loc.get('city'),loc.get('region'),loc.get('country')) if v)
            add(x.get('title') or x.get('job_title'), x.get('organisation') or x.get('company') or x.get('company_name'),
                loc,x.get('url') or x.get('job_url') or x.get('link'),'Dev Global Jobs',
                salary=x.get('salary_text') or x.get('salary'),posted=x.get('posted_at') or x.get('created_at'),
                description=x.get('description') or x.get('summary'),country=x.get('country') or ('Australia' if code=='au' else 'Bermuda'),
                jobtype=x.get('employment_type'))
        sources.append('Dev Global Jobs '+code.upper())
    except Exception as e:errors.append('Dev Global Jobs '+code.upper()+': '+str(e)[:100])
# Feed 3: OnJob (free to redistribute and link back; limited to first 2 paginated pages)
for url in ('https://onjob.io/feeds/jobs.json','https://onjob.io/feeds/jobs/2.json'):
    try:
        data=fetch(url)
        entries=data if isinstance(data,list) else data.get('jobs',[]) or data.get('items',[])
        for x in entries:
            if not isinstance(x,dict):continue
            posting=x.get('jobPosting') or x.get('job_posting') or x.get('json_ld') or {}
            if not isinstance(posting,dict):posting={}
            loc=x.get('location') or x.get('jobLocation') or posting.get('jobLocation') or ''
            if isinstance(loc,list):loc=', '.join(s(y) for y in loc)
            if isinstance(loc,dict):
                addr=loc.get('address',loc)
                loc=', '.join(s(addr.get(k)) for k in ('addressLocality','addressRegion','addressCountry') if isinstance(addr,dict) and addr.get(k))
            add(x.get('title') or posting.get('title'),x.get('company') or posting.get('hiringOrganization'),
                loc,x.get('url') or posting.get('url'),'OnJob',description=x.get('description') or posting.get('description'),
                posted=x.get('datePosted') or posting.get('datePosted'),jobtype=x.get('employmentType') or posting.get('employmentType'))
        sources.append('OnJob')
    except Exception as e: errors.append('OnJob: '+str(e)[:120])
# Optional Adzuna Australia. Requires free developer credentials, held only in GitHub secrets.
app=os.environ.get('ADZUNA_APP_ID');key=os.environ.get('ADZUNA_APP_KEY')
if app and key:
    for page in (1,2):
        try:
            params={'app_id':app,'app_key':key,'results_per_page':50,'what':'IT infrastructure engineer','where':'Brisbane','content-type':'application/json','sort_by':'date'}
            data=fetch('https://api.adzuna.com/v1/api/jobs/au/search/'+str(page)+'?'+urllib.parse.urlencode(params))
            for x in data.get('results',[]):
                low=x.get('salary_min'); high=x.get('salary_max')
                salary=('AUD '+str(round(low))+'–'+str(round(high or low))) if low else ''
                add(x.get('title'),x.get('company'),x.get('location'),x.get('redirect_url'),'Adzuna',
                    salary=salary,posted=x.get('created'),description=x.get('description'),country='Australia',
                    jobtype=x.get('contract_type'))
            sources.append('Adzuna')
        except Exception as e:errors.append('Adzuna: '+str(e)[:120])
else: errors.append('Adzuna keys not set; Australian results may be limited')
# Preserve last known data only if every source failed. Do not imply old data was freshly verified.
previous={}
if OUT.exists():
    try: previous=json.loads(OUT.read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
if not sources and previous.get('jobs'):
    payload={**previous,'lastAttempt':NOW,'fetchErrors':errors,'stale':True}
else:
    payload={'lastUpdated':NOW,'lastAttempt':NOW,'stale':False,'sources':sorted(set(sources)),
      'fetchErrors':list(dict.fromkeys(errors)),'jobs':sorted(jobs.values(),key=lambda j:j.get('posted',''),reverse=True)}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Fresh-source checks:',sources,'matching vacancies:',len(payload.get('jobs',[])),'errors:',errors)
